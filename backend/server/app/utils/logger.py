import logging
import os
from pathlib import Path

# 全局标记，防止重复配置日志
_logger_configured = False

def setup_logger(app):
    """配置日志系统"""
    global _logger_configured
    
    # 如果已经配置过，直接返回，避免重复添加处理器
    if _logger_configured:
        return
    
    log_dir = Path(app.instance_path) / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 配置日志级别
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # 配置根日志记录器（而不是 'app'，避免只配置部分logger）
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 检查是否已经有处理器，避免重复添加
    if not root_logger.handlers:
        # 文件日志处理器
        file_handler = logging.FileHandler(
            log_dir / 'app.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        root_logger.addHandler(file_handler)
        
        # 控制台日志处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(log_format, date_format))
        root_logger.addHandler(console_handler)
    
    # 配置其他库的日志级别
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger('transformers').setLevel(logging.WARNING)
    
    _logger_configured = True

