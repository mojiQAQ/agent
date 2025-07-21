#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说分章脚本
将 chapters/novel.txt 按照 '第x章' 的关键字进行分解，每50章一个文件
"""

import re
import os
from pathlib import Path

def split_novel_by_chapters(input_file, chapters_per_file=50, start_chapter=None, end_chapter=None):
    """
    将小说按章节分解
    
    Args:
        input_file (str): 输入文件路径
        chapters_per_file (int): 每个文件包含的章节数，默认50章
        start_chapter (int): 起始章节号，可选
        end_chapter (int): 结束章节号，可选
    """
    # 读取小说文件
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用正则表达式匹配章节标题
    chapter_pattern = r'第(\d+)章[^\n]*'
    chapters = re.finditer(chapter_pattern, content)
    
    # 收集所有章节的起始位置和章节号
    chapter_info = []
    for match in chapters:
        chapter_num = int(match.group(1))
        start_pos = match.start()
        chapter_info.append((chapter_num, start_pos, match.group(0)))
    
    if not chapter_info:
        print("未找到任何章节标记")
        return
    
    # 按章节号排序
    chapter_info.sort(key=lambda x: x[0])
    
    # 过滤章节范围
    if start_chapter or end_chapter:
        filtered_chapters = []
        for chapter_num, start_pos, title in chapter_info:
            if start_chapter and chapter_num < start_chapter:
                continue
            if end_chapter and chapter_num > end_chapter:
                continue
            filtered_chapters.append((chapter_num, start_pos, title))
        chapter_info = filtered_chapters
    
    print(f"处理章节范围: 第{chapter_info[0][0]}章 - 第{chapter_info[-1][0]}章")
    print(f"共 {len(chapter_info)} 个章节")
    
    # 创建输出目录
    output_dir = Path(input_file).parent / "split_chapters"
    output_dir.mkdir(exist_ok=True)
    
    # 按照每50章分组
    for i in range(0, len(chapter_info), chapters_per_file):
        # 计算当前组的章节范围
        start_chapter = chapter_info[i][0]
        end_idx = min(i + chapters_per_file - 1, len(chapter_info) - 1)
        end_chapter = chapter_info[end_idx][0]
        
        # 确定文本截取范围
        start_pos = chapter_info[i][1]
        if end_idx + 1 < len(chapter_info):
            end_pos = chapter_info[end_idx + 1][1]
        else:
            end_pos = len(content)
        
        # 截取对应的文本内容
        chapter_content = content[start_pos:end_pos]
        
        # 生成输出文件名
        if chapters_per_file == 10:
            # 如果是10章分组，添加特殊标识
            output_filename = f"chapters_{start_chapter:03d}-{end_chapter:03d}_detailed.txt"
        elif chapters_per_file == 1:
            output_filename = f"chapter_{start_chapter:03d}_single.txt"
        else:
            output_filename = f"chapters_{start_chapter:03d}-{end_chapter:03d}.txt"
        output_path = output_dir / output_filename
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(chapter_content)
        
        print(f"已生成: {output_filename} (第{start_chapter}章 - 第{end_chapter}章)")

def main():
    import sys
    
    # 设置输入文件路径
    script_dir = Path(__file__).parent
    input_file = script_dir / "chapters" / "novel.txt"
    
    if not input_file.exists():
        print(f"错误: 找不到文件 {input_file}")
        return
    
    # 解析命令行参数
    chapters_per_file = 50
    start_chapter = None
    end_chapter = None
    
    if len(sys.argv) > 1:
        try:
            chapters_per_file = int(sys.argv[1])
        except ValueError:
            print("错误: 章节数必须是整数")
            return
    
    if len(sys.argv) > 2:
        try:
            start_chapter = int(sys.argv[2])
        except ValueError:
            print("错误: 起始章节号必须是整数")
            return
    
    if len(sys.argv) > 3:
        try:
            end_chapter = int(sys.argv[3])
        except ValueError:
            print("错误: 结束章节号必须是整数")
            return
    
    print(f"开始处理文件: {input_file}")
    print(f"分组设置: 每{chapters_per_file}章一个文件")
    if start_chapter:
        print(f"起始章节: 第{start_chapter}章")
    if end_chapter:
        print(f"结束章节: 第{end_chapter}章")
    
    split_novel_by_chapters(str(input_file), chapters_per_file=chapters_per_file, 
                          start_chapter=start_chapter, end_chapter=end_chapter)
    print("分章完成!")

if __name__ == "__main__":
    main()