#!/usr/bin/env python3
"""
简化版火山引擎图生图3.0-人像写真 API客户端
专门用于从图片URL生成图片并保存到本地
"""

import os
import json
import time
import hashlib
import hmac
import base64
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VolcengineImg2ImgError(Exception):
    """Volcengine图生图API异常"""
    pass


class SimpleVolcengineImg2Img:
    """简化版火山引擎图生图API客户端"""
    
    def __init__(self, access_key_id: str, secret_access_key: str, region: str = "cn-north-1"):
        """
        初始化API客户端
        
        Args:
            access_key_id: 访问密钥ID
            secret_access_key: 访问密钥
            region: 地域
        """
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        
        # API配置
        self.endpoint = "https://visual.volcengineapi.com"
        self.version = "2022-08-31"
        self.action = "CVSync2AsyncSubmitTask"
        
        logger.info(f"Volcengine图生图API客户端初始化完成")
    
    def _generate_signature(self, method: str, uri: str, query: str, headers: Dict[str, str], body: str) -> str:
        """
        生成API请求签名
        
        Args:
            method: HTTP方法
            uri: 请求URI
            query: 查询参数
            headers: 请求头
            body: 请求体
            
        Returns:
            签名字符串
        """
        # 构建待签名字符串
        canonical_headers = '\n'.join([f"{k.lower()}:{v}" for k, v in sorted(headers.items())])
        signed_headers = ';'.join([k.lower() for k in sorted(headers.keys())])
        
        payload_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
        
        canonical_request = f"{method}\n{uri}\n{query}\n{canonical_headers}\n\n{signed_headers}\n{payload_hash}"
        
        # 创建签名字符串
        timestamp = headers.get('X-Date', datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'))
        date = timestamp[:8]
        credential_scope = f"{date}/{self.region}/visual/request"
        string_to_sign = f"HMAC-SHA256\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # 计算签名
        def sign(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
        
        kdate = sign(f"Volc{self.secret_access_key}".encode('utf-8'), date)
        kregion = sign(kdate, self.region)
        kservice = sign(kregion, "visual")
        ksigning = sign(kservice, "request")
        
        signature = hmac.new(ksigning, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        return f"HMAC-SHA256 Credential={self.access_key_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
    
    def _download_image_as_base64(self, image_url: str) -> str:
        """
        下载图片并转换为base64格式
        
        Args:
            image_url: 图片URL
            
        Returns:
            base64编码的图片数据
        """
        try:
            logger.info(f"下载图片: {image_url}")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # 转换为base64
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            logger.info(f"图片下载成功，大小: {len(response.content)} bytes")
            return image_base64
            
        except Exception as e:
            raise VolcengineImg2ImgError(f"下载图片失败: {e}")
    
    def image_to_image(self, 
                      image_url: str,
                      prompt: str = "",
                      gpen: float = 0.4,
                      skin: float = 0.3,
                      skin_unifi: float = 0.0,
                      width: int = 1024,
                      height: int = 1024,
                      gen_mode: str = "creative",
                      seed: int = -1) -> Dict[str, Any]:
        """
        执行图生图转换
        
        Args:
            image_url: 源图像URL
            prompt: 提示词描述
            gpen: 人脸增强参数 (0.0-1.0)
            skin: 皮肤参数 (0.0-1.0)
            skin_unifi: 皮肤统一参数 (0.0-1.0)
            width: 输出图像宽度
            height: 输出图像高度
            gen_mode: 生成模式 (creative/portrait/professional/artistic)
            seed: 随机种子，-1表示随机
            
        Returns:
            API响应结果
        """
        # 下载图片并转换为base64
        image_base64 = self._download_image_as_base64(image_url)
        
        # 构建请求参数
        params = {
            "req_key": "i2i_portrait_photo",
            "image_input": image_base64,
            "prompt": prompt,
            "gpen": max(0.0, min(1.0, gpen)),
            "skin": max(0.0, min(1.0, skin)),
            "skin_unifi": max(0.0, min(1.0, skin_unifi)),
            "width": width,
            "height": height,
            "gen_mode": gen_mode,
            "seed": seed
        }
        
        # 构建请求
        uri = "/"
        query = f"Action={self.action}&Version={self.version}"
        body = json.dumps(params)
        
        headers = {
            "Content-Type": "application/json",
            "Host": self.endpoint.replace("https://", "").replace("http://", ""),
            "X-Date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        }
        
        # 生成签名
        try:
            authorization = self._generate_signature("POST", uri, query, headers, body)
            headers["Authorization"] = authorization
        except Exception as e:
            raise VolcengineImg2ImgError(f"生成签名失败: {e}")
        
        # 发送请求
        url = f"{self.endpoint}{uri}?{query}"
        
        try:
            logger.info(f"发送图生图请求: {url}")
            response = requests.post(url, headers=headers, data=body, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("ResponseMetadata", {}).get("Error"):
                error_info = result["ResponseMetadata"]["Error"]
                error_msg = error_info.get("Message", "未知错误")
                raise VolcengineImg2ImgError(f"API请求失败: {error_msg}")
            
            logger.info("图生图请求成功")
            return result
                
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            raise VolcengineImg2ImgError(f"网络请求失败: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"响应解析失败: {e}")
            raise VolcengineImg2ImgError(f"响应解析失败: {e}")
    
    def save_result(self, result: Dict[str, Any], output_path: str) -> str:
        """
        保存API结果到文件
        
        Args:
            result: API响应结果
            output_path: 输出文件路径
            
        Returns:
            保存的文件路径
        """
        try:
            # 提取图像数据 - 根据实际API响应格式调整
            image_data = None
            
            # 尝试不同的响应格式
            if "Result" in result and "image_urls" in result["Result"]:
                # 如果返回的是图片URL
                image_urls = result["Result"]["image_urls"]
                if image_urls:
                    image_url = image_urls[0]
                    logger.info(f"从URL下载结果图片: {image_url}")
                    response = requests.get(image_url, timeout=30)
                    response.raise_for_status()
                    image_data = response.content
            
            elif "Result" in result and "image" in result["Result"]:
                # 如果返回的是base64数据
                image_b64 = result["Result"]["image"]
                if image_b64.startswith('data:image'):
                    image_b64 = image_b64.split(',', 1)[1]
                image_data = base64.b64decode(image_b64)
            
            elif "data" in result and "image" in result["data"]:
                # 另一种可能的格式
                image_b64 = result["data"]["image"]
                if image_b64.startswith('data:image'):
                    image_b64 = image_b64.split(',', 1)[1]
                image_data = base64.b64decode(image_b64)
            
            if image_data:
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                
                logger.info(f"结果已保存到: {output_path}")
                return output_path
            else:
                # 如果没有找到图像数据，保存完整的响应用于调试
                debug_path = output_path.replace('.jpg', '_debug.json')
                with open(debug_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                raise VolcengineImg2ImgError(f"响应中没有找到图像数据，完整响应已保存到: {debug_path}")
                
        except Exception as e:
            raise VolcengineImg2ImgError(f"保存结果失败: {e}")


def generate_image_from_url(image_url: str, 
                          output_path: str,
                          access_key_id: str,
                          secret_access_key: str,
                          prompt: str = "高质量人像写真",
                          **kwargs) -> str:
    """
    从图片URL生成新图片并保存到本地的便捷函数
    
    Args:
        image_url: 输入图片URL
        output_path: 输出文件路径
        access_key_id: 火山引擎访问密钥ID
        secret_access_key: 火山引擎访问密钥
        prompt: 生成提示词
        **kwargs: 其他参数
        
    Returns:
        保存的文件路径
    """
    try:
        # 创建客户端
        client = SimpleVolcengineImg2Img(access_key_id, secret_access_key)
        
        # 执行图生图
        result = client.image_to_image(
            image_url=image_url,
            prompt=prompt,
            **kwargs
        )
        
        # 保存结果
        saved_path = client.save_result(result, output_path)
        return saved_path
        
    except Exception as e:
        logger.error(f"图生图处理失败: {e}")
        raise


# 示例使用
if __name__ == "__main__":
    # 配置参数
    ACCESS_KEY_ID = "YOUR_ACCESS_KEY_ID"
    SECRET_ACCESS_KEY = "YOUR_SECRET_ACCESS_KEY"
    
    # 示例图片URL
    IMAGE_URL = "https://example.com/sample.jpg"
    
    # 输出路径
    OUTPUT_PATH = "output/generated_image.jpg"
    
    try:
        saved_path = generate_image_from_url(
            image_url=IMAGE_URL,
            output_path=OUTPUT_PATH,
            access_key_id=ACCESS_KEY_ID,
            secret_access_key=SECRET_ACCESS_KEY,
            prompt="美丽的人像写真，专业摄影，高质量",
            gpen=0.4,
            skin=0.3,
            gen_mode="portrait",
            width=1024,
            height=1024
        )
        print(f"生成成功！图片已保存到: {saved_path}")
        
    except Exception as e:
        print(f"生成失败: {e}")