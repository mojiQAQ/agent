#!/usr/bin/env python3
"""
简化版测试脚本，用于调试火山引擎API问题
"""

import os
import json
import base64
import requests
from volcengine.visual.VisualService import VisualService

def test_simple():
    """简化测试"""
    
    ACCESS_KEY_ID = ""
    SECRET_ACCESS_KEY = ""
    
    # 创建服务
    visual_service = VisualService()
    visual_service.set_ak(ACCESS_KEY_ID)
    visual_service.set_sk(SECRET_ACCESS_KEY)
    
    # 下载测试图片
    image_url = "http://zhuluoji.cn-sh2.ufileos.com/test/qcc.jpeg"
    response = requests.get(image_url, timeout=30)
    image_base64 = base64.b64encode(response.content).decode('utf-8')
    print(f"图片大小: {len(response.content)} bytes")
    
    # 测试1: 最简参数
    form1 = {
        "req_key": "i2i_portrait_photo",
        "image_input": image_base64,
        "prompt": "高质量人像写真"
    }
    
    print("测试1: 最简参数")
    try:
        result1 = visual_service.cv_submit_task(form1)
        print(f"成功: {result1}")
    except Exception as e:
        print(f"失败: {e}")
    
    # 测试2: 完整参数
    form2 = {
        "req_key": "i2i_portrait_photo",
        "image_input": image_base64,
        "prompt": "高质量人像写真",
        "gpen": 0.4,
        "skin": 0.3,
        "width": 512,
        "height": 512,
        "gen_mode": "creative"
    }
    
    print("\n测试2: 完整参数")
    try:
        result2 = visual_service.cv_submit_task(form2)
        print(f"成功: {result2}")
    except Exception as e:
        print(f"失败: {e}")
    
    # 测试3: 尝试其他req_key
    form3 = {
        "req_key": "img2img_portrait_photo",
        "image_input": image_base64,
        "prompt": "高质量人像写真"
    }
    
    print("\n测试3: 其他req_key")
    try:
        result3 = visual_service.cv_submit_task(form3)
        print(f"成功: {result3}")
    except Exception as e:
        print(f"失败: {e}")

if __name__ == "__main__":
    test_simple()