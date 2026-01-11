"""
攻击器基类
所有攻击算法必须实现此接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class BaseAttacker(ABC):
    """攻击器基类 - 所有攻击算法必须实现此接口"""
    
    def __init__(self, model, tokenizer, config: Dict[str, Any]):
        """
        初始化攻击器
        
        Args:
            model: 目标模型（可以是任何模型类型）
            tokenizer: 对应的tokenizer
            config: 攻击配置参数，包含：
                - true_label: 真实标签
                - max_queries: 最大查询次数
                - timeout: 超时时间（秒）
                - seed: 随机种子
                - eval_batch_size: 批次大小
                - language: 编程语言
        """
        self.model = model
        self.tokenizer = tokenizer
        self.config = config
        self.query_times = 0
        self.start_time = None
    
    @abstractmethod
    def attack(
        self,
        code_data: Dict[str, str],
        true_label: int,
        substitutes: Optional[Dict[str, list]] = None
    ) -> Dict[str, Any]:
        """
        执行攻击
        
        Args:
            code_data: 代码数据字典，包含：
                - code1: 第一段代码
                - code2: 第二段代码（对于需要代码对的任务）
            true_label: 真实标签
            substitutes: 替代词字典 {identifier: [candidates]}
        
        Returns:
            攻击结果字典，包含：
                - success: 是否成功生成对抗样本
                - original_code: 原始代码
                - adversarial_code: 对抗性代码
                - replaced_identifiers: 替换的标识符字典 {old: new}
                - query_times: 模型查询次数
                - time_cost: 耗时（秒）
                - error: 错误信息（如果失败）
        """
        pass
    
    @abstractmethod
    def get_supported_model_types(self) -> List[str]:
        """
        返回支持的模型类型列表
        
        Returns:
            支持的模型类型列表，如 ['roberta', 'gpt2', 'codet5']
        """
        pass
    
    def validate_model(self, model_type: str) -> bool:
        """
        验证模型类型是否支持
        
        Args:
            model_type: 模型类型
            
        Returns:
            是否支持
        """
        return model_type.lower() in [t.lower() for t in self.get_supported_model_types()]
    
    def get_attack_method_name(self) -> str:
        """
        获取攻击方法名称
        
        Returns:
            攻击方法名称
        """
        return self.__class__.__name__.replace('Attacker', '').lower()
    
    def _increment_query(self):
        """增加查询次数"""
        self.query_times += 1
    
    def _check_timeout(self) -> bool:
        """检查是否超时"""
        if self.start_time is None:
            return False
        
        timeout = self.config.get('timeout', 3600)
        elapsed = self._get_elapsed_time()
        return elapsed > timeout
    
    def _get_elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        if self.start_time is None:
            return 0.0
        import time
        return time.time() - self.start_time
    
    def _check_max_queries(self) -> bool:
        """检查是否超过最大查询次数"""
        max_queries = self.config.get('max_queries', 1000)
        return self.query_times >= max_queries

