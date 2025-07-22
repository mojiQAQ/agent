import json
from pathlib import Path

def update_processed_with_image_prompt(processed_path, image_path, output_path=None):
    """
    将 image_path 中每个场景的“完整图片提示词”补充到 processed_path 的每个场景的“图片提示词”字段。
    如果 output_path 未指定，则覆盖 processed_path。
    """
    with open(processed_path, 'r', encoding='utf-8') as f:
        processed_data = json.load(f)
    with open(image_path, 'r', encoding='utf-8') as f:
        image_data = json.load(f)

    # 构建 (原场景编号, 完整图片提示词) 映射
    image_prompt_map = {}
    for scene in image_data["场景提示词列表"]:
        scene_info = scene["场景基本信息"]
        scene_id = scene_info["原场景编号"]
        image_prompt = scene["完整图片提示词"]
        image_prompt_map[scene_id] = image_prompt

    # 遍历 processed_data，补充图片提示词
    for para in processed_data["场景拆解"]:
        for scene in para["场景列表"]:
            scene_id = scene["场景编号"]
            if "图片提示词" not in scene or not scene["图片提示词"]:
                # 只在原本没有图片提示词时补充
                if scene_id in image_prompt_map:
                    scene["图片提示词"] = image_prompt_map[scene_id]

    # 保存
    if not output_path:
        output_path = processed_path
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)
    print(f"已补充图片提示词: {output_path}")

# 用法示例：
# update_processed_with_image_prompt('chapters/processed/chapter_001_processed.json', 'chapters/processed/chapter_001_image.json') 

if __name__ == "__main__":
    # update_processed_with_image_prompt('chapters/processed/chapter_001_processed.json', 'chapters/processed/chapter_001_image.json')
    update_processed_with_image_prompt('chapters/processed/chapter_002_processed.json', 'chapters/processed/chapter_002_image.json')
    update_processed_with_image_prompt('chapters/processed/chapter_003_processed.json', 'chapters/processed/chapter_003_image.json')
    update_processed_with_image_prompt('chapters/processed/chapter_004_processed.json', 'chapters/processed/chapter_004_image.json')
    update_processed_with_image_prompt('chapters/processed/chapter_005_processed.json', 'chapters/processed/chapter_005_image.json')