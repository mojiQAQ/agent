#!/usr/bin/env python3
"""
为 chapter21-40 的每个场景补充主角和重点展现信息
严格参考 chapter1 的格式
"""

import json
import os
from pathlib import Path

def analyze_scene_main_character(scene_data):
    """分析场景的主角和重点展现"""
    scene_name = scene_data.get("场景名称", "")
    people_states = scene_data.get("人物状态", [])
    
    # 优先判断主角
    main_character = "乔楚楚"
    key_focus = "清秀女性形象"
    
    # 根据人物状态判断主角
    if people_states:
        # 如果只有一个人物，就是主角
        if len(people_states) == 1:
            main_character = people_states[0].get("人物", "乔楚楚")
        else:
            # 如果有多个人物，优先选择乔楚楚，其次是沈卿
            for person in people_states:
                if person.get("人物") == "乔楚楚":
                    main_character = "乔楚楚"
                    break
                elif person.get("人物") == "沈卿":
                    main_character = "沈卿"
    
    # 根据主角生成重点展现
    if main_character == "乔楚楚":
        # 根据场景名称和动作确定重点展现
        if any(keyword in scene_name for keyword in ["哭泣", "委屈", "泪"]):
            key_focus = "委屈哭泣的女性情感"
        elif any(keyword in scene_name for keyword in ["害羞", "脸红", "羞"]):
            key_focus = "害羞脸红的清秀女性"
        elif any(keyword in scene_name for keyword in ["愤怒", "生气", "怒"]):
            key_focus = "愤怒表情的女性形象"
        elif any(keyword in scene_name for keyword in ["工作", "实验", "专心"]):
            key_focus = "专心工作的女性形象"
        elif any(keyword in scene_name for keyword in ["无视", "冷漠", "不理"]):
            key_focus = "冷漠无视的女性态度"
        elif any(keyword in scene_name for keyword in ["洗澡", "睡衣", "衬衫"]):
            key_focus = "居家状态的女性魅力"
        elif any(keyword in scene_name for keyword in ["视死如归", "决绝", "反抗"]):
            key_focus = "决绝反抗的女性气质"
        elif any(keyword in scene_name for keyword in ["严肃", "质疑", "问"]):
            key_focus = "严肃质疑的女性表情"
        else:
            key_focus = "清秀女性形象"
    
    elif main_character == "沈卿":
        # 根据场景名称和动作确定重点展现
        if any(keyword in scene_name for keyword in ["守护", "门外", "等待"]):
            key_focus = "守护等待的男性深情"
        elif any(keyword in scene_name for keyword in ["憔悴", "疲惫", "狼狈"]):
            key_focus = "憔悴疲惫的男性形象"
        elif any(keyword in scene_name for keyword in ["道歉", "请求", "解释"]):
            key_focus = "道歉请求的男性真诚"
        elif any(keyword in scene_name for keyword in ["高调", "示爱", "玫瑰"]):
            key_focus = "高调示爱的霸总形象"
        elif any(keyword in scene_name for keyword in ["工作", "办公", "心不在焉"]):
            key_focus = "工作状态的精英男性"
        elif any(keyword in scene_name for keyword in ["无奈", "困惑", "懵"]):
            key_focus = "无奈困惑的男性表情"
        else:
            key_focus = "英气男性形象"
    
    else:
        # 其他角色的处理
        if "姚佩佩" in main_character:
            key_focus = "活泼八卦的女性形象"
        elif "乔瑛瑛" in main_character:
            key_focus = "嫉妒愤怒的女性形象"
        elif "沈母" in main_character:
            key_focus = "调皮母亲的形象"
        elif "林子源" in main_character:
            key_focus = "损友调侃的男性形象"
        elif "营长" in main_character:
            key_focus = "职场精英的男性形象"
        else:
            key_focus = "配角人物形象"
    
    return main_character, key_focus

def update_chapter_scenes(chapter_file_path):
    """更新章节文件中的场景主角信息"""
    try:
        with open(chapter_file_path, 'r', encoding='utf-8') as f:
            chapter_data = json.load(f)
        
        # 更新场景拆解中的每个场景
        for paragraph in chapter_data.get("场景拆解", []):
            for scene in paragraph.get("场景列表", []):
                if "主角" not in scene or "重点展现" not in scene:
                    main_character, key_focus = analyze_scene_main_character(scene)
                    scene["主角"] = main_character
                    scene["重点展现"] = key_focus
        
        # 保存更新后的文件
        with open(chapter_file_path, 'w', encoding='utf-8') as f:
            json.dump(chapter_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 更新完成: {chapter_file_path}")
        return True
        
    except Exception as e:
        print(f"❌ 更新失败: {chapter_file_path}, 错误: {e}")
        return False

def main():
    """主函数：批量更新所有章节"""
    chapters_dir = Path("/Users/moji/ground/agent/chapters")
    
    # 需要更新的章节文件列表
    chapter_files = []
    for i in range(21, 41):
        chapter_files.append(f"chapter{i}_breakdown.json")
    
    success_count = 0
    total_count = len(chapter_files)
    
    print(f"开始更新 {total_count} 个章节文件...")
    
    for chapter_file in chapter_files:
        file_path = chapters_dir / chapter_file
        if file_path.exists():
            if update_chapter_scenes(file_path):
                success_count += 1
        else:
            print(f"⚠️ 文件不存在: {file_path}")
    
    print(f"\n更新完成！成功: {success_count}/{total_count}")

if __name__ == "__main__":
    main()