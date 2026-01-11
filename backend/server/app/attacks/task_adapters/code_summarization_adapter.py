"""
代码摘要任务适配器
处理代码摘要生成任务的模型加载和数据处理
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'roberta', 'code-summarization', 'code'))

from app.attacks.task_adapters.base_adapter import TaskAdapter

logger = logging.getLogger(__name__)


class CodeSummarizationAdapter(TaskAdapter):
    """
    代码摘要任务适配器

    处理代码摘要生成任务，使用Seq2Seq模型从代码生成自然语言摘要。
    """

    def __init__(self, task_type: str = 'code-summarization', model_name: str = 'codebert'):
        super().__init__(task_type, model_name)

    def get_model_class(self):
        """
        返回代码摘要任务使用的模型类

        Returns:
            Seq2Seq 类
        """
        try:
            from model import Seq2Seq
            return Seq2Seq
        except ImportError:
            logger.error("无法导入代码摘要模型类，请检查路径配置")
            raise

    def get_config_params(self) -> Dict[str, Any]:
        """
        返回代码摘要任务的配置参数

        Returns:
            配置参数字典
        """
        return {
            'num_labels': 1,  # 生成任务
            'task_type': 'generation',
            'max_source_length': 256,
            'max_target_length': 128,
        }

    def preprocess_input(self, code_data: Dict[str, str]):
        """
        预处理代码摘要输入数据

        Args:
            code_data: 包含code的字典

        Returns:
            预处理后的数据
        """
        from utils import get_code_tokens

        code = code_data.get('code', '')

        # 分词处理
        code_tokens = get_code_tokens(code) if code else []

        return {
            'code_tokens': code_tokens,
            'original_code': code
        }

    def postprocess_output(self, model_output) -> Dict[str, Any]:
        """
        后处理代码摘要模型输出

        Args:
            model_output: 模型输出（生成的摘要文本）

        Returns:
            处理后的结果字典
        """
        # 对于生成任务，model_output通常是生成的文本
        if isinstance(model_output, str):
            generated_summary = model_output
        elif isinstance(model_output, list):
            generated_summary = model_output[0] if model_output else ""
        else:
            generated_summary = str(model_output)

        return {
            'generated_summary': generated_summary,
            'summary_length': len(generated_summary.split()) if generated_summary else 0,
        }

    def get_supported_models(self) -> List[str]:
        """返回支持的模型列表"""
        return ['codebert', 'codet5', 'codegpt', 'graphcodebert', 'plbart']

    def validate_input(self, code_data: Dict[str, str]) -> bool:
        """验证输入数据"""
        return (isinstance(code_data.get('code', ''), str) and
                len(code_data.get('code', '').strip()) > 0)
