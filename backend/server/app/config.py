import os
from pathlib import Path

class Config:
    """应用配置"""
    
    # Flask基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 模型路径配置
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    MODEL_PATH = BASE_DIR / 'CodeBERT_adv' / 'Clone-detection' / 'saved_models'
    MODEL_NAME = 'codebert'
    
    # 设备配置 - 自动检测GPU，找不到则使用CPU
    USE_GPU = os.environ.get('USE_GPU', 'true').lower() == 'true'  # 默认启用GPU检测
    # CUDA_DEVICE可以是 'cpu', 'cuda', 'cuda:0', 'cuda:1' 等，或整数 0, 1 等
    cuda_device_str = os.environ.get('CUDA_DEVICE', 'cuda:0')
    if cuda_device_str.lower() == 'cpu':
        CUDA_DEVICE = 'cpu'
    elif cuda_device_str.isdigit():
        CUDA_DEVICE = int(cuda_device_str)
    else:
        CUDA_DEVICE = cuda_device_str
    
    # Hugging Face 镜像站配置（用于解决网络连接问题）
    # 默认使用 hf-mirror.com 镜像站，可通过环境变量 HF_ENDPOINT 覆盖
    HF_ENDPOINT = os.environ.get('HF_ENDPOINT', 'https://hf-mirror.com')
    
    # 攻击参数配置
    DEFAULT_MAX_ITERATIONS = 100
    DEFAULT_QUERY_BUDGET = 500
    DEFAULT_BATCH_SIZE = 4
    
    # 上传文件配置
    UPLOAD_FOLDER = BASE_DIR / 'app' / 'static' / 'uploads'
    # 模型文件可能很大（400-500MB），设置为 1GB
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1GB
    
    # 模型存储配置
    MODELS_BASE_DIR = BASE_DIR / 'saved_models'  # 模型存储根目录
  

    # 微调权重存储目录
    CHECKPOINTS_BASE_DIR = BASE_DIR / 'checkpoints'
    CHECKPOINTS_CLONE_DETECTION = CHECKPOINTS_BASE_DIR / 'clone-detection'
    CHECKPOINTS_VULNERABILITY = CHECKPOINTS_BASE_DIR / 'vulnerability-prediction'
    CHECKPOINTS_CODE_SUMMARIZATION = CHECKPOINTS_BASE_DIR / 'code-summarization'
    
    # 数据集存储配置
    DATASETS_BASE_DIR = BASE_DIR / 'dataset'  # 数据集存储根目录
    # 按任务类型分类存储
    DATASETS_CLONE_DETECTION = DATASETS_BASE_DIR / 'clone-detection'
    DATASETS_VULNERABILITY = DATASETS_BASE_DIR / 'vulnerability-prediction'
    DATASETS_CODE_SUMMARIZATION = DATASETS_BASE_DIR / 'code-summarization'
    
    # Redis配置（用于Celery任务队列）
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    # MySQL数据库配置
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '20040619yl...')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'itgen_db')
    
    # 数据库配置
    # 注意：如果使用 sha256_password 或 caching_sha2_password，需要安装 cryptography 包
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20
    }

