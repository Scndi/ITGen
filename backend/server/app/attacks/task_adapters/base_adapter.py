"""
任务适配器基类
为不同AI任务提供统一的接口
"""

import os
import sys
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'python_parser'))

logger = logging.getLogger(__name__)


class TaskAdapter(ABC):
    """
    任务适配器基类

    为不同AI任务提供统一的模型加载、数据处理和预测接口。
    每个任务类型（如克隆检测、代码摘要、漏洞预测）都继承此类。
    """

    def __init__(self, task_type: str, model_name: str = 'codebert'):
        self.task_type = task_type
        self.model_name = model_name

    @abstractmethod
    def get_model_class(self) -> type:
        """
        返回该任务使用的模型类

        Returns:
            模型类（如 Model, Seq2Seq 等）
        """
        pass

    @abstractmethod
    def get_config_params(self) -> Dict[str, Any]:
        """
        返回模型配置参数

        Returns:
            配置参数字典
        """
        pass

    @abstractmethod
    def preprocess_input(self, code_data: Dict[str, str]) -> Any:
        """
        预处理输入数据

        Args:
            code_data: 代码数据字典

        Returns:
            预处理后的数据
        """
        pass

    @abstractmethod
    def postprocess_output(self, model_output: Any) -> Dict[str, Any]:
        """
        后处理模型输出

        Args:
            model_output: 模型原始输出

        Returns:
            处理后的结果字典
        """
        pass

    def get_supported_models(self) -> List[str]:
        """
        返回支持的模型列表

        Returns:
            支持的模型名称列表
        """
        return ['codebert', 'codet5', 'codegpt', 'graphcodebert', 'plbart']

    def validate_input(self, code_data: Dict[str, str]) -> bool:
        """
        验证输入数据

        Args:
            code_data: 代码数据字典

        Returns:
            是否有效
        """
        if not isinstance(code_data, dict):
            return False

        # 检查必需的代码字段
        if self.task_type in ['clone-detection', 'vulnerability-prediction', 'vulnerability-detection']:
            return 'code1' in code_data and 'code2' in code_data
        elif self.task_type in ['code-summarization']:
            return 'code' in code_data  # 代码摘要只需要一段代码
        elif self.task_type in ['authorship-attribution']:
            return 'code' in code_data  # 作者归属也只需要一段代码

        return False
