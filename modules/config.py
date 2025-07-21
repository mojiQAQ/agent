"""
配置管理模块
负责加载和管理应用配置
"""

import os
import yaml
from typing import Dict, Any
from pathlib import Path

# 全局配置变量
_config_cache: Dict[str, Any] = {}


def get_config_path() -> str:
    """
    获取配置文件路径
    
    Returns:
        配置文件的绝对路径
    """
    # 获取项目根目录
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    config_path = project_root / "configs" / "settings.yaml"
    
    return str(config_path)


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，默认为None使用默认路径
        
    Returns:
        配置字典
        
    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML格式错误
    """
    global _config_cache
    
    if config_path is None:
        config_path = get_config_path()
    
    # 检查缓存
    cache_key = config_path
    if cache_key in _config_cache:
        return _config_cache[cache_key]
    
    # 检查文件是否存在
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 缓存配置
        _config_cache[cache_key] = config
        return config
        
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"配置文件格式错误: {e}")


def get_config(config_path: str = None) -> Dict[str, Any]:
    """
    获取配置（带缓存）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    return load_config(config_path)


def reload_config(config_path: str = None) -> Dict[str, Any]:
    """
    重新加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    global _config_cache
    
    if config_path is None:
        config_path = get_config_path()
    
    # 清除缓存
    cache_key = config_path
    if cache_key in _config_cache:
        del _config_cache[cache_key]
    
    return load_config(config_path)


def get_volcengine_config() -> Dict[str, Any]:
    """
    获取火山引擎配置
    
    Returns:
        火山引擎配置字典
    """
    config = get_config()
    return config.get('volcengine', {})


def get_img2img_config() -> Dict[str, Any]:
    """
    获取图生图配置
    
    Returns:
        图生图配置字典
    """
    volcengine_config = get_volcengine_config()
    return volcengine_config.get('image_to_image', {})

# 腾讯云 API 相关配置
def get_tencent_config() -> Dict[str, Any]:
    """获取腾讯云API配置"""
    config = get_config()
    return config.get('tencent_cloud', {})


def update_config(key_path: str, value: Any, config_path: str = None) -> bool:
    """
    更新配置值（仅内存中，不写入文件）
    
    Args:
        key_path: 配置键路径，用.分隔，如 'volcengine.access_key_id'
        value: 新值
        config_path: 配置文件路径
        
    Returns:
        是否更新成功
    """
    try:
        config = get_config(config_path)
        
        # 分解键路径
        keys = key_path.split('.')
        current = config
        
        # 导航到目标位置
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 设置值
        current[keys[-1]] = value
        
        return True
        
    except Exception:
        return False 