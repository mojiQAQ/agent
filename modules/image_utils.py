"""
图像处理工具函数模块
提供图像格式转换、尺寸调整、质量优化等功能
"""

import base64
import io
import os
from typing import Tuple, Union, Optional, Dict, List, Any
from PIL import Image, ImageEnhance, ImageFilter, ExifTags
import numpy as np
from .logger import get_logger
from pathlib import Path


class ImageUtils:
    """图像处理工具类"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # 支持的图像格式
        self.supported_formats = {
            'JPEG': ['.jpg', '.jpeg'],
            'PNG': ['.png'],
            'WEBP': ['.webp'],
            'BMP': ['.bmp'],
            'TIFF': ['.tiff', '.tif']
        }
        
        # 常用尺寸预设
        self.size_presets = {
            'square_small': (512, 512),
            'square_medium': (768, 768),
            'square_large': (1024, 1024),
            'portrait': (512, 768),
            'landscape': (768, 512),
            'widescreen': (1024, 576),
            'instagram_square': (1080, 1080),
            'instagram_portrait': (1080, 1350),
            'instagram_story': (1080, 1920)
        }
    
    @staticmethod
    def file_to_base64(file_path: str) -> str:
        """将图像文件转换为base64编码
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            base64编码字符串
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")
        
        with open(file_path, 'rb') as f:
            image_bytes = f.read()
            return base64.b64encode(image_bytes).decode('utf-8')
    
    @staticmethod
    def base64_to_file(base64_str: str, output_path: str, format: str = 'JPEG') -> bool:
        """将base64编码保存为图像文件
        
        Args:
            base64_str: base64编码字符串
            output_path: 输出文件路径
            format: 图像格式
            
        Returns:
            是否成功
        """
        try:
            image_bytes = base64.b64decode(base64_str)
            image = Image.open(io.BytesIO(image_bytes))
            
            # 确保目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存图像
            if format.upper() == 'JPEG' and image.mode in ['RGBA', 'LA']:
                # JPEG不支持透明度，转换为RGB
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            image.save(output_path, format=format.upper())
            return True
            
        except Exception as e:
            get_logger(__name__).error(f"Failed to save base64 to file: {e}")
            return False
    
    @staticmethod
    def pil_to_base64(image: Image.Image, format: str = 'JPEG', quality: int = 95) -> str:
        """将PIL图像转换为base64编码
        
        Args:
            image: PIL图像对象
            format: 输出格式
            quality: 图像质量 (1-100)
            
        Returns:
            base64编码字符串
        """
        buffer = io.BytesIO()
        
        # 处理透明度
        if format.upper() == 'JPEG' and image.mode in ['RGBA', 'LA']:
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        save_kwargs = {'format': format.upper()}
        if format.upper() == 'JPEG':
            save_kwargs['quality'] = quality
            save_kwargs['optimize'] = True
        elif format.upper() == 'PNG':
            save_kwargs['optimize'] = True
        
        image.save(buffer, **save_kwargs)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    @staticmethod
    def base64_to_pil(base64_str: str) -> Image.Image:
        """将base64编码转换为PIL图像
        
        Args:
            base64_str: base64编码字符串
            
        Returns:
            PIL图像对象
        """
        image_bytes = base64.b64decode(base64_str)
        return Image.open(io.BytesIO(image_bytes))
    
    def resize_image(self, image: Union[Image.Image, str], 
                    target_size: Union[Tuple[int, int], str],
                    method: str = 'lanczos',
                    maintain_aspect: bool = True) -> Image.Image:
        """调整图像尺寸
        
        Args:
            image: PIL图像对象或base64字符串
            target_size: 目标尺寸 (width, height) 或预设名称
            method: 重采样方法 ('lanczos', 'bilinear', 'bicubic', 'nearest')
            maintain_aspect: 是否保持长宽比
            
        Returns:
            调整后的PIL图像
        """
        # 转换输入
        if isinstance(image, str):
            image = self.base64_to_pil(image)
        
        # 获取目标尺寸
        if isinstance(target_size, str):
            if target_size not in self.size_presets:
                raise ValueError(f"Unknown size preset: {target_size}")
            target_width, target_height = self.size_presets[target_size]
        else:
            target_width, target_height = target_size
        
        # 选择重采样方法
        resample_methods = {
            'lanczos': Image.Resampling.LANCZOS,
            'bilinear': Image.Resampling.BILINEAR,
            'bicubic': Image.Resampling.BICUBIC,
            'nearest': Image.Resampling.NEAREST
        }
        resample = resample_methods.get(method.lower(), Image.Resampling.LANCZOS)
        
        if maintain_aspect:
            # 保持长宽比，进行等比缩放
            image.thumbnail((target_width, target_height), resample)
            
            # 创建目标尺寸的画布
            canvas = Image.new('RGB', (target_width, target_height), (255, 255, 255))
            
            # 计算居中位置
            x = (target_width - image.width) // 2
            y = (target_height - image.height) // 2
            
            # 粘贴图像到画布中心
            if image.mode == 'RGBA':
                canvas.paste(image, (x, y), image)
            else:
                canvas.paste(image, (x, y))
            
            return canvas
        else:
            # 直接拉伸到目标尺寸
            return image.resize((target_width, target_height), resample)
    
    def crop_to_aspect_ratio(self, image: Union[Image.Image, str], 
                           aspect_ratio: Union[float, str]) -> Image.Image:
        """按长宽比裁剪图像
        
        Args:
            image: PIL图像对象或base64字符串
            aspect_ratio: 目标长宽比 (width/height) 或预设比例
            
        Returns:
            裁剪后的图像
        """
        if isinstance(image, str):
            image = self.base64_to_pil(image)
        
        # 预设长宽比
        aspect_presets = {
            'square': 1.0,
            'portrait': 3/4,
            'landscape': 4/3,
            'widescreen': 16/9,
            'instagram': 1.0,
            'story': 9/16
        }
        
        if isinstance(aspect_ratio, str):
            if aspect_ratio not in aspect_presets:
                raise ValueError(f"Unknown aspect ratio preset: {aspect_ratio}")
            target_ratio = aspect_presets[aspect_ratio]
        else:
            target_ratio = float(aspect_ratio)
        
        width, height = image.size
        current_ratio = width / height
        
        if abs(current_ratio - target_ratio) < 0.01:
            return image  # 已经是目标比例
        
        if current_ratio > target_ratio:
            # 当前图像更宽，需要裁剪宽度
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            bbox = (left, 0, left + new_width, height)
        else:
            # 当前图像更高，需要裁剪高度
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            bbox = (0, top, width, top + new_height)
        
        return image.crop(bbox)
    
    def enhance_image(self, image: Union[Image.Image, str], 
                     brightness: float = 1.0,
                     contrast: float = 1.0,
                     saturation: float = 1.0,
                     sharpness: float = 1.0) -> Image.Image:
        """增强图像质量
        
        Args:
            image: PIL图像对象或base64字符串
            brightness: 亮度调整 (0.0-2.0, 1.0为原始)
            contrast: 对比度调整 (0.0-2.0, 1.0为原始)
            saturation: 饱和度调整 (0.0-2.0, 1.0为原始)
            sharpness: 锐度调整 (0.0-2.0, 1.0为原始)
            
        Returns:
            增强后的图像
        """
        if isinstance(image, str):
            image = self.base64_to_pil(image)
        
        # 亮度调整
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(brightness)
        
        # 对比度调整
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(contrast)
        
        # 饱和度调整
        if saturation != 1.0:
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(saturation)
        
        # 锐度调整
        if sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(sharpness)
        
        return image
    
    def apply_filter(self, image: Union[Image.Image, str], filter_type: str) -> Image.Image:
        """应用图像滤镜
        
        Args:
            image: PIL图像对象或base64字符串
            filter_type: 滤镜类型
            
        Returns:
            应用滤镜后的图像
        """
        if isinstance(image, str):
            image = self.base64_to_pil(image)
        
        filters = {
            'blur': ImageFilter.BLUR,
            'detail': ImageFilter.DETAIL,
            'edge_enhance': ImageFilter.EDGE_ENHANCE,
            'edge_enhance_more': ImageFilter.EDGE_ENHANCE_MORE,
            'emboss': ImageFilter.EMBOSS,
            'find_edges': ImageFilter.FIND_EDGES,
            'smooth': ImageFilter.SMOOTH,
            'smooth_more': ImageFilter.SMOOTH_MORE,
            'sharpen': ImageFilter.SHARPEN,
            'gaussian_blur': ImageFilter.GaussianBlur(radius=2),
            'unsharp_mask': ImageFilter.UnsharpMask()
        }
        
        if filter_type not in filters:
            available_filters = ', '.join(filters.keys())
            raise ValueError(f"Unknown filter type: {filter_type}. Available: {available_filters}")
        
        return image.filter(filters[filter_type])
    
    def get_image_info(self, image: Union[Image.Image, str]) -> Dict:
        """获取图像信息
        
        Args:
            image: PIL图像对象或base64字符串
            
        Returns:
            图像信息字典
        """
        if isinstance(image, str):
            image = self.base64_to_pil(image)
        
        info = {
            'size': image.size,
            'width': image.width,
            'height': image.height,
            'mode': image.mode,
            'format': image.format,
            'has_transparency': image.mode in ['RGBA', 'LA'] or 'transparency' in image.info
        }
        
        # 获取EXIF信息
        if hasattr(image, '_getexif') and image._getexif():
            exif = {}
            for tag_id, value in image._getexif().items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                exif[tag] = value
            info['exif'] = exif
        
        return info
    
    def optimize_for_web(self, image: Union[Image.Image, str], 
                        max_size: Tuple[int, int] = (1920, 1920),
                        quality: int = 85,
                        format: str = 'JPEG') -> str:
        """优化图像用于网络传输
        
        Args:
            image: PIL图像对象或base64字符串
            max_size: 最大尺寸
            quality: 压缩质量
            format: 输出格式
            
        Returns:
            优化后的base64编码
        """
        if isinstance(image, str):
            image = self.base64_to_pil(image)
        
        # 调整尺寸
        if image.width > max_size[0] or image.height > max_size[1]:
            image = self.resize_image(image, max_size, maintain_aspect=True)
        
        # 转换格式并压缩
        return self.pil_to_base64(image, format=format, quality=quality)
    
    def create_thumbnail(self, image: Union[Image.Image, str], 
                        size: Tuple[int, int] = (256, 256)) -> str:
        """创建缩略图
        
        Args:
            image: PIL图像对象或base64字符串
            size: 缩略图尺寸
            
        Returns:
            缩略图的base64编码
        """
        if isinstance(image, str):
            image = self.base64_to_pil(image)
        
        # 创建缩略图
        thumbnail = image.copy()
        thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
        
        return self.pil_to_base64(thumbnail, quality=80)
    
    def batch_resize(self, images: List[Union[Image.Image, str]], 
                    target_size: Union[Tuple[int, int], str]) -> List[str]:
        """批量调整图像尺寸
        
        Args:
            images: 图像列表
            target_size: 目标尺寸
            
        Returns:
            调整后的base64编码列表
        """
        results = []
        for image in images:
            try:
                resized = self.resize_image(image, target_size)
                results.append(self.pil_to_base64(resized))
            except Exception as e:
                self.logger.error(f"Failed to resize image: {e}")
                results.append("")
        
        return results
    
    def validate_image_data(self, image_data: str, 
                          max_size: int = 10 * 1024 * 1024) -> Tuple[bool, str]:
        """验证图像数据
        
        Args:
            image_data: base64编码的图像数据
            max_size: 最大文件大小（字节）
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 检查base64格式
            try:
                decoded_data = base64.b64decode(image_data)
            except Exception:
                return False, "Invalid base64 encoding"
            
            # 检查文件大小
            if len(decoded_data) > max_size:
                return False, f"Image size exceeds limit: {len(decoded_data)} > {max_size} bytes"
            
            # 检查是否为有效图像
            try:
                image = Image.open(io.BytesIO(decoded_data))
                image.verify()  # 验证图像完整性
            except Exception as e:
                return False, f"Invalid image data: {e}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def get_dominant_colors(self, image: Union[Image.Image, str], 
                          num_colors: int = 5) -> List[Tuple[int, int, int]]:
        """获取图像主要颜色
        
        Args:
            image: PIL图像对象或base64字符串
            num_colors: 返回的颜色数量
            
        Returns:
            主要颜色列表 [(R, G, B), ...]
        """
        if isinstance(image, str):
            image = self.base64_to_pil(image)
        
        # 转换为RGB模式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 缩小图像以提高性能
        image.thumbnail((150, 150))
        
        # 使用k-means聚类获取主要颜色
        import numpy as np
        from sklearn.cluster import KMeans
        
        # 将图像转换为像素数组
        pixels = np.array(image).reshape(-1, 3)
        
        # 进行k-means聚类
        kmeans = KMeans(n_clusters=num_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        # 获取聚类中心（主要颜色）
        colors = kmeans.cluster_centers_.astype(int)
        
        return [tuple(color) for color in colors] 

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取支持的图像格式
        
        Returns:
            格式字典
        """
        return self.supported_formats.copy()
    
    def validate_image_format(self, file_path: str) -> bool:
        """验证图像格式是否支持
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            是否支持
        """
        file_ext = Path(file_path).suffix.lower()
        for format_name, extensions in self.supported_formats.items():
            if file_ext in extensions:
                return True
        return False
    
    def create_volcengine_client(self):
        """创建Volcengine图生图客户端
        
        Returns:
            Volcengine客户端实例，如果配置不完整则返回None
        """
        try:
            from .volcengine_img2img import create_volcengine_client
            return create_volcengine_client()
        except ImportError as e:
            self.logger.error(f"无法导入Volcengine模块: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"创建Volcengine客户端失败: {e}")
            return None
    
    def volcengine_image_to_image(self, 
                                 source_image: Union[Image.Image, str],
                                 prompt: Optional[str] = None,
                                 gpen: float = 0.4,
                                 skin: float = 0.3,
                                 skin_unifi: float = 0.0,
                                 width: int = 1024,
                                 height: int = 1024,
                                 gen_mode: str = "creative",
                                 seed: int = -1,
                                 **kwargs) -> Optional[Dict[str, Any]]:
        """使用Volcengine API进行图生图转换
        
        Args:
            source_image: 源图像，支持PIL图像或文件路径
            prompt: 提示词描述
            gpen: 人脸增强参数 (0.0-1.0)
            skin: 皮肤参数 (0.0-1.0)
            skin_unifi: 皮肤统一参数 (0.0-1.0)
            width: 输出图像宽度
            height: 输出图像高度
            gen_mode: 生成模式 (creative/portrait/professional/artistic)
            seed: 随机种子，-1表示随机
            **kwargs: 其他参数
            
        Returns:
            转换结果，失败时返回None
        """
        try:
            client = self.create_volcengine_client()
            if client is None:
                self.logger.error("无法创建Volcengine客户端")
                return None
            
            result = client.image_to_image(
                source_image=source_image,
                prompt=prompt,
                gpen=gpen,
                skin=skin,
                skin_unifi=skin_unifi,
                width=width,
                height=height,
                gen_mode=gen_mode,
                seed=seed,
                **kwargs
            )
            
            self.logger.info("Volcengine图生图转换完成")
            return result
            
        except Exception as e:
            self.logger.error(f"Volcengine图生图转换失败: {e}")
            return None
    
    def volcengine_batch_process(self, 
                                image_list: List[Union[Image.Image, str]],
                                prompts: Optional[List[str]] = None,
                                gpen: float = 0.4,
                                skin: float = 0.3,
                                skin_unifi: float = 0.0,
                                width: int = 1024,
                                height: int = 1024,
                                gen_mode: str = "creative",
                                seed: int = -1,
                                **kwargs) -> List[Dict[str, Any]]:
        """批量使用Volcengine进行图像处理
        
        Args:
            image_list: 图像列表
            prompts: 提示词列表，如果为None则使用默认提示词
            gpen: 人脸增强参数 (0.0-1.0)
            skin: 皮肤参数 (0.0-1.0)
            skin_unifi: 皮肤统一参数 (0.0-1.0)
            width: 输出图像宽度
            height: 输出图像高度
            gen_mode: 生成模式 (creative/portrait/professional/artistic)
            seed: 随机种子，-1表示随机
            **kwargs: 其他参数
            
        Returns:
            处理结果列表
        """
        try:
            client = self.create_volcengine_client()
            if client is None:
                self.logger.error("无法创建Volcengine客户端")
                return []
            
            results = client.batch_process(
                image_list=image_list,
                prompts=prompts,
                gpen=gpen,
                skin=skin,
                skin_unifi=skin_unifi,
                width=width,
                height=height,
                gen_mode=gen_mode,
                seed=seed,
                **kwargs
            )
            
            self.logger.info(f"批量处理完成，共处理 {len(image_list)} 张图像")
            return results
            
        except Exception as e:
            self.logger.error(f"批量处理失败: {e}")
            return []
    
    def get_volcengine_supported_modes(self) -> List[str]:
        """获取Volcengine支持的生成模式列表
        
        Returns:
            生成模式列表，失败时返回空列表
        """
        try:
            client = self.create_volcengine_client()
            if client is None:
                return []
            return client.get_supported_modes()
        except Exception as e:
            self.logger.error(f"获取支持模式失败: {e}")
            return [] 