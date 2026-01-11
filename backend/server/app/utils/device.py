"""
设备检测工具函数
自动检测并使用GPU（如果可用），否则使用CPU
"""
import torch
import logging

logger = logging.getLogger(__name__)

def get_device(device_id: int = 0, force_cpu: bool = False):
    """
    获取计算设备（优先GPU，找不到则CPU）
    
    Args:
        device_id: GPU设备ID（默认0）
        force_cpu: 是否强制使用CPU（默认False）
    
    Returns:
        torch.device: 计算设备
    """
    if force_cpu:
        device = torch.device('cpu')
        logger.info(f"强制使用CPU设备")
        return device
    
    if torch.cuda.is_available():
        # 检查指定的GPU设备是否存在
        if device_id < torch.cuda.device_count():
            device = torch.device(f'cuda:{device_id}')
            logger.info(f"使用GPU设备: {device} (CUDA可用，共{torch.cuda.device_count()}个GPU)")
        else:
            # 如果指定的设备ID不存在，使用默认的cuda:0
            device = torch.device('cuda:0')
            logger.warning(f"指定的GPU设备ID {device_id}不存在，使用默认GPU: {device}")
    else:
        device = torch.device('cpu')
        logger.info("CUDA不可用，使用CPU设备")
    
    return device

def get_device_from_config(config=None):
    """
    从配置对象获取设备
    
    Args:
        config: 配置对象（可选），如果提供则从中读取USE_GPU和CUDA_DEVICE
    
    Returns:
        torch.device: 计算设备
    """
    if config is not None:
        use_gpu = getattr(config, 'USE_GPU', False)
        cuda_device = getattr(config, 'CUDA_DEVICE', 'cpu')
        
        if use_gpu and isinstance(cuda_device, str) and cuda_device.startswith('cuda'):
            # 从字符串中提取设备ID，如 "cuda:0" -> 0
            try:
                device_id = int(cuda_device.split(':')[-1]) if ':' in cuda_device else 0
            except ValueError:
                device_id = 0
            return get_device(device_id=device_id, force_cpu=False)
        elif use_gpu and isinstance(cuda_device, int):
            return get_device(device_id=cuda_device, force_cpu=False)
        else:
            return get_device(force_cpu=True)
    else:
        # 如果没有配置，自动检测
        return get_device()

