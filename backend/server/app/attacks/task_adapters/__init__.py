"""
任务适配器模块
为不同任务类型提供统一的模型加载和数据处理接口
"""

from app.attacks.task_adapters.base_adapter import TaskAdapter
from app.attacks.task_adapters.clone_detection_adapter import CloneDetectionAdapter
from app.attacks.task_adapters.code_summarization_adapter import CodeSummarizationAdapter
from app.attacks.task_adapters.vulnerability_adapter import VulnerabilityAdapter

__all__ = [
    'TaskAdapter',
    'CloneDetectionAdapter',
    'CodeSummarizationAdapter',
    'VulnerabilityAdapter'
]

# 任务类型到适配器的映射
TASK_ADAPTERS = {
    'clone-detection': CloneDetectionAdapter,
    'code-summarization': CodeSummarizationAdapter,
    'vulnerability-prediction': VulnerabilityAdapter,
    'vulnerability-detection': VulnerabilityAdapter,  # 与prediction使用相同适配器
    'authorship-attribution': CloneDetectionAdapter,  # 使用克隆检测的适配器（多分类）
}
