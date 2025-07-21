#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFmpeg 视频剪辑工具
实现音频和图片合成视频，以及视频拼接功能
"""

import os
import json
import subprocess
import glob
from pathlib import Path
from typing import List, Tuple, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FFmpegVideoEditor:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        
    def get_audio_duration(self, audio_file: str) -> float:
        """获取音频文件时长（秒）"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', str(audio_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            logger.info(f"音频 {audio_file} 时长: {duration:.2f} 秒")
            return duration
        except subprocess.CalledProcessError as e:
            logger.error(f"获取音频时长失败: {e}")
            raise
        except ValueError as e:
            logger.error(f"解析音频时长失败: {e}")
            raise
    
    def create_image_sequence_video(self, image_files: List[str], duration: float, 
                                   output_file: str, fps: int = 1) -> bool:
        """创建图片序列视频"""
        if not image_files:
            logger.error("没有图片文件")
            return False
            
        # 计算每张图片的显示时长
        image_duration = duration / len(image_files)
        
        try:
            # 创建临时文件列表
            temp_list_file = "temp_image_list.txt"
            with open(temp_list_file, 'w', encoding='utf-8') as f:
                for img_file in image_files:
                    f.write(f"file '{img_file}'\n")
                    f.write(f"duration {image_duration}\n")
                # 最后一张图片需要重复一次，否则会被截断
                f.write(f"file '{image_files[-1]}'\n")
            
            # 使用 ffmpeg 创建视频
            cmd = [
                'ffmpeg', '-y',  # 覆盖输出文件
                '-f', 'concat',
                '-safe', '0',
                '-i', temp_list_file,
                '-vsync', 'vfr',  # 可变帧率
                '-pix_fmt', 'yuv420p',  # 兼容性更好的像素格式
                '-r', str(fps),  # 帧率
                '-t', str(duration),  # 总时长
                str(output_file)
            ]
            
            logger.info(f"创建图片序列视频: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # 清理临时文件
            os.remove(temp_list_file)
            
            logger.info(f"图片序列视频创建成功: {output_file}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"创建图片序列视频失败: {e}")
            if os.path.exists(temp_list_file):
                os.remove(temp_list_file)
            return False
        except Exception as e:
            logger.error(f"创建图片序列视频时发生错误: {e}")
            if os.path.exists(temp_list_file):
                os.remove(temp_list_file)
            return False
    
    def combine_audio_and_video(self, audio_file: str, video_file: str, 
                               output_file: str) -> bool:
        """合成音频和视频"""
        try:
            cmd = [
                'ffmpeg', '-y',  # 覆盖输出文件
                '-i', str(video_file),
                '-i', str(audio_file),
                '-c:v', 'copy',  # 复制视频流
                '-c:a', 'aac',   # 音频编码为 AAC
                '-shortest',     # 以最短的流为准
                str(output_file)
            ]
            
            logger.info(f"合成音频和视频: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info(f"音频视频合成成功: {output_file}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"合成音频和视频失败: {e}")
            return False
    
    def create_paragraph_video(self, para_dir: Path) -> Optional[str]:
        """为单个段落创建视频"""
        # 查找音频文件
        audio_files = list(para_dir.glob("*.wav")) + list(para_dir.glob("*.mp3"))
        if not audio_files:
            logger.warning(f"段落目录 {para_dir} 中没有找到音频文件")
            return None
            
        audio_file = audio_files[0]
        
        # 查找图片文件
        image_files = sorted(para_dir.glob("*.jpg")) + sorted(para_dir.glob("*.png"))
        if not image_files:
            logger.warning(f"段落目录 {para_dir} 中没有找到图片文件")
            return None
        
        # 获取音频时长
        duration = self.get_audio_duration(audio_file)
        
        # 创建临时视频文件
        temp_video = para_dir / "temp_video.mp4"
        if not self.create_image_sequence_video(
            [str(img) for img in image_files], duration, str(temp_video)
        ):
            return None
        
        # 合成最终视频
        output_video = para_dir / f"{para_dir.name}.mp4"
        if not self.combine_audio_and_video(audio_file, temp_video, output_video):
            return None
        
        # 清理临时文件
        if temp_video.exists():
            temp_video.unlink()
        
        return str(output_video)
    
    def concatenate_videos(self, video_files: List[str], output_file: str) -> bool:
        """拼接多个视频文件"""
        if not video_files:
            logger.error("没有视频文件可拼接")
            return False
        
        try:
            # 创建视频列表文件
            temp_list_file = "temp_video_list.txt"
            with open(temp_list_file, 'w', encoding='utf-8') as f:
                for video_file in video_files:
                    f.write(f"file '{video_file}'\n")
            
            # 使用 ffmpeg 拼接视频
            cmd = [
                'ffmpeg', '-y',  # 覆盖输出文件
                '-f', 'concat',
                '-safe', '0',
                '-i', temp_list_file,
                '-c', 'copy',  # 直接复制流，不重新编码
                str(output_file)
            ]
            
            logger.info(f"拼接视频: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # 清理临时文件
            os.remove(temp_list_file)
            
            logger.info(f"视频拼接成功: {output_file}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"拼接视频失败: {e}")
            if os.path.exists(temp_list_file):
                os.remove(temp_list_file)
            return False
        except Exception as e:
            logger.error(f"拼接视频时发生错误: {e}")
            if os.path.exists(temp_list_file):
                os.remove(temp_list_file)
            return False
    
    def process_chapter(self, chapter_dir: Path) -> bool:
        """处理整个章节"""
        logger.info(f"开始处理章节: {chapter_dir}")
        
        # 查找所有段落目录
        para_dirs = [d for d in chapter_dir.iterdir() if d.is_dir() and d.name.startswith(('1-', '2-', '3-', '4-', '5-', '6-', '7-', '8-', '9-'))]
        para_dirs.sort(key=lambda x: int(x.name.split('-')[0]))
        
        if not para_dirs:
            logger.warning(f"章节目录 {chapter_dir} 中没有找到段落目录")
            return False
        
        # 为每个段落创建视频
        video_files = []
        for para_dir in para_dirs:
            logger.info(f"处理段落: {para_dir}")
            video_file = self.create_paragraph_video(para_dir)
            if video_file:
                video_files.append(video_file)
            else:
                logger.warning(f"段落 {para_dir} 视频创建失败")
        
        if not video_files:
            logger.error(f"章节 {chapter_dir} 没有成功创建任何视频")
            return False
        
        # 拼接所有段落视频为章节视频
        chapter_video = chapter_dir / f"{chapter_dir.name}.mp4"
        if self.concatenate_videos(video_files, str(chapter_video)):
            logger.info(f"章节视频创建成功: {chapter_video}")
            return True
        else:
            logger.error(f"章节视频创建失败: {chapter_video}")
            return False
    
    def process_all_chapters(self) -> None:
        """处理所有章节"""
        chapter_dirs = [d for d in self.output_dir.iterdir() if d.is_dir()]
        
        if not chapter_dirs:
            logger.warning(f"输出目录 {self.output_dir} 中没有找到章节目录")
            return
        
        for chapter_dir in chapter_dirs:
            self.process_chapter(chapter_dir)

def main():
    """主函数"""
    editor = FFmpegVideoEditor()
    
    # 检查 ffmpeg 是否可用
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        logger.info("FFmpeg 可用")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("FFmpeg 未安装或不可用，请先安装 FFmpeg")
        return
    
    # 处理所有章节
    editor.process_all_chapters()

if __name__ == "__main__":
    main() 