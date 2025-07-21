import os
import json
import time
import requests
from pathlib import Path
from tqdm import tqdm

# 配置
API_KEY = os.getenv("CLAUDE_API_KEY")
API_URL = "https://globalai.vip/v1/chat/completions"
MODEL = "claude-opus-4-20250514-thinking"
SYSTEM_PROMPT_PATH = Path("chapters/prompt_change.md")
CHAPTERS_DIR = Path("chapters/split_chapters")
OUTPUT_DIR = Path("chapters/processed")
MAX_RETRY = 3
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
    data = {
        "model": MODEL,
        "max_tokens": 40960,
        # "system": system_prompt,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.2
    }
    for attempt in range(MAX_RETRY):
        try:
            response = requests.post(API_URL, headers=headers, json=data, timeout=120)
            if response.status_code == 200:
                return response.json()["content"][0]["text"]
            else:
                print(f"API error: {response.status_code} {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")
        print(f"Retrying in {RETRY_INTERVAL} seconds...")
        time.sleep(RETRY_INTERVAL)
    raise RuntimeError("Claude API failed after retries.")

def main():
    if not API_KEY:
        print("请先设置环境变量 CLAUDE_API_KEY")
        return

    system_prompt = load_system_prompt()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chapter_files = sorted(CHAPTERS_DIR.glob("chapter_*_detailed.txt"))
    print(f"共检测到 {len(chapter_files)} 个章节文件。")

    for chapter_file in tqdm(chapter_files, desc="Processing chapters"):
        output_file = OUTPUT_DIR / (chapter_file.stem.replace("_detailed", "") + "_processed.json")
        if output_file.exists():
            continue  # 跳过已生成
        with open(chapter_file, "r", encoding="utf-8") as f:
            user_input = f.read()
        try:
            result = call_claude_api(system_prompt, user_input)
            # 尝试解析为JSON，如果失败则原样保存
            try:
                json_obj = json.loads(result)
                with open(output_file, "w", encoding="utf-8") as out_f:
                    json.dump(json_obj, out_f, ensure_ascii=False, indent=2)
            except Exception:
                with open(output_file, "w", encoding="utf-8") as out_f:
                    out_f.write(result)
            time.sleep(1.5)  # 防止触发速率限制
        except Exception as e:
            print(f"处理 {chapter_file.name} 失败: {e}")

if __name__ == "__main__":
    main()
