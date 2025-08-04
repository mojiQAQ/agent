import os
import json
import time
import requests
from pathlib import Path
from tqdm import tqdm
from loguru import logger

# 配置
API_KEY = os.getenv("CLAUDE_API_KEY")
API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
MODEL = "doubao-1.5-pro-256k-250115"
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

    temp_json = """
    请直接按照以下格式输出，不要做多余的对话，不要输出任何解释。也不能偷懒，要把所有的段落和场景都完全生成，最大不要超过15个场景。

{
  "章节信息": {
    "章节号": "第12章",
    "标题": "B计划，强突总部",
    "原文字数": "1680字",
    "改写字数": "980字",
    "总时长估计": "2分56秒-3分16秒",
    "段落数量": "16个",
    "爽文元素": [
      "精英小队",
      "神兵天降",
      "以少敌多",
      "完美配合",
      "强攻总部",
      "震撼救援"
    ]
  },
  "人物特征库": {
    "胡正平": {
      "基本信息": {
        "年龄": "35岁",
        "性别": "男性",
        "身高": "178cm",
        "体型": "精壮匀称，肌肉结实"
      },
      "面部特征": {
        "脸型": "国字脸",
        "肤色": "小麦色健康肤色",
        "眼睛": {
          "颜色": "深褐色",
          "大小": "中等大小",
          "形状": "丹凤眼",
          "特征": "双眼皮，眼神锐利坚毅"
        },
        "眉毛": {
          "形状": "剑眉",
          "浓度": "浓密",
          "颜色": "深黑色"
        },
        "鼻子": {
          "形状": "鹰钩鼻",
          "大小": "中等偏大",
          "特征": "鼻梁高挺有棱角"
        },
        "嘴巴": {
          "大小": "中等",
          "嘴唇": "薄唇",
          "颜色": "自然色"
        },
        "耳朵": {
          "大小": "中等",
          "状态": "完全露出"
        }
      },
      "头发特征": {
        "颜色": "深黑色",
        "发型": "军人寸头",
        "质感": "粗硬有型",
        "刘海": "无刘海，额头完全露出"
      },
      "服装风格": {
        "上衣": "黑色战术背心",
        "下装": "军绿色战术裤",
        "鞋子": "黑色战术靴",
        "配饰": "战术头盔、护目镜、通讯耳机",
        "整体风格": "全副武装特种兵"
      },
      "性格标签": "冷静、果断、责任感强、指挥能力出众"
    },
    "黑鸟": {
      "基本信息": {
        "年龄": "29岁",
        "性别": "男性",
        "身高": "175cm",
        "体型": "精瘦灵活，动作敏捷"
      },
      "面部特征": {
        "脸型": "瓜子脸",
        "肤色": "健康肤色",
        "眼睛": {
          "颜色": "深黑色",
          "大小": "中等大小",
          "形状": "单凤眼",
          "特征": "双眼皮，眼神机敏专注"
        },
        "眉毛": {
          "形状": "一字眉",
          "浓度": "中等浓密",
          "颜色": "深黑色"
        },
        "鼻子": {
          "形状": "直鼻",
          "大小": "适中",
          "特征": "鼻梁挺直"
        },
        "嘴巴": {
          "大小": "适中",
          "嘴唇": "中等厚度",
          "颜色": "自然色"
        },
        "耳朵": {
          "大小": "中等",
          "状态": "完全露出"
        }
      },
      "头发特征": {
        "颜色": "深黑色",
        "发型": "军人寸头",
        "质感": "粗硬整齐",
        "刘海": "无刘海"
      },
      "服装风格": {
        "上衣": "黑色战术背心",
        "下装": "军绿色战术裤",
        "鞋子": "黑色战术靴",
        "配饰": "战术头盔、护目镜、通讯耳机",
        "整体风格": "全副武装特种兵"
      },
      "性格标签": "敏捷、忠诚、执行力强、团队精神"
    },
    "铁牛": {
      "基本信息": {
        "年龄": "32岁",
        "性别": "男性",
        "身高": "185cm",
        "体型": "魁梧壮实，肌肉发达"
      },
      "面部特征": {
        "脸型": "方脸",
        "肤色": "古铜色",
        "眼睛": {
          "颜色": "深褐色",
          "大小": "大眼睛",
          "形状": "圆眼",
          "特征": "双眼皮，眼神坚定有力"
        },
        "眉毛": {
          "形状": "浓眉",
          "浓度": "非常浓密",
          "颜色": "深黑色"
        },
        "鼻子": {
          "形状": "大鼻",
          "大小": "较大",
          "特征": "鼻翼宽厚"
        },
        "嘴巴": {
          "大小": "大嘴",
          "嘴唇": "厚唇",
          "颜色": "自然色"
        },
        "耳朵": {
          "大小": "中等",
          "状态": "完全露出"
        }
      },
      "头发特征": {
        "颜色": "深黑色",
        "发型": "军人寸头",
        "质感": "粗硬浓密",
        "刘海": "无刘海"
      },
      "服装风格": {
        "上衣": "黑色战术背心",
        "下装": "军绿色战术裤",
        "鞋子": "黑色战术靴",
        "配饰": "战术头盔、护目镜、通讯耳机",
        "整体风格": "全副武装特种兵"
      },
      "性格标签": "勇猛、可靠、力量型、保护欲强"
    },
    "周扬": {
      "基本信息": {
        "年龄": "25岁",
        "性别": "男性",
        "身高": "175cm",
        "体型": "中等偏瘦，身材匀称"
      },
      "面部特征": {
        "脸型": "方圆脸",
        "肤色": "黄皮肤，略显苍白疲惫",
        "眼睛": {
          "颜色": "深黑色",
          "大小": "中等大小",
          "形状": "单凤眼",
          "特征": "双眼皮，眼神疲惫但清明"
        },
        "眉毛": {
          "形状": "剑眉",
          "浓度": "浓密",
          "颜色": "深黑色"
        },
        "鼻子": {
          "形状": "挺直",
          "大小": "适中",
          "特征": "鼻梁高挺有立体感"
        },
        "嘴巴": {
          "大小": "适中",
          "嘴唇": "薄唇",
          "颜色": "略显干燥"
        },
        "耳朵": {
          "大小": "中等",
          "状态": "完全露出"
        }
      },
      "头发特征": {
        "颜色": "深黑色",
        "发型": "短发，略显凌乱",
        "质感": "粗糙，缺乏光泽",
        "刘海": "无刘海，额头完全露出"
      },
      "服装风格": {
        "上衣": "白色衬衫，略显皱褶",
        "下装": "深蓝色牛仔裤",
        "鞋子": "白色运动鞋",
        "配饰": "无",
        "整体风格": "普通便装，略显疲惫"
      },
      "性格标签": "天才、坚韧、疲惫、震惊"
    }
  },
  "场景拆解": [
    {
      "序号": 1,
      "段落标题": "废弃工厂的精英待命",
      "场景时长": "12秒",
      "段落字数": "58字",
      "爽文元素": "精英小队神秘感",
      "情绪强度": "紧张待命",
      "场景文案": "废弃工厂内，蛟龙特种小队五名精英战士已待命一天一夜。他们装备精良，纪律严明，即使休息时也保持着随时战斗的警觉状态，手中武器从不离身。",
      "场景列表": [
        {
          "场景编号": "1-1",
          "场景名称": "废弃工厂待命",
          "环境设定": {
            "时间": "深夜23:00",
            "地点": "城郊废弃工厂内部",
            "天气": "室内环境，略显阴冷",
            "氛围": "紧张待命，专业肃杀",
            "光线": "昏暗的临时照明灯光"
          },
          "人物状态": [
            {
              "人物": "胡正平",
              "详细外貌": "35岁国字脸小麦色健康肤色男性，深褐色丹凤眼双眼皮锐利坚毅，浓密剑眉深黑色，鹰钩鼻中等偏大高挺有棱角，中等薄唇自然色，深黑色军人寸头粗硬有型无刘海额头露出",
              "服装": "黑色战术背心，军绿色战术裤，黑色战术靴，战术头盔护目镜通讯耳机",
              "动作": "坐在临时椅子上看电视，身体保持警觉姿态",
              "表情": "深褐色丹凤眼专注屏幕，浓密剑眉微蹙，薄唇紧抿显示高度戒备",
              "画面位置": "位于画面中央偏左，占据中景主要位置"
            }
          ],
          "画面构图": {
            "画面比例": "4:3",
            "镜头类型": "中景群像",
            "视角高度": "与人物视线平齐的水平角度",
            "焦点位置": "胡正平位于画面左侧黄金分割点"
          },
          "背景环境详细布局": {
            "远景背景": {
              "位置": "画面上1/3区域",
              "内容": "废弃工厂高大水泥墙壁，破损窗户透进微弱月光，生锈钢架结构，蛛网和尘埃",
              "色调": "暗灰色调带荒废感"
            },
            "中景环境": {
              "位置": "画面中1/3区域",
              "内容": "临时设置的简易桌椅，小型电视机，扑克牌散落桌面，军用背包整齐摆放",
              "道具分布": "左侧武器架放置突击步枪，右侧通讯设备和地图"
            },
            "近景前景": {
              "位置": "画面下1/3区域",
              "内容": "水泥地面裂缝和积尘，战术靴印痕，散落的烟蒂和水瓶",
              "细节": "可见地面的真实质感和使用痕迹"
            }
          },
          "人物关系与空间": {
            "主要人物": "胡正平为中心，其他队员分散休息",
            "人物朝向": "胡正平面向电视，身体略向前倾保持警觉",
            "与环境关系": "坐在临时椅子上，与电视距离约2米",
            "空间感": "废弃工厂内的临时驻扎点"
          },
          "光影效果": {
            "主光源": "临时照明灯斜射，在人物脸部形成明暗对比",
            "环境光": "破损窗户透进的微弱月光作为辅助光源",
            "色温": "3000K暖光与5000K月光混合，营造紧张氛围",
            "阴影分布": "人物背部和设备后方形成深色阴影，增强立体感"
          },
          "场景描述": "4:3画面比例中景群像，临时照明灯斜射的废弃工厂内部。画面上1/3暗灰色水泥墙壁破损窗户微弱月光生锈钢架蛛网尘埃荒废感，中1/3临时桌椅小型电视扑克牌军用背包左侧武器架右侧通讯设备地图，下1/3水泥地面裂缝积尘战术靴印烟蒂水瓶真实质感。35岁国字脸小麦色男性深黑色寸头，深褐色丹凤眼专注锐利浓密剑眉微蹙薄唇紧抿高度戒备，黑色战术背心军绿战术裤黑色战术靴战术装备，位于画面左侧黄金分割点坐临时椅子看电视身体前倾警觉，3000K暖光5000K月光混合营造紧张氛围，写实军事风格",
          "镜头建议": "中景群像，焦点在胡正平和战术装备，突出精英小队的专业素养和待命状态",
          "图片提示词": "现代写实军事风格，realistic military style，冷色调，废弃工厂内部深夜环境，破损水泥墙壁生锈钢架结构蛛网尘埃荒废感暗灰色调，临时设置简易桌椅小型电视机扑克牌散落桌面军用背包整齐摆放左侧武器架突击步枪右侧通讯设备地图，水泥地面裂缝积尘战术靴印痕散落烟蒂水瓶真实质感使用痕迹，35岁国字脸小麦色健康肤色男性胡正平，深褐色丹凤眼双眼皮锐利坚毅专注屏幕浓密剑眉深黑色微蹙薄唇中等自然色紧抿高度戒备，鹰钩鼻中等偏大高挺有棱角，深黑色军人寸头粗硬有型无刘海额头完全露出，黑色战术背心军绿色战术裤黑色战术靴战术头盔护目镜通讯耳机，位于画面左侧黄金分割点坐临时椅子看电视身体略向前倾保持警觉距离电视约2米，3000K暖光5000K月光混合营造紧张氛围临时照明灯斜射人物脸部明暗对比破损窗户微弱月光辅助光源"
        }
      ]
    }
  ]
}
    """


    dataSystem = {
        "model": MODEL,
        "thinking": {
            "type": "enabled"
        },
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
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
