#!/usr/bin/env python3
"""
火山引擎图生图API测试脚本
演示如何从图片URL生成新图片并保存到本地
"""

import os
import sys
import logging
from pathlib import Path

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from volcengine_img2img_official import generate_image_from_url, VolcengineImg2ImgError

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_volcengine_img2img():
    """测试火山引擎图生图API"""
    
    print("=" * 60)
    print("火山引擎图生图3.0-人像写真 API 测试")
    print("=" * 60)
    
    # 配置参数 - 请替换为您的实际密钥
    ACCESS_KEY_ID = os.getenv("VOLCENGINE_ACCESS_KEY_ID", "")
    SECRET_ACCESS_KEY = os.getenv("VOLCENGINE_SECRET_ACCESS_KEY", "")
    
    # 检查密钥配置
    if ACCESS_KEY_ID == "YOUR_ACCESS_KEY_ID" or SECRET_ACCESS_KEY == "YOUR_SECRET_ACCESS_KEY":
        print("❌ 错误: 请设置正确的火山引擎访问密钥")
        print("方法1: 设置环境变量:")
        print("  export VOLCENGINE_ACCESS_KEY_ID='your_access_key_id'")
        print("  export VOLCENGINE_SECRET_ACCESS_KEY='your_secret_access_key'")
        print("方法2: 直接修改脚本中的ACCESS_KEY_ID和SECRET_ACCESS_KEY变量")
        return False
    
    # 测试用例
    test_cases = [
        {
            "name": "人像写真测试",
            "image_url": "http://zhuluoji.cn-sh2.ufileos.com/test/qcc.jpeg",  # 请替换为实际的图片URL
            "output_path": "output/t1.jpg",
            "prompt": "白天阳光下的现代高楼天台，一位22岁长直发清秀女性身穿白色衬衫牛仔裤，站在天台边缘护栏旁，低头俯视下方密集的人群，表情困惑惊恐，急忙收回脚步，远景俯拍，紧张危险氛围，乙女动漫风格",
            "params": {
                "gpen": 0.5,
                "skin": 0.4,
                "skin_unifi": 0.2,
                "gen_mode": "reference_char",
                "width": 1920,
                "height": 1080
            }
        },
        {
            "name": "创意风格测试",
            "image_url": "http://zhuluoji.cn-sh2.ufileos.com/test/qcc.jpeg",  # 请替换为实际的图片URL
            "output_path": "output/t2.jpg",
            "prompt": "现代高楼天台边缘，一位长直发女性悬挂在护栏外侧抓住栏杆，表情恐惧绝望，身着商务装的成熟男性俯身紧紧抓住她的手腕奋力营救，眼眶泛红满脸紧张，天台背景，惊险刺激氛围，乙女动漫风格",
            "params": {
                "gpen": 0.3,
                "skin": 0.2,
                "skin_unifi": 0.0,
                "gen_mode": "reference_char",
                "width": 1920,
                "height": 1080
            }
        }
    ]
    
    # 确保输出目录存在
    os.makedirs("output", exist_ok=True)
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*50}")
        print(f"测试 {i}: {test_case['name']}")
        print(f"{'='*50}")
        
        try:
            print(f"📷 输入图片URL: {test_case['image_url']}")
            print(f"📝 提示词: {test_case['prompt']}")
            print(f"⚙️ 参数: {test_case['params']}")
            
            # 执行图生图
            saved_path = generate_image_from_url(
                image_url=test_case["image_url"],
                output_path=test_case["output_path"],
                access_key_id=ACCESS_KEY_ID,
                secret_access_key=SECRET_ACCESS_KEY,
                prompt=test_case["prompt"],
                **test_case["params"]
            )
            
            print(f"✅ 测试成功！生成的图片已保存到: {saved_path}")
            success_count += 1
            
        except VolcengineImg2ImgError as e:
            print(f"❌ API错误: {e}")
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            logger.error(f"测试异常: {e}", exc_info=True)
    
    # 测试总结
    print(f"\n{'='*60}")
    print(f"测试完成: {success_count}/{len(test_cases)} 个测试成功")
    print(f"{'='*60}")
    
    if success_count > 0:
        print("🎉 至少有一个测试成功，API工作正常！")
        
        # 显示输出文件
        output_files = list(Path("output").glob("test_*.jpg"))
        if output_files:
            print(f"\n📁 生成的文件:")
            for file in output_files:
                file_size = file.stat().st_size
                print(f"  - {file} ({file_size} bytes)")
    else:
        print("❌ 所有测试失败，请检查配置和网络连接")
    
    return success_count > 0


def test_with_sample_urls():
    """使用一些示例URL进行测试"""
    
    print("\n" + "=" * 60)
    print("使用示例URL测试")
    print("=" * 60)
    
    # 一些公开的示例图片URL（请根据实际情况替换）
    sample_urls = [
        {
            "url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400",
            "description": "男性肖像"
        },
        {
            "url": "https://images.unsplash.com/photo-1494790108755-2616b612b786?w=400", 
            "description": "女性肖像"
        }
    ]
    
    ACCESS_KEY_ID = os.getenv("VOLCENGINE_ACCESS_KEY_ID", "YOUR_ACCESS_KEY_ID")
    SECRET_ACCESS_KEY = os.getenv("VOLCENGINE_SECRET_ACCESS_KEY", "YOUR_SECRET_ACCESS_KEY")
    
    if ACCESS_KEY_ID == "YOUR_ACCESS_KEY_ID":
        print("❌ 请先配置访问密钥")
        return
    
    for i, sample in enumerate(sample_urls):
        print(f"\n📷 测试 {sample['description']}")
        print(f"URL: {sample['url']}")
        
        try:
            output_path = f"output/sample_{i+1}.jpg"
            saved_path = generate_image_from_url(
                image_url=sample["url"],
                output_path=output_path,
                access_key_id=ACCESS_KEY_ID,
                secret_access_key=SECRET_ACCESS_KEY,
                prompt=f"高质量{sample['description']}写真，专业摄影",
                gpen=0.4,
                skin=0.3,
                gen_mode="portrait"
            )
            print(f"✅ 成功: {saved_path}")
            
        except Exception as e:
            print(f"❌ 失败: {e}")


def main():
    """主函数"""
    print("🚀 开始测试火山引擎图生图API...")
    
    try:
        # 基本测试
        basic_success = test_volcengine_img2img()
        
        # 如果用户想要使用示例URL测试
        if basic_success:
            choice = input("\n是否使用示例URL进行额外测试? (y/N): ").strip().lower()
            if choice == 'y':
                test_with_sample_urls()
        
        print("\n🏁 所有测试完成！")
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生异常: {e}")
        logger.error(f"主函数异常: {e}", exc_info=True)


if __name__ == "__main__":
    main()