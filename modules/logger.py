import logging
import os
from pathlib import Path

# ANSI color codes for terminal output
COLORS = {
    'RESET': '\033[0m',
    'BLACK': '\033[30m',
    'RED': '\033[31m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'BLUE': '\033[34m',
    'MAGENTA': '\033[35m',
    'CYAN': '\033[36m',
    'WHITE': '\033[37m',
    'BOLD': '\033[1m',
}

class ColoredFormatter(logging.Formatter):
    """自定义日志格式化器，支持彩色输出"""
    
    FORMATS = {
        logging.DEBUG: COLORS['BLUE'] + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + COLORS['RESET'],
        logging.INFO: '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        logging.WARNING: COLORS['YELLOW'] + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + COLORS['RESET'],
        logging.ERROR: COLORS['RED'] + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + COLORS['RESET'],
        logging.CRITICAL: COLORS['RED'] + COLORS['BOLD'] + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + COLORS['RESET'],
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def get_logger(name):
    """获取一个命名的日志记录器实例
    
    Args:
        name: 记录器名称，通常使用模块名
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 如果记录器已经有处理器，说明已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别，默认 INFO，可通过环境变量 DEBUG 控制
    log_level = logging.DEBUG if os.getenv('DEBUG') else logging.INFO
    logger.setLevel(log_level)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # 创建文件处理器
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / 'pictale.log')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger 