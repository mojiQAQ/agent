#!/usr/bin/env python3
"""
基于火山引擎官方Python SDK的图生图3.0-人像写真 API客户端
参考官方文档: https://www.volcengine.com/docs/85128/1602212
"""

import os
import json
import time
import base64
import requests
from typing import Dict, Any, Optional
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VolcengineImg2ImgError(Exception):
    """Volcengine图生图API异常"""
    pass


try:
    # 尝试导入官方SDK
    from volcengine.visual.VisualService import VisualService
    OFFICIAL_SDK_AVAILABLE = True
    logger.info("检测到官方SDK，将使用官方SDK")
except ImportError:
    OFFICIAL_SDK_AVAILABLE = False
    logger.warning("未检测到官方SDK，将使用简化实现")


class VolcengineImg2ImgOfficial:
    """基于官方SDK的火山引擎图生图API客户端"""
    
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
        
        if OFFICIAL_SDK_AVAILABLE:
            # 使用官方SDK
            self.visual_service = VisualService()
            self.visual_service.set_ak(access_key_id)
            self.visual_service.set_sk(secret_access_key)
            logger.info("使用官方SDK初始化成功")
        else:
            # 使用自定义实现
            self.visual_service = None
            logger.info("使用简化实现初始化")
    
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
    
    def _fallback_request(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """
        当官方SDK不可用时的备用请求方法
        
        Args:
            form: 请求参数
            
        Returns:
            API响应结果
        """
        import hashlib
        import hmac
        from datetime import datetime
        
        # API配置
        endpoint = "https://visual.volcengineapi.com"
        version = "2022-08-31"
        action = "CVSync2AsyncSubmitTask"
        
        # 构建请求
        uri = "/"
        query = f"Action={action}&Version={version}"
        body = json.dumps(form)
        
        headers = {
            "Content-Type": "application/json",
            "Host": "visual.volcengineapi.com",
            "X-Date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        }
        
        # 生成签名
        def sign(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
        
        # 构建待签名字符串
        canonical_headers = '\n'.join([f"{k.lower()}:{v}" for k, v in sorted(headers.items())])
        signed_headers = ';'.join([k.lower() for k in sorted(headers.keys())])
        payload_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
        canonical_request = f"POST\n{uri}\n{query}\n{canonical_headers}\n\n{signed_headers}\n{payload_hash}"
        
        # 创建签名字符串
        timestamp = headers['X-Date']
        date = timestamp[:8]
        credential_scope = f"{date}/{self.region}/visual/request"
        string_to_sign = f"HMAC-SHA256\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # 计算签名
        kdate = sign(f"Volc{self.secret_access_key}".encode('utf-8'), date)
        kregion = sign(kdate, self.region)
        kservice = sign(kregion, "visual")
        ksigning = sign(kservice, "request")
        signature = hmac.new(ksigning, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        authorization = f"HMAC-SHA256 Credential={self.access_key_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        headers["Authorization"] = authorization
        
        # 发送请求
        url = f"{endpoint}{uri}?{query}"
        
        try:
            logger.info(f"发送备用请求: {url}")
            response = requests.post(url, headers=headers, data=body, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise VolcengineImg2ImgError(f"备用请求失败: {e}")
    
    def image_to_image(self, 
                      image_url: str,
                      prompt: str = "高质量人像写真",
                      gpen: float = 0.4,
                      skin: float = 0.3,
                      skin_unifi: float = 0.0,
                      width: int = 1920,
                      height: int = 1080,
                      gen_mode: str = "creative",
                      seed: int = -1) -> Dict[str, Any]:
        """
        执行图生图转换（异步模式）
        
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
            任务提交结果，包含task_id
        """
        # 构建请求参数
        form = {
            "req_key": "i2i_portrait_photo",
            "image_input": image_url,
            "prompt": prompt,
            "gpen": max(0.0, min(1.0, gpen)),
            "skin": max(0.0, min(1.0, skin)),
            "skin_unifi": max(0.0, min(1.0, skin_unifi)),
            "width": width,
            "height": height,
            "gen_mode": gen_mode,
            "seed": seed
        }
        
        try:
            if OFFICIAL_SDK_AVAILABLE and self.visual_service:
                # 使用官方SDK提交异步任务
                logger.info("使用官方SDK提交图生图任务")
                logger.info(f"提交参数: {form}")
                result = self.visual_service.cv_sync2async_submit_task(form)
                logger.info(f"SDK返回结果: {result}")
            else:
                # 使用备用实现
                logger.info("使用备用实现提交图生图任务")
                result = self._fallback_request(form)
            
            logger.info(f"任务提交成功: {result}")
            return result
            
        except Exception as e:
            logger.error(f"图生图任务提交失败: {e}")
            raise VolcengineImg2ImgError(f"图生图任务提交失败: {e}")
    
    def get_task_result(self, task_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """
        获取异步任务结果
        
        Args:
            task_id: 任务ID
            max_wait_time: 最大等待时间（秒）
            
        Returns:
            任务结果
        """
        form = {
            "req_key": "i2i_portrait_photo",
            "task_id": task_id,
            "req_json": "{\"logo_info\":{\"add_logo\":true,\"position\":0,\"language\":0,\"opacity\":0.3,\"logo_text_content\":\"这里是明水印内容\"},\"return_url\":true}"
        }
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                if OFFICIAL_SDK_AVAILABLE and self.visual_service:
                    # 使用官方SDK获取结果
                    result = self.visual_service.cv_sync2async_get_result(form)
                else:
                    # 使用备用实现 - 需要调用结果查询接口
                    result = self._fallback_request(form)
                
                # 检查任务状态
                if result.get("code") == 10000:
                    data = result.get("data", {})
                    status = data.get("status")
                    
                    if status == "done":
                        logger.info("任务完成")
                        return result
                    elif status == "failed":
                        error_msg = data.get("message", "任务失败")
                        raise VolcengineImg2ImgError(f"任务执行失败: {error_msg}")
                    else:
                        logger.info(f"任务状态: {status}，等待中...")
                        time.sleep(5)  # 等待5秒后重试
                else:
                    error_msg = result.get("message", "获取结果失败")
                    raise VolcengineImg2ImgError(f"获取任务结果失败: {error_msg}")
                    
            except Exception as e:
                logger.error(f"获取任务结果异常: {e}")
                time.sleep(5)
        
        raise VolcengineImg2ImgError(f"任务超时，最大等待时间: {max_wait_time}秒")
    
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
            # 提取图像数据
            image_data = None
            
            # 尝试不同的响应格式
            if "data" in result:
                data = result["data"]
                
                # 检查是否有图片URL
                if "image_urls" in data and data["image_urls"]:
                    image_url = data["image_urls"][0]
                    logger.info(f"从URL下载结果图片: {image_url}")
                    response = requests.get(image_url, timeout=30)
                    response.raise_for_status()
                    image_data = response.content
                
                # 检查是否有base64数据
                elif "image" in data:
                    image_b64 = data["image"]
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
                os.makedirs(os.path.dirname(debug_path), exist_ok=True)
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
        print(f"image_url: {image_url}")
        print(f"output_path: {output_path}")
        print(f"access_key_id: {access_key_id}")
        print(f"secret_access_key: {secret_access_key}")
        print(f"prompt: {prompt}")
        print(f"kwargs: {kwargs}")

        # 创建客户端
        client = VolcengineImg2ImgOfficial(access_key_id, secret_access_key)
        
        # 提交任务
        logger.info("提交图生图任务...")
        submit_result = client.image_to_image(
            image_url=image_url,
            prompt=prompt,
            **kwargs
        )
        
        # 提取task_id
        task_id = None
        if "data" in submit_result and "task_id" in submit_result["data"]:
            task_id = submit_result["data"]["task_id"]
        elif "task_id" in submit_result:
            task_id = submit_result["task_id"]
        
        if not task_id:
            raise VolcengineImg2ImgError("提交任务成功但未获取到task_id")
        
        logger.info(f"任务ID: {task_id}")
        
        # 等待任务完成
        logger.info("等待任务完成...")
        final_result = client.get_task_result(task_id)
        
        # 保存结果
        saved_path = client.save_result(final_result, output_path)
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