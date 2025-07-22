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
SYSTEM_PROMPT_PATH = Path("chapters/prompt_change.md")
CHAPTERS_DIR = Path("chapters/split_chapters")
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
    dataSystem = {
        "model": MODEL,
        "max_tokens": 200000,
        # "system": system_prompt,
        "stop": ["EOF"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "好的，我明白了。我将根据您输入的小说按照您提供的输出格式进行输出。并且不要缺少段落，保证生成的段落数量完整。"},
            {"role": "user", "content": user_input},
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

    chapter_files = sorted(CHAPTERS_DIR.glob("chapter_*_detailed.txt"))
    logger.info(f"共检测到 {len(chapter_files)} 个章节文件。")

    for chapter_file in tqdm(chapter_files, desc="Processing chapters"):
        output_file = OUTPUT_DIR / (chapter_file.stem.replace("_detailed", "") + "_processed.json")
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
                    json.dump(json_obj, out_f, ensure_ascii=False)
            except Exception as e:
                logger.error(f"解析JSON失败: {e}")
                with open(output_file, "w", encoding="utf-8") as out_f:
                    out_f.write(result)
            time.sleep(1.5)  # 防止触发速率限制
        except Exception as e:
            logger.error(f"处理 {chapter_file.name} 失败: {e}")

if __name__ == "__main__":
    main()
