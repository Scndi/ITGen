"""
模型适配器 - 统一不同模型的接口
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ModelAdapter:
    """
    模型适配器
    
    统一不同模型类型（RoBERTa, GPT2, CodeT5等）的接口
    使得攻击算法可以以统一的方式与不同模型交互
    """
    
    def __init__(self, model, tokenizer, config: Dict[str, Any]):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config
        self.model_type = self._detect_model_type(model)
        logger.info(f"✓ 模型适配器初始化，检测到模型类型: {self.model_type}")
    
    def _detect_model_type(self, model) -> str:
        """
        自动检测模型类型
        
        Args:
            model: 模型对象
            
        Returns:
            模型类型字符串
        """
        model_class_name = model.__class__.__name__.lower()
        
        # 检测模型类型
        if 'roberta' in model_class_name or 'codebert' in model_class_name or 'graphcodebert' in model_class_name:
            return 'roberta'
        elif 'gpt' in model_class_name or 'codegpt' in model_class_name:
            return 'gpt2'
        elif 't5' in model_class_name or 'codet5' in model_class_name:
            return 'codet5'
        elif 'bart' in model_class_name or 'plbart' in model_class_name:
            return 'bart'
        else:
            # 默认使用roberta（最常见）
            logger.warning(f"⚠ 无法识别模型类型 {model_class_name}，使用默认类型: roberta")
            return 'roberta'
    
    def predict(self, code_data: Dict[str, str]) -> int:
        """
        统一的预测接口
        
        Args:
            code_data: 代码数据字典，包含code1和code2
        
        Returns:
            预测标签
        """
        if self.model_type == 'roberta':
            return self._roberta_predict(code_data)
        elif self.model_type == 'gpt2':
            return self._gpt2_predict(code_data)
        elif self.model_type == 'codet5':
            return self._codet5_predict(code_data)
        elif self.model_type == 'bart':
            return self._bart_predict(code_data)
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
    
    def _roberta_predict(self, code_data: Dict[str, str]) -> int:
        """RoBERTa/CodeBERT/GraphCodeBERT预测逻辑"""
        # TODO: 实现RoBERTa模型的预测逻辑
        # 可以从现有的 Attack/CodeBERT/ 目录下的代码迁移
        code1 = code_data.get('code1', '')
        code2 = code_data.get('code2', '')
        
        # 示例实现
        # 实际应该调用模型的forward方法
        try:
            # 这里应该调用实际的模型预测
            # 例如：logits, preds = model.get_results([example], batch_size)
            # return preds[0]
            pass
        except Exception as e:
            logger.error(f"RoBERTa预测失败: {e}")
            raise
        
        # 临时返回
        return 1
    
    def _gpt2_predict(self, code_data: Dict[str, str]) -> int:
        """GPT2/CodeGPT预测逻辑"""
        # TODO: 实现GPT2模型的预测逻辑
        code1 = code_data.get('code1', '')
        code2 = code_data.get('code2', '')
        
        # 示例实现
        return 1
    
    def _codet5_predict(self, code_data: Dict[str, str]) -> int:
        """CodeT5预测逻辑"""
        # TODO: 实现CodeT5模型的预测逻辑
        code1 = code_data.get('code1', '')
        code2 = code_data.get('code2', '')
        
        # 示例实现
        return 1
    
    def _bart_predict(self, code_data: Dict[str, str]) -> int:
        """BART/PLBART预测逻辑"""
        # TODO: 实现BART模型的预测逻辑
        code1 = code_data.get('code1', '')
        code2 = code_data.get('code2', '')
        
        # 示例实现
        return 1
    
    def tokenize(self, code: str) -> list:
        """统一的tokenize接口"""
        return self.tokenizer.tokenize(code)
    
    def encode(self, code: str) -> list:
        """统一的encode接口"""
        return self.tokenizer.encode(code, return_tensors='pt')

