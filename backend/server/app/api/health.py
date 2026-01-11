from flask import Blueprint, jsonify
from datetime import datetime
import torch
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('health', __name__)

@bp.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    try:
        # 检查CUDA可用性
        cuda_available = torch.cuda.is_available()
        cuda_device_count = torch.cuda.device_count() if cuda_available else 0
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'cuda_available': cuda_available,
            'cuda_device_count': cuda_device_count,
            'algorithm_service_available': True,  # 可以添加实际检查
            'active_connections': 0,
            'note': '后端服务正常运行，算法服务状态见algorithm_service_available字段'
        }), 200
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

