"""
克隆检测任务适配器
处理代码克隆检测任务的模型加载和数据处理
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'roberta', 'clone-detection', 'code'))

from app.attacks.task_adapters.base_adapter import TaskAdapter

logger = logging.getLogger(__name__)


class CloneDetectionAdapter(TaskAdapter):
    """
    克隆检测任务适配器

    处理代码克隆检测任务，使用分类模型判断两段代码是否相似。
    """

    def __init__(self, task_type: str = 'clone-detection', model_name: str = 'codebert'):
        super().__init__(task_type, model_name)

    def get_model_class(self):
        """
        返回克隆检测任务使用的模型类

        Returns:
            Model 类
        """
        try:
            from model import Model
            return Model
        except ImportError:
            logger.error("无法导入克隆检测模型类，请检查路径配置")
            raise

    def get_config_params(self) -> Dict[str, Any]:
        """
        返回克隆检测任务的配置参数

        Returns:
            配置参数字典
        """
        return {
            'num_labels': 2,  # 二分类：是否克隆
            'task_type': 'classification',
            'max_length': 512,
        }

    def preprocess_input(self, code_data: Dict[str, str]):
        """
        预处理克隆检测输入数据

        Args:
            code_data: 包含code1和code2的字典

        Returns:
            预处理后的数据
        """
        from utils import get_code_tokens

        code1 = code_data.get('code1', '')
        code2 = code_data.get('code2', '')

        # 分词处理
        code1_tokens = get_code_tokens(code1) if code1 else []
        code2_tokens = get_code_tokens(code2) if code2 else []

        return {
            'code1_tokens': code1_tokens,
            'code2_tokens': code2_tokens,
            'original_code1': code1,
            'original_code2': code2
        }

    def postprocess_output(self, model_output) -> Dict[str, Any]:
        """
        后处理克隆检测模型输出

        Args:
            model_output: 模型输出元组 (logits, predictions)

        Returns:
            处理后的结果字典
        """
        logits, predictions = model_output

        # 获取预测结果
        predicted_label = predictions[0] if len(predictions) > 0 else 0
        confidence = float(max(logits[0])) if len(logits) > 0 and len(logits[0]) > 0 else 0.0

        return {
            'predicted_label': predicted_label,
            'confidence': confidence,
            'logits': logits.tolist() if hasattr(logits, 'tolist') else logits,
            'is_similar': predicted_label == 1  # 1表示相似，0表示不相似
        }

    def get_supported_models(self) -> List[str]:
        """返回支持的模型列表"""
        return ['codebert', 'codet5', 'codegpt', 'graphcodebert', 'plbart']

    def validate_input(self, code_data: Dict[str, str]) -> bool:
        """验证输入数据"""
        return (super().validate_input(code_data) and
                isinstance(code_data.get('code1', ''), str) and
                isinstance(code_data.get('code2', ''), str) and
                len(code_data.get('code1', '').strip()) > 0 and
                len(code_data.get('code2', '').strip()) > 0)
