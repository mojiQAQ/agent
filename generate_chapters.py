#!/usr/bin/env python3
"""
根据21-40.txt内容和prompt_optimized.md格式生成章节拆解文件
"""

import json
import re
from pathlib import Path

def extract_chapter_content(file_path, chapter_num):
    """提取指定章节的内容"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找章节开始和结束位置
    start_pattern = f"第{chapter_num}章"
    end_pattern = f"第{chapter_num+1}章" if chapter_num < 40 else None
    
    start_pos = content.find(start_pattern)
    if start_pos == -1:
        return None
        
    if end_pattern:
        end_pos = content.find(end_pattern)
        if end_pos == -1:
            chapter_content = content[start_pos:]
        else:
            chapter_content = content[start_pos:end_pos]
    else:
        chapter_content = content[start_pos:]
    
    return chapter_content.strip()

def generate_basic_breakdown(chapter_num, content):
    """生成基本的章节拆解结构"""
    
    # 基本人物库
    character_base = {
        "乔楚楚": {
            "基础描述": "22岁女性，身高165cm，清秀面容，大眼睛，长直发，穿越者身份",
            "服装风格": "校园风格，白色衬衫配牛仔裤，简约现代",
            "特征标签": "机智、善良、内心独白丰富、容易脸红"
        },
        "沈卿": {
            "基础描述": "英气男性，剑眉星目，薄唇泛红，戴金属框眼镜，能听到楚楚内心声音",
            "服装风格": "黑色商务西装，居家时休闲装",
            "特征标签": "深沉、温柔、霸道、暗中保护"
        }
    }
    
    # 根据内容提取关键信息
    lines = content.split('\n')
    scenes = []
    current_scene = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('第'):
            continue
            
        # 检测场景分隔符
        if line == '……' or line == '...':
            if current_scene:
                scenes.append('\n'.join(current_scene))
                current_scene = []
        else:
            current_scene.append(line)
    
    if current_scene:
        scenes.append('\n'.join(current_scene))
    
    # 生成段落
    paragraphs = []
    for i, scene in enumerate(scenes[:6]):  # 限制最多6个段落
        # 简化的段落标题生成
        title = f"情节发展{i+1}"
        if "夏令营" in scene:
            title = "夏令营生活"
        elif "办公室" in scene:
            title = "办公室情节"
        elif "家" in scene or "公寓" in scene:
            title = "居家时光"
        elif "餐厅" in scene or "吃饭" in scene:
            title = "用餐时光"
        elif "实验" in scene:
            title = "实验室场景"
        
        # 提取人物对话和动作
        description = scene[:200] + "..." if len(scene) > 200 else scene
        
        paragraph = {
            "章节": f"第{chapter_num}章",
            "序号": i + 1,
            "段落标题": title,
            "场景时长": "90秒",
            "第三人称描述": description,
            "场景列表": [
                {
                    "场景编号": f"{chapter_num}-{i+1}",
                    "场景名称": title,
                    "环境设定": {
                        "时间": "白天",
                        "地点": "室内",
                        "天气": "室内",
                        "氛围": "温馨"
                    },
                    "人物状态": [
                        {
                            "人物": "乔楚楚",
                            "外貌": "22岁清秀女性，长直发，白色衬衫牛仔裤",
                            "动作": "参与情节发展",
                            "表情": "自然、真诚"
                        }
                    ],
                    "图片提示词": f"现代场景中，清秀长发女性身穿白衬衫牛仔裤参与{title}，温馨的环境氛围，乙女动漫风格",
                    "镜头建议": "中景镜头，展现人物互动"
                }
            ]
        }
        paragraphs.append(paragraph)
    
    # 生成完整结构
    breakdown = {
        "章节信息": {
            "章节范围": f"第{chapter_num}章",
            "标题集合": [f"第{chapter_num}章：故事发展"],
            "总时长估计": "8-10分钟"
        },
        "人物特征库": character_base,
        "场景拆解": paragraphs
    }
    
    return breakdown

def main():
    """主函数：生成第23-40章的拆解文件"""
    source_file = "/Users/moji/ground/agent/chapters/21-40.txt"
    output_dir = Path("/Users/moji/ground/agent/chapters")
    
    # 生成第23-40章
    for chapter_num in range(23, 41):
        print(f"正在生成第{chapter_num}章...")
        
        # 提取章节内容
        content = extract_chapter_content(source_file, chapter_num)
        if not content:
            print(f"第{chapter_num}章内容未找到，跳过")
            continue
        
        # 生成拆解结构
        breakdown = generate_basic_breakdown(chapter_num, content)
        
        # 保存文件
        output_file = output_dir / f"chapter{chapter_num}_breakdown.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(breakdown, f, ensure_ascii=False, indent=2)
        
        print(f"第{chapter_num}章拆解文件已生成: {output_file}")
    
    print("所有章节拆解文件生成完成！")

if __name__ == "__main__":
    main()