import os
import json
import time
import requests
from pathlib import Path
from tqdm import tqdm
from loguru import logger

# 配置
API_KEY = os.getenv("CLAUDE_API_KEY")
API_URL = "https://globalai.vip/v1/chat/completions"
MODEL = "claude-sonnet-4-20250514"
SYSTEM_PROMPT_PATH = Path("chapters/prompt_image.md")
CHAPTERS_DIR = Path("chapters/processed")
OUTPUT_DIR = Path("chapters/processed")
MAX_RETRY = 1
RETRY_INTERVAL = 10  # seconds

def load_system_prompt():
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

def call_claude_api(system_prompt, user_input):
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "Authorization": f"Bearer {API_KEY}",
        "content-type": "application/json"
    }

    temp_json = """
    请直接按照以下*格式*输出，不要做多余的对话，不要输出任何解释

    {
    "批次信息": {
      "章节号": "第xx章",
      "章节标题": "计划赶不上变化",
      "处理场景数量": "16个场景",
      "人物特征库版本": "v1.1",
      "系统版本": "v3.0"
    },
    "场景提示词列表": [
      {
        "场景基本信息": {
          "场景序号": 1,
          "原场景编号": "1-1",
          "场景名称": "会客室初次见面",
          "对应段落": "神秘美女突然来访",
          "爽文元素": ["神秘身份开场"],
          "情绪强度": "好奇震撼"
        },
        "完整图片提示词": "现代写实动漫风格，anime style，冷色调，M国福克斯监狱会客室内部，白色墙壁监狱规章制度右上角监控摄像头左侧小窗户自然光冷白色调严肃感，金属会客桌占据中央干净整洁两把椅子相对黑色公文包访客登记簿，灰色水泥地面椅子腿金属反光高跟鞋帆布鞋对比，女主角陈若云28岁鹅蛋脸白皙透亮，深棕色大杏眼双眼皮聪慧坚定嘴角微扬职业友善，适中柳叶眉深棕色，小巧挺直精致鼻梁高挺微翘，适中嘴唇中等厚度，深棕色中长发微卷光泽顺滑偏分刘海优雅知性，白色职业衬衫黑色职业套裙黑色高跟鞋精致手表，位于画面左侧黄金分割点优雅端坐双手交叠桌面从容姿态，男主角周扬25岁方圆脸黄皮肤略显苍白，深黑色单凤眼双眼皮专注深邃震惊失神眉毛微扬薄唇微张惊讶，浓密剑眉深黑色，挺直鼻梁高挺立体，适中薄唇，深黑色短发略显凌乱粗糙无光泽无刘海额头露出，橙色短袖囚服橙色长裤囚服黑色帆布鞋，位于画面右侧边缘刚进入身体僵硬准备坐下"
      }
    ]
    }
    """


    dataSystem = {
        "model": MODEL,
        "max_tokens": 200000,
        # "system": system_prompt,
        "stop": ["EOF"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": temp_json}
        ],
        "temperature": 0.7
    }

    for attempt in range(MAX_RETRY):
        try:
            response = requests.post(API_URL, headers=headers, json=dataSystem)
            if response.status_code == 200:
                result = response.json()
                logger.info(result)
                if result.get("error"):
                    logger.error(f"API error: {result.get('error')}")
                logger.info(f"Total tokens: {result['usage']['total_tokens']}")
                logger.info(f"Prompt tokens: {result['usage']['prompt_tokens']}")
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"API error: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"Request failed: {e}")
        logger.info(f"Retrying in {RETRY_INTERVAL} seconds...")
        time.sleep(RETRY_INTERVAL)
    raise RuntimeError("Claude API failed after retries.")

def main():
    if not API_KEY:
        logger.error("请先设置环境变量 CLAUDE_API_KEY")
        return

    system_prompt = load_system_prompt()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chapter_files = sorted(CHAPTERS_DIR.glob("chapter_*_processed.json"))
    logger.info(f"共检测到 {len(chapter_files)} 个章节文件。")

    for chapter_file in tqdm(chapter_files, desc="Processing chapters"):
        output_file = OUTPUT_DIR / (chapter_file.stem.replace("_processed", "") + "_image.json")
        if output_file.exists():
            logger.info(f"{output_file} 已存在，跳过")
            continue  # 跳过已生成
        with open(chapter_file, "r", encoding="utf-8") as f:
            user_input = f.read()
        try:
            logger.info(f"Processing {chapter_file.name}")
            result = call_claude_api(system_prompt, user_input)
            # 尝试解析为JSON，如果失败则原样保存
            try:
                result = result.replace("```json", "").replace("```", "")
                json_obj = json.loads(result)
                with open(output_file, "w", encoding="utf-8") as out_f:
                    logger.info(json_obj)
                    json.dump(json_obj, out_f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.error(f"解析JSON失败: {e}")
                with open(output_file, "w", encoding="utf-8") as out_f:
                    out_f.write(result)
            time.sleep(1.5)  # 防止触发速率限制
        except Exception as e:
            logger.error(f"处理 {chapter_file.name} 失败: {e}")

if __name__ == "__main__":
    main()
