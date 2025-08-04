import os
import json
import random
from pathlib import Path
from modules.audio import AudioGenerator
from modules.volcengine_img2img_official import VolcengineImg2ImgOfficial, generate_image_from_prompt, generate_image_from_url
from modules.config import get_config
import subprocess
import shlex
import re

def split_text_into_sentences(text):
    """
    智能分割文本为句子，支持中文标点符号，特别处理引号
    """
    import re
    
    # 清理文本：移除多余空白字符
    text = re.sub(r'\s+', '', text.strip())
    
    if not text:
        return []
    
    # 使用更复杂的正则表达式来处理引号和标点的组合
    # 匹配：标点符号 + 可选的结束引号 + 可选的非引号字符（如逗号） + 可选的开始引号
    pattern = r'([。！？…]+["""''）】〉》』】〕｝〗〙〛〉｠]*[，、]*)'
    
    # 分割文本，保留分隔符
    parts = re.split(pattern, text)
    
    sentences = []
    current_sentence = ""
    
    i = 0
    while i < len(parts):
        part = parts[i]
        
        if not part:
            i += 1
            continue
        
        # 检查是否是分割符（包含句号等）
        if re.search(r'[。！？…]', part):
            # 这是一个结束标点，加到当前句子并结束
            current_sentence += part
            
            # 检查下一部分是否以开始引号开头
            if i + 1 < len(parts) and parts[i + 1]:
                next_part = parts[i + 1]
                # 如果下一部分以开始引号开头，可能需要合并到下下个句子
                if re.match(r'^["""''（【〈《『【〔｛〖〘〚〈｟]*', next_part):
                    # 不做处理，让开始引号留在下一句
                    pass
            
            if current_sentence.strip():
                sentences.append(current_sentence.strip())
            current_sentence = ""
        else:
            # 普通文本部分
            current_sentence += part
        
        i += 1
    
    # 处理最后一部分
    if current_sentence.strip():
        sentences.append(current_sentence.strip())
    
    # 后处理：合并过短的句子和处理开头引号问题
    final_sentences = []
    i = 0
    while i < len(sentences):
        sentence = sentences[i]
        
        # 如果当前句子以开始引号开头，尝试与前一句合并
        if (sentence.startswith(('"', '"', '（', '【')) and 
            final_sentences and 
            i > 0):  # 不是第一句
            
            # 检查前一句是否是一个完整的非引号句子
            prev_sentence = final_sentences[-1]
            
            # 如果前一句不以引号结尾，且当前句以引号开头，很可能需要合并
            if (not prev_sentence.endswith(('"', '"', '）', '】', '。', '！', '？')) or
                len(sentence) <= 15):  # 或者当前句很短
                # 与前一句合并
                final_sentences[-1] += sentence
            else:
                final_sentences.append(sentence)
        else:
            final_sentences.append(sentence)
        
        i += 1
    
    # 再次处理：检查是否有引号配对问题
    processed_sentences = []
    for i, sentence in enumerate(final_sentences):
        # 如果句子以引号开头但不是第一句，尝试特殊处理
        if (sentence.startswith(('"', '"')) and 
            i > 0 and 
            processed_sentences):
            
            # 检查前面是否有未闭合的引号
            prev_sentence = processed_sentences[-1]
            if ('"' in prev_sentence or '"' in prev_sentence) and \
               not (prev_sentence.endswith('"') or prev_sentence.endswith('"')):
                # 前面有未闭合引号，与前一句合并
                processed_sentences[-1] += sentence
            else:
                processed_sentences.append(sentence)
        else:
            processed_sentences.append(sentence)
    
    final_sentences = processed_sentences
    
    # 如果没有找到标点符号，或者句子太少，尝试按逗号等标点分割
    if len(final_sentences) <= 1 and text:
        # 首先尝试按逗号、顿号分割
        comma_parts = re.split(r'([，、])', text)
        comma_sentences = []
        current_part = ""
        
        for i, part in enumerate(comma_parts):
            current_part += part
            if part in ['，', '、'] or len(current_part) >= 25:
                # 检查下一部分是否以引号开头，如果是则合并
                if i + 1 < len(comma_parts):
                    next_part = comma_parts[i + 1]
                    quote_pattern = r'^["""''）】〉》』】〕｝〗〙〛〉｠]*'
                    quotes_match = re.match(quote_pattern, next_part)
                    
                    if quotes_match and quotes_match.group():
                        # 将引号部分添加到当前部分
                        quote_part = quotes_match.group()
                        current_part += quote_part
                        # 更新下一部分
                        comma_parts[i + 1] = next_part[len(quote_part):]
                
                if current_part.strip():
                    comma_sentences.append(current_part.strip())
                current_part = ""
        
        # 添加最后一部分
        if current_part.strip():
            comma_sentences.append(current_part.strip())
        
        # 如果按逗号分割效果更好，使用它
        if len(comma_sentences) > len(final_sentences) and len(comma_sentences) > 1:
            final_sentences = comma_sentences
        elif len(text) > 30:  # 如果还是太长，按长度强制分割
            max_length = 30  # 每句最大字符数
            parts = []
            remaining = text
            while remaining:
                if len(remaining) <= max_length:
                    parts.append(remaining)
                    break
                
                # 在max_length范围内寻找合适的分割点
                split_pos = max_length
                for punct in ['，', '、', ' ', '的', '了', '在']:
                    pos = remaining.rfind(punct, max_length // 2, max_length)
                    if pos > 0:
                        split_pos = pos + 1
                        break
                
                parts.append(remaining[:split_pos])
                remaining = remaining[split_pos:]
            
            final_sentences = [s.strip() for s in parts if s.strip()]
        else:
            final_sentences = [text] if text else []
    
    # 过滤掉空句子和过短的句子
    final_sentences = [s for s in final_sentences if len(s.strip()) >= 2]
    
    return final_sentences if final_sentences else [text]

def calculate_sentence_timing(sentences, total_duration, min_duration=1.5, max_duration=8.0):
    """
    根据句子长度和总时长计算每句字幕的显示时间
    参数:
    - sentences: 句子列表
    - total_duration: 总音频时长（秒）
    - min_duration: 每句最小显示时长（秒）
    - max_duration: 每句最大显示时长（秒）
    """
    if not sentences:
        return []
    
    # 计算每句的相对权重（基于字符数量）
    sentence_lengths = [len(s) for s in sentences]
    total_chars = sum(sentence_lengths)
    
    if total_chars == 0:
        return [(0, total_duration / len(sentences)) for _ in sentences]
    
    # 根据权重分配时间
    sentence_durations = []
    for length in sentence_lengths:
        # 基础时间分配（按字符比例）
        base_duration = (length / total_chars) * total_duration
        
        # 根据句子长度调整：短句适当延长，长句适当缩短
        if length <= 10:  # 短句
            adjusted_duration = max(base_duration, min_duration)
        elif length >= 40:  # 长句
            adjusted_duration = min(base_duration, max_duration)
        else:  # 中等长度句子
            adjusted_duration = base_duration
        
        sentence_durations.append(adjusted_duration)
    
    # 标准化时间，确保总时长匹配
    actual_total = sum(sentence_durations)
    if actual_total > 0:
        scale_factor = total_duration / actual_total
        sentence_durations = [d * scale_factor for d in sentence_durations]
    
    # 计算每句的开始时间和持续时间
    timing_info = []
    current_time = 0
    
    for duration in sentence_durations:
        timing_info.append((current_time, duration))
        current_time += duration
    
    return timing_info

def create_srt_subtitle(text, start_time=0, duration=None, output_path=None):
    """
    创建SRT字幕文件，支持按句子分割显示
    参数:
    - text: 字幕文本
    - start_time: 开始时间（秒）
    - duration: 持续时间（秒），如果为None则使用文本长度估算
    - output_path: 输出文件路径
    """
    if not text or not text.strip():
        return ""
    
    # 去除英文单引号和中文单引号
    text = text.replace("'", "").replace("’", "")
    
    if duration is None:
        # 根据文本长度估算时间（平均每个字0.15秒，最少3秒）
        duration = max(len(text) * 0.15, 3.0)
    
    def seconds_to_srt_time(seconds):
        """将秒转换为SRT时间格式 HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    # 分割文本为句子
    sentences = split_text_into_sentences(text)
    # 对每个句子也去除单引号
    sentences = [s.replace("'", "").replace("’", "") for s in sentences]
    
    # 如果只有一句话，使用原来的逻辑
    if len(sentences) <= 1:
        start_srt = seconds_to_srt_time(start_time)
        end_srt = seconds_to_srt_time(start_time + duration)
        srt_content = f"1\n{start_srt} --> {end_srt}\n{text}\n\n"
    else:
        # 计算每句的时间
        timing_info = calculate_sentence_timing(sentences, duration)
        
        # 生成多条字幕
        srt_content = ""
        for i, (sentence, (sentence_start, sentence_duration)) in enumerate(zip(sentences, timing_info)):
            subtitle_start = start_time + sentence_start
            subtitle_end = subtitle_start + sentence_duration
            
            start_srt = seconds_to_srt_time(subtitle_start)
            end_srt = seconds_to_srt_time(subtitle_end)
            
            srt_content += f"{i+1}\n{start_srt} --> {end_srt}\n{sentence}\n\n"
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        print(f"字幕文件已生成: {output_path} (包含 {len(sentences)} 条字幕)")
    
    return srt_content

def parse_srt_file(srt_content):
    """
    解析SRT文件内容，返回字幕条目列表
    返回格式：[(start_seconds, end_seconds, text), ...]
    """
    def srt_time_to_seconds(srt_time):
        """将SRT时间格式转换为秒"""
        parts = srt_time.replace(',', ':').split(':')
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]) + int(parts[3]) / 1000
    
    entries = []
    lines = srt_content.strip().split('\n')
    i = 0
    
    while i < len(lines):
        # 跳过空行
        if not lines[i].strip():
            i += 1
            continue
        
        # 跳过序号行
        if lines[i].strip().isdigit():
            i += 1
            if i >= len(lines):
                break
        
        # 解析时间行
        if '-->' in lines[i]:
            time_line = lines[i].strip()
            times = time_line.split(' --> ')
            start_time = srt_time_to_seconds(times[0].strip())
            end_time = srt_time_to_seconds(times[1].strip())
            
            i += 1
            
            # 获取字幕文本（可能有多行）
            subtitle_lines = []
            while i < len(lines) and lines[i].strip():
                subtitle_lines.append(lines[i])
                i += 1
            
            subtitle_text = '\n'.join(subtitle_lines)
            if subtitle_text.strip():
                entries.append((start_time, end_time, subtitle_text.strip()))
        else:
            i += 1
    
    return entries

def merge_srt_files(srt_files, video_files, output_path):
    '''
    合并多个SRT字幕文件，严格按视频片段真实时长对齐字幕，避免累计误差。
    srt_files: 字幕文件列表
    video_files: 对应的视频文件列表（顺序必须一致）
    '''
    def seconds_to_srt_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    all_entries = []
    current_time_offset = 0.0

    for srt_file, video_file in zip(srt_files, video_files):
        if not Path(srt_file).exists() or not Path(video_file).exists():
            continue

        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if not content:
            continue

        entries = parse_srt_file(content)
        video_duration = get_audio_duration(video_file)  # 用视频真实时长

        # 计算当前字幕的总时长
        if entries:
            srt_duration = entries[-1][1]
        else:
            srt_duration = 0

        # 时间缩放因子
        scale = video_duration / srt_duration if srt_duration > 0 else 1.0

        for start_time, end_time, text in entries:
            adjusted_start = current_time_offset + start_time * scale
            adjusted_end = current_time_offset + end_time * scale
            all_entries.append((adjusted_start, adjusted_end, text))
        current_time_offset += video_duration

    # 生成合并后的SRT内容
    merged_content = ""
    for i, (start_time, end_time, text) in enumerate(all_entries):
        start_srt = seconds_to_srt_time(start_time)
        end_srt = seconds_to_srt_time(end_time)
        merged_content += f"{i+1}\n{start_srt} --> {end_srt}\n{text}\n\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(merged_content)
    print(f"合并字幕文件已生成: {output_path} (严格对齐视频时长)")
    return str(output_path)

def get_random_camera_motion(frames):
    """
    随机选择一种运镜效果
    参数: frames - 总帧数
    返回: (效果名称, zoompan参数)
    
    zoompan参数说明：
    - z='zoom表达式': 控制缩放比例
    - x='x坐标表达式': 控制水平移动
    - y='y坐标表达式': 控制垂直移动
    - d=持续帧数: 效果持续时间（帧数）
    
    表达式中可用变量：
    - in_w, in_h: 输入图片宽高
    - out_w, out_h: 输出视频宽高
    - on: 当前帧数 (0-based)
    - n: 当前帧数 (1-based)
    """
    effects = [
        # 镜头推进：从全景缓慢推进到1.3倍大小
        ("推进", f"z='1+0.3*on/{frames}':x='iw/2-(iw*(1+0.3*on/{frames})/2)':y='ih/2-(ih*(1+0.3*on/{frames})/2)'"),
        
        # 镜头拉远：从特写(1.3倍)缓慢拉远到全景
        ("拉远", f"z='1.3-0.3*on/{frames}':x='iw/2-(iw*(1.3-0.3*on/{frames})/2)':y='ih/2-(ih*(1.3-0.3*on/{frames})/2)'"),
        
        # 镜头左移：保持1.2倍大小，从右向左平移
        ("左移", f"z='1.2':x='iw/2-(iw*1.2/2)+iw*0.15*on/{frames}':y='ih/2-(ih*1.2/2)'"),
        
        # 镜头右移：保持1.2倍大小，从左向右平移
        ("右移", f"z='1.2':x='iw/2-(iw*1.2/2)-iw*0.15*on/{frames}':y='ih/2-(ih*1.2/2)'")
    ]
    return random.choice(effects)

def load_progress(progress_path):
    if progress_path.exists():
        try:
            with open(progress_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_progress(progress_path, progress):
    with open(progress_path, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def get_audio_duration(audio_path):
    """用ffprobe获取音频时长（秒）"""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def create_paragraph_video_ffmpeg(audio_path, image_paths, output_path):
    """
    用ffmpeg将音频和多张图片合成视频，图片顺序与场景顺序一致，图片时长均分整个音频时长。
    添加运镜特效。
    """
    if not image_paths:
        print("没有场景图片，跳过视频生成")
        return None
    
    # 验证图片文件存在
    valid_images = [img for img in image_paths if Path(img).exists()]
    if not valid_images:
        print("没有有效的场景图片文件")
        return None
    
    duration = get_audio_duration(audio_path)
    if duration <= 0:
        print(f"音频时长无效: {audio_path}")
        return None
    
    print(f"创建段落视频: {len(valid_images)} 张图片，音频时长: {duration:.2f}秒")
    
    image_duration = duration / len(valid_images)
    print(f"每张图片显示时长: {image_duration:.2f}秒")
    
    # 确保输出目录存在
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成临时图片序列视频
    try:
        # 1. 首先将每张图片转换为带运镜效果的视频片段
        temp_videos = []
        for i, img in enumerate(valid_images):
            temp_video = output_dir / f"temp_segment_{i}_{os.getpid()}.mp4"
            
            # 计算帧数（使用30fps）
            frames = int(image_duration * 30)
            
            # 随机选择一种运镜效果
            effect_name, zoompan_params = get_random_camera_motion(frames)
            print(f"场景 {i+1}: 使用{effect_name}效果")
            
            # 构建滤镜参数
            filter_complex = (
                # 1. 首先将图片放大并应用锐化
                f"scale=2400:1350:flags=lanczos,"
                f"unsharp=3:3:1.5:3:3:0.5,"
                # 2. 应用运镜效果
                f"zoompan={zoompan_params}"
                f":d={frames}"  # 持续帧数
                ":fps=30"  # 输出帧率
                ":s=1920x1080,"  # 输出分辨率
                # 3. 最终格式化
                "format=yuv420p"
            )
            
            cmd = [
                'ffmpeg', '-y',
                '-i', str(Path(img).resolve()),
                '-vf', filter_complex,
                '-c:v', 'libx264',
                '-preset', 'slow',  # 使用较慢的编码预设以提高质量
                '-crf', '23',      # 控制视频质量
                '-t', str(image_duration),
                str(temp_video)
            ]

            print(f"执行命令: {' '.join(cmd)}")
            
            print(f"生成视频片段 {i+1}/{len(valid_images)}")
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"生成视频片段失败 {i+1}:")
                print(f"stderr: {res.stderr}")
                print(f"stdout: {res.stdout}")
                # 清理已生成的临时文件
                for v in temp_videos:
                    v.unlink(missing_ok=True)
                return None
            temp_videos.append(temp_video)
        
        # 2. 生成片段列表文件
        temp_list = output_dir / f"temp_list_{os.getpid()}.txt"
        with open(temp_list, 'w', encoding='utf-8') as f:
            for v in temp_videos:
                f.write(f"file '{v.resolve()}'\n")
        
        # 3. 合并所有视频片段
        temp_final = output_dir / f"temp_final_{os.getpid()}.mp4"
        cmd_concat = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(temp_list),
            '-c', 'copy',
            str(temp_final)
        ]
        print("合并视频片段...")
        res_concat = subprocess.run(cmd_concat, capture_output=True, text=True)
        if res_concat.returncode != 0:
            print("合并视频片段失败:")
            print(f"stderr: {res_concat.stderr}")
            print(f"stdout: {res_concat.stdout}")
            # 清理临时文件
            temp_list.unlink(missing_ok=True)
            for v in temp_videos:
                v.unlink(missing_ok=True)
            return None
        
        # 4. 添加音频（不嵌入字幕）
        cmd_audio = [
            'ffmpeg', '-y',
            '-i', str(temp_final),
            '-i', str(audio_path),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',
            str(output_path)
        ]
        print("添加音频...")
            
        res_audio = subprocess.run(cmd_audio, capture_output=True, text=True)
        if res_audio.returncode != 0:
            print("添加音频和字幕失败:")
            print(f"stderr: {res_audio.stderr}")
            print(f"stdout: {res_audio.stdout}")
            return None
        
        print(f"段落视频已生成: {output_path}")
        return str(output_path)
        
    except Exception as e:
        print(f"创建段落视频时发生错误: {e}")
        return None
        
    finally:
        # 清理所有临时文件
        for v in temp_videos:
            v.unlink(missing_ok=True)
        if 'temp_list' in locals():
            temp_list.unlink(missing_ok=True)
        if 'temp_final' in locals():
            temp_final.unlink(missing_ok=True)

def create_chapter_video_ffmpeg(paragraph_videos, output_path, chapter_subtitle_path=None):
    """
    用ffmpeg将所有段落视频拼接成章节视频，并添加背景音乐和字幕
    """
    valid_videos = [v for v in paragraph_videos if Path(v).exists()]
    if not valid_videos:
        print("没有有效的段落视频，跳过章节视频生成")
        return None
    
    print(f"拼接章节视频: {len(valid_videos)} 个段落视频")
    
    # 确保输出目录存在
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查背景音乐文件
    bgm_path = Path("configs/bgm.mp3")
    if not bgm_path.exists():
        print(f"背景音乐文件不存在: {bgm_path}，使用原始音频")
        use_bgm = False
    else:
        print(f"使用背景音乐: {bgm_path}")
        use_bgm = True
    
    temp_list_file = output_dir / f"temp_videolist_{os.getpid()}.txt"
    temp_concat_video = output_dir / f"temp_concat_{os.getpid()}.mp4"
    
    try:
        # 1. 首先拼接所有段落视频（不带音频）
        with open(temp_list_file, 'w', encoding='utf-8') as f:
            for v in valid_videos:
                # 使用绝对路径避免路径问题
                abs_video_path = Path(v).resolve()
                f.write(f"file '{abs_video_path}'\n")
        
        if use_bgm:
            # 如果有背景音乐，分两步处理
            # 第一步：拼接视频
            cmd_concat = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', str(temp_list_file),
                '-c', 'copy',
                str(temp_concat_video)
            ]
            
            print("拼接视频片段...")
            res_concat = subprocess.run(cmd_concat, capture_output=True, text=True)
            if res_concat.returncode != 0:
                print(f"视频拼接失败:")
                print(f"stderr: {res_concat.stderr}")
                print(f"stdout: {res_concat.stdout}")
                return None
            
            # 第二步：添加背景音乐和主音频混合（不嵌入字幕）
            cmd_final = [
                'ffmpeg', '-y',
                '-i', str(temp_concat_video),  # 拼接后的视频
                '-i', str(bgm_path.resolve()),  # 背景音乐
                '-filter_complex', 
                '[1:a]volume=0.3,aloop=loop=-1:size=2e+09[bgm];'  # 背景音乐降低音量到30%，循环播放
                '[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[audio_out]',  # 混合音频
                '-map', '0:v',  # 使用原视频
                '-map', '[audio_out]',  # 使用混合后的音频
                '-c:v', 'copy',  # 视频不重新编码
                '-c:a', 'aac',  # 音频编码为AAC
                '-shortest',  # 以最短的输入为准
                str(output_path)
            ]
            
            print("添加背景音乐并混合音频...")
            res_final = subprocess.run(cmd_final, capture_output=True, text=True)
            if res_final.returncode != 0:
                print(f"添加背景音乐失败:")
                print(f"stderr: {res_final.stderr}")
                print(f"stdout: {res_final.stdout}")
                return None
        else:
            # 如果没有背景音乐，直接拼接（不嵌入字幕）
            cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', str(temp_list_file),
                '-c', 'copy',
                str(output_path)
            ]
            
            print("拼接视频（无背景音乐）...")
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"章节视频拼接失败:")
                print(f"stderr: {res.stderr}")
                print(f"stdout: {res.stdout}")
                return None
        
        print(f"章节视频已生成: {output_path}")
        return str(output_path)
        
    except Exception as e:
        print(f"创建章节视频时发生错误: {e}")
        return None
    finally:
        # 清理临时文件
        temp_list_file.unlink(missing_ok=True)
        if 'temp_concat_video' in locals():
            temp_concat_video.unlink(missing_ok=True)

def create_complete_video_ffmpeg(chapter_videos, output_path, complete_subtitle_path=None):
    """
    用ffmpeg将所有章节视频拼接成完整视频，并添加背景音乐和字幕
    参数:
    - chapter_videos: 章节视频路径列表
    - output_path: 输出完整视频路径
    - complete_subtitle_path: 完整字幕文件路径
    """
    valid_videos = [v for v in chapter_videos if Path(v).exists()]
    if not valid_videos:
        print("没有有效的章节视频，跳过完整视频生成")
        return None
    
    print(f"拼接完整视频: {len(valid_videos)} 个章节视频")
    
    # 确保输出目录存在
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查背景音乐文件
    bgm_path = Path("configs/bgm.mp3")
    if not bgm_path.exists():
        print(f"背景音乐文件不存在: {bgm_path}，使用原始音频")
        use_bgm = False
    else:
        print(f"使用背景音乐: {bgm_path}")
        use_bgm = True
    
    temp_list_file = output_dir / f"temp_complete_videolist_{os.getpid()}.txt"
    temp_concat_video = output_dir / f"temp_complete_concat_{os.getpid()}.mp4"
    
    try:
        # 1. 首先拼接所有章节视频
        with open(temp_list_file, 'w', encoding='utf-8') as f:
            for v in valid_videos:
                # 使用绝对路径避免路径问题
                abs_video_path = Path(v).resolve()
                f.write(f"file '{abs_video_path}'\n")
        
        if use_bgm:
            # 如果有背景音乐，分两步处理
            # 第一步：拼接视频
            cmd_concat = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', str(temp_list_file),
                '-c', 'copy',
                str(temp_concat_video)
            ]
            
            print("拼接章节视频...")
            res_concat = subprocess.run(cmd_concat, capture_output=True, text=True)
            if res_concat.returncode != 0:
                print(f"章节视频拼接失败:")
                print(f"stderr: {res_concat.stderr}")
                print(f"stdout: {res_concat.stdout}")
                return None
            
            # 第二步：添加背景音乐（不嵌入字幕）
            cmd_final = [
                'ffmpeg', '-y',
                '-i', str(temp_concat_video),  # 拼接后的视频
                '-i', str(bgm_path.resolve()),  # 背景音乐
                '-filter_complex', 
                '[1:a]volume=0.3,aloop=loop=-1:size=2e+09[bgm];'  # 背景音乐降低音量到30%，循环播放
                '[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[audio_out]',  # 混合音频
                '-map', '0:v',  # 使用原视频
                '-map', '[audio_out]',  # 使用混合后的音频
                '-c:v', 'copy',  # 视频不重新编码
                '-c:a', 'aac',  # 音频编码为AAC
                '-shortest',  # 以最短的输入为准
                str(output_path)
            ]
            
            print("添加背景音乐...")
            res_final = subprocess.run(cmd_final, capture_output=True, text=True)
            if res_final.returncode != 0:
                print(f"添加背景音乐失败:")
                print(f"stderr: {res_final.stderr}")
                print(f"stdout: {res_final.stdout}")
                return None
        else:
            # 如果没有背景音乐，直接拼接（不嵌入字幕）
            cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', str(temp_list_file),
                '-c', 'copy',
                str(output_path)
            ]
            print("拼接视频（无背景音乐）...")
            
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"完整视频拼接失败:")
                print(f"stderr: {res.stderr}")
                print(f"stdout: {res.stdout}")
                return None
        
        print(f"完整视频已生成: {output_path}")
        return str(output_path)
        
    except Exception as e:
        print(f"创建完整视频时发生错误: {e}")
        return None
    finally:
        # 清理临时文件
        temp_list_file.unlink(missing_ok=True)
        if 'temp_concat_video' in locals():
            temp_concat_video.unlink(missing_ok=True)

def create_complete_movie(output_base="output", movie_output_path="output/complete_movie.mp4"):
    """
    扫描output目录，收集所有章节视频和字幕，合并成完整电影
    参数:
    - output_base: 输出目录根路径
    - movie_output_path: 完整电影输出路径
    """
    print(f"\n{'='*80}")
    print("开始创建完整电影")
    print(f"{'='*80}")
    
    output_dir = Path(output_base)
    if not output_dir.exists():
        print(f"输出目录不存在: {output_dir}")
        return None
    
    # 收集所有章节目录和视频文件
    chapter_dirs = []
    chapter_videos = []
    chapter_subtitles = []
    
    # 扫描所有子目录，查找章节视频
    for item in output_dir.iterdir():
        if item.is_dir():
            chapter_video = item / "chapter_video.mp4"
            chapter_subtitle = item / "chapter_subtitle.srt"
            
            if chapter_video.exists():
                chapter_dirs.append(item.name)
                chapter_videos.append(str(chapter_video))
                
                if chapter_subtitle.exists():
                    chapter_subtitles.append(str(chapter_subtitle))
                    print(f"发现章节: {item.name} (有视频和字幕)")
                else:
                    print(f"发现章节: {item.name} (仅有视频)")
    
    if not chapter_videos:
        print("未找到任何章节视频文件")
        return None
    
    # 按章节名称排序（尝试按数字排序）
    def sort_key(name):
        import re
        match = re.search(r'(\d+)', name)
        if match:
            return int(match.group(1))
        return name
    
    # 创建排序后的列表，补齐字幕列表长度
    while len(chapter_subtitles) < len(chapter_videos):
        chapter_subtitles.append("")  # 为没有字幕的章节添加空字符串
    
    sorted_data = sorted(zip(chapter_dirs, chapter_videos, chapter_subtitles), key=lambda x: sort_key(x[0]))
    chapter_dirs, chapter_videos, chapter_subtitles = zip(*sorted_data) if sorted_data else ([], [], [])
    
    # 过滤掉空的字幕文件
    chapter_subtitles = [sub for sub in chapter_subtitles if sub and Path(sub).exists()]
    chapter_videos_for_subs = [v for v, s in zip(chapter_videos, chapter_subtitles) if s and Path(s).exists()]
    
    print(f"找到 {len(chapter_videos)} 个章节视频，按顺序:")
    for i, (dir_name, video_path) in enumerate(zip(chapter_dirs, chapter_videos)):
        duration = get_audio_duration(video_path)
        print(f"  {i+1}. {dir_name} ({duration:.2f}秒)")
    
    # 生成完整字幕文件
    complete_subtitle_path = None
    if chapter_subtitles and chapter_videos_for_subs:
        complete_subtitle_path = Path(movie_output_path).parent / "complete_movie_subtitle.srt"
        print(f"合并章节字幕到: {complete_subtitle_path}")
        merge_srt_files(list(chapter_subtitles), list(chapter_videos_for_subs), str(complete_subtitle_path))
    
    # 生成完整视频
    print(f"开始生成完整电影: {movie_output_path}")
    result = create_complete_video_ffmpeg(
        chapter_videos=list(chapter_videos),
        output_path=movie_output_path,
        complete_subtitle_path=str(complete_subtitle_path) if complete_subtitle_path else None
    )
    
    if result:
        total_duration = get_audio_duration(result)
        print(f"\n🎉 完整电影生成成功!")
        print(f"📁 电影文件: {result}")
        print(f"⏱️  总时长: {total_duration:.2f}秒 ({total_duration/60:.1f}分钟)")
        if complete_subtitle_path and complete_subtitle_path.exists():
            print(f"📝 字幕文件: {complete_subtitle_path}")
        print(f"🎬 包含章节数: {len(chapter_videos)}")
        print(f"{'='*80}")
        return result
    else:
        print("❌ 完整电影生成失败")
        return None

def process_chapter(chapter_json_path, output_base="output"):
    # 1. 读取章节JSON
    with open(chapter_json_path, "r", encoding="utf-8") as f:
        chapter_data = json.load(f)
    chapter_info = chapter_data["章节信息"]
    scene_breakdown = chapter_data["场景拆解"]

    config = get_config()
    volc_cred = config.get("volcengine")["credentials"]
    volc_params = config.get("volcengine")["image_to_image"]["default_params"]
    audio_gen = AudioGenerator()
    volc_client = VolcengineImg2ImgOfficial(
        access_key_id=volc_cred["access_key_id"],
        secret_access_key=volc_cred["secret_access_key"],
        region=volc_cred.get("region", "cn-north-1")
    )

    # 章节目录名
    chapter_num = chapter_info["章节号"].replace("第", "").replace("章", "")
    chapter_title = chapter_info.get("标题", "")
    chapter_folder = f"{chapter_num}-{chapter_title}" if chapter_title else f"{chapter_num}章"
    chapter_output_dir = Path(output_base) / chapter_folder
    progress_path = chapter_output_dir / ".progress.json"
    progress = load_progress(progress_path)
    paragraph_videos = []
    paragraph_subtitles = []

    print(f"\n{'='*60}")
    print(f"开始处理 {chapter_info['章节号']}: {chapter_folder}")
    print(f"包含 {len(scene_breakdown)} 个段落")
    print(f"{'='*60}")

    all_results = []
    for para in scene_breakdown:
        para_title = para["段落标题"]
        para_num = para["序号"]
        para_dir = chapter_output_dir / f"{para_num}-{para_title}"
        para_dir.mkdir(parents=True, exist_ok=True)
        para_key = f"{chapter_info['章节号']}-{para_title}"
        para_progress = progress.get(para_key, {})

        print(f"\n处理段落: {chapter_info['章节号']} - {para_title}")

        # 2. 检查并生成段落音频
        audio_path = para_dir / "audio.wav"
        if audio_path.exists() and audio_path.stat().st_size > 0:
            print(f"音频文件已存在且有效: {audio_path}")
            audio_file = str(audio_path)
        else:
            print(f"生成音频文件: {audio_path}")
            try:
                audio_file = audio_gen.generate(
                    text=para["场景文案"],
                    type="paragraph",
                    language="zh",
                    output_path=str(audio_path)
                )
                para_progress["audio_done"] = True
                save_progress(progress_path, progress)
            except Exception as e:
                print(f"音频生成失败: {para_title}，错误: {e}")
                save_progress(progress_path, progress)
                break

        # 3. 检查并生成场景图片和字幕
        scene_files = []
        scene_subtitles = []
        missing_scenes = []
        scene_count = len(para["场景列表"])
        total_duration = get_audio_duration(str(audio_path)) if Path(audio_path).exists() else 0
        scene_duration = total_duration / scene_count if scene_count > 0 else 10.0

        for i, scene in enumerate(para["场景列表"]):
            scene_id = scene["场景编号"]
            img_path = para_dir / f"scene_{scene_id}.jpg"
            scene_subtitle_path = para_dir / f"scene_{scene_id}_subtitle.srt"

            # 生成场景字幕
            if not scene_subtitle_path.exists():
                scene_start_time = i * scene_duration
                print(f"生成场景字幕: scene_{scene_id}")
                create_srt_subtitle(
                    text=para["场景文案"],
                    start_time=scene_start_time,
                    duration=scene_duration,
                    output_path=str(scene_subtitle_path)
                )
            else:
                print(f"场景字幕已存在: scene_{scene_id}")

            scene_subtitles.append(str(scene_subtitle_path))

            if img_path.exists() and img_path.stat().st_size > 0:
                print(f"场景图片已存在且有效: scene_{scene_id}.jpg")
                scene_files.append(str(img_path))
            else:
                missing_scenes.append((scene, img_path))

        # 生成缺失的场景图片
        for scene, img_path in missing_scenes:
            print(f"生成缺失的场景图片: scene_{scene['场景编号']}.jpg")
            try:
                if scene.get("场景图片url"):
                    image_url = scene.get("场景图片url")
                else:
                    image_url = f"http://zhuluoji.cn-sh2.ufileos.com/test/{scene.get('主角', '主角')}.jpeg"
                generate_image_from_prompt(
                    output_path=str(img_path),
                    access_key_id=volc_cred["access_key_id"],
                    secret_access_key=volc_cred["secret_access_key"],
                    prompt=scene["图片提示词"],
                )
                scene_files.append(str(img_path))
                para_progress["scene_files"] = scene_files
                progress[para_key] = para_progress
                save_progress(progress_path, progress)
            except Exception as e:
                print(f"图片生成失败: scene_{scene['场景编号']}.jpg，错误: {e}")
                save_progress(progress_path, progress)
                return all_results  # 断点退出

        # 4. 生成段落字幕文件
        paragraph_subtitle_path = para_dir / "paragraph_subtitle.srt"
        audio_duration = get_audio_duration(str(audio_path))
        if not paragraph_subtitle_path.exists():
            print(f"生成段落字幕: {para_title}")
            create_srt_subtitle(
                text=para["场景文案"],
                start_time=0,
                duration=audio_duration,
                output_path=str(paragraph_subtitle_path)
            )
        else:
            print(f"段落字幕已存在: {paragraph_subtitle_path}")
        paragraph_subtitles.append(str(paragraph_subtitle_path))

        # 5. 检查并生成段落视频
        paragraph_video_path = para_dir / "paragraph_video.mp4"
        video_exists = paragraph_video_path.exists() and paragraph_video_path.stat().st_size > 0
        if video_exists:
            video_duration = get_audio_duration(str(paragraph_video_path))
            duration_match = abs(video_duration - audio_duration) <= 1.0
            if duration_match:
                print(f"段落视频已存在且有效: {paragraph_video_path}")
                paragraph_videos.append(str(paragraph_video_path))
            else:
                print(f"段落视频存在但时长不匹配 (视频: {video_duration:.2f}s, 音频: {audio_duration:.2f}s)，需要重新生成")
                video_exists = False
        if not video_exists:
            print(f"生成段落视频: {para_title}")
            video_path = create_paragraph_video_ffmpeg(
                audio_path=str(audio_path),
                image_paths=scene_files,
                output_path=str(paragraph_video_path)
            )
            if video_path:
                para_progress["video_done"] = True
                progress[para_key] = para_progress
                save_progress(progress_path, progress)
                paragraph_videos.append(video_path)
                print(f"段落视频生成成功: {para_title}")
            else:
                print(f"段落视频生成失败: {para_title}")

        # 6. 记录结果
        all_results.append({
            "chapter": chapter_info["章节号"],
            "para_title": para_title,
            "audio": str(audio_path),
            "images": scene_files,
            "video": str(paragraph_video_path),
            "paragraph_subtitle": str(paragraph_subtitle_path),
            "scene_subtitles": scene_subtitles
        })
        progress[para_key] = para_progress
        save_progress(progress_path, progress)

    # 7. 生成章节字幕文件
    chapter_subtitle_path = chapter_output_dir / "chapter_subtitle.srt"
    if paragraph_subtitles:
        if not chapter_subtitle_path.exists():
            print(f"生成章节字幕: {chapter_folder}")
            merge_srt_files(paragraph_subtitles, paragraph_videos, str(chapter_subtitle_path))
        else:
            print(f"章节字幕已存在: {chapter_subtitle_path}")

    # 8. 检查并生成本章节视频
    chapter_video_path = chapter_output_dir / "chapter_video.mp4"
    if paragraph_videos:
        chapter_needs_update = True
        if chapter_video_path.exists() and chapter_video_path.stat().st_size > 0:
            total_para_duration = sum(get_audio_duration(v) for v in paragraph_videos)
            chapter_duration = get_audio_duration(str(chapter_video_path))
            if abs(total_para_duration - chapter_duration) <= 1.0:
                print(f"章节视频已存在且有效: {chapter_video_path}")
                chapter_needs_update = False
            else:
                print(f"章节视频存在但时长不匹配 (视频: {chapter_duration:.2f}s, 预期: {total_para_duration:.2f}s)，需要重新生成")
        if chapter_needs_update:
            print(f"生成章节视频: {chapter_folder}")
            chapter_video_result = create_chapter_video_ffmpeg(
                paragraph_videos, 
                str(chapter_video_path),
                chapter_subtitle_path=str(chapter_subtitle_path) if chapter_subtitle_path.exists() else None
            )
            if chapter_video_result:
                print(f"章节视频生成成功: {chapter_video_result}")
            else:
                print(f"章节视频生成失败: {chapter_folder}")
    else:
        print(f"没有有效的段落视频，跳过章节视频生成: {chapter_info['章节号']}")

    print(f"\n{'='*60}")
    print(f"章节处理完成！共生成 {len(paragraph_videos)} 个段落视频")
    for video in paragraph_videos:
        print(f"  - {video}")
    print(f"{'='*60}")

    return all_results

def process_all_chapters(chapters_dir="chapters/processed", output_base="output"):
    """
    处理所有章节文件，生成视频
    """
    chapters_dir = Path(chapters_dir)
    chapter_files = [
        "chapter_001_processed.json",
        "chapter_002_processed.json",
        "chapter_003_processed.json",
        "chapter_004_processed.json",
        "chapter_005_processed.json",
        "chapter_006_processed.json",
        "chapter_007_processed.json",
        "chapter_008_processed.json",
        "chapter_009_processed.json",
        "chapter_010_processed.json",
        "chapter_011_processed.json",
        "chapter_012_processed.json",
        "chapter_013_processed.json",
        "chapter_014_processed.json",
        "chapter_015_processed.json",
        "chapter_016_processed.json",
        "chapter_017_processed.json",
        "chapter_018_processed.json",
        "chapter_019_processed.json",
        "chapter_020_processed.json",
        "chapter_021_processed.json",
        "chapter_022_processed.json",
        "chapter_023_processed.json",
        "chapter_024_processed.json",
        "chapter_025_processed.json",
        "chapter_026_processed.json",
        "chapter_027_processed.json",
        "chapter_028_processed.json",
        "chapter_029_processed.json",
        "chapter_030_processed.json",
        "chapter_031_processed.json",
        "chapter_032_processed.json",
        "chapter_033_processed.json",
        "chapter_034_processed.json",
        "chapter_035_processed.json",
        "chapter_036_processed.json",
        "chapter_037_processed.json",
        "chapter_038_processed.json",
        "chapter_039_processed.json",
        "chapter_040_processed.json",
    ]
    
    all_results = []
    
    for chapter_file in chapter_files:
        chapter_path = chapters_dir / chapter_file
        if not chapter_path.exists():
            print(f"章节文件不存在: {chapter_path}")
            continue
        
        print(f"\n{'='*50}")
        print(f"开始处理章节: {chapter_file}")
        print(f"{'='*50}")
        
        try:
            results = process_chapter(str(chapter_path), output_base)
            all_results.extend(results)
            print(f"章节 {chapter_file} 处理完成")
        except Exception as e:
            print(f"章节 {chapter_file} 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n所有章节处理完成，共生成 {len(all_results)} 个段落视频")
    
    # 生成完整电影
    print(f"\n{'='*60}")
    print("开始生成完整电影...")
    print(f"{'='*60}")
    
    complete_movie_path = create_complete_movie(
        output_base=output_base,
        movie_output_path=f"{output_base}/complete_movie.mp4"
    )
    
    if complete_movie_path:
        print(f"✅ 完整电影已生成: {complete_movie_path}")
    else:
        print("❌ 完整电影生成失败")
    
    return all_results

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg == "--movie" or arg == "--complete":
            # 只生成完整电影
            print("生成完整电影...")
            complete_movie_path = create_complete_movie()
            if complete_movie_path:
                print(f"✅ 完整电影生成完成: {complete_movie_path}")
            else:
                print("❌ 完整电影生成失败")
        
        elif arg.endswith('.json'):
            # 处理单个章节
            chapter_json = arg
            print(f"处理单个章节: {chapter_json}")
            results = process_chapter(chapter_json)
            print("\n章节处理完成，结果：")
            for para in results:
                print(f"段落: {para['para_title']}")
                print(f"  音频: {para['audio']}")
                print(f"  视频: {para['video']}")
                for img in para['images']:
                    print(f"  场景图片: {img}")
        else:
            print("用法:")
            print("  python loop.py [章节文件.json]     # 处理单个章节")
            print("  python loop.py --movie              # 仅生成完整电影")
            print("  python loop.py                      # 处理所有章节并生成完整电影")
    else:
        # 处理所有章节
        print("处理所有章节")
        all_results = process_all_chapters()
        print(f"\n所有章节处理完成，共生成 {len(all_results)} 个段落视频")
