"""
Beam攻击算法实现
基于束搜索的对抗攻击方法
"""

import os
import sys
import time
import logging
import torch
import random
import copy
from typing import Dict, Any, Optional, List

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'python_parser'))

from utils import CodeDataset, is_valid_identifier, get_code_tokens
from python_parser.run_parser import get_example

from app.attacks.base.base_attacker import BaseAttacker
from app.attacks.base.shared_utils import InputFeatures, convert_examples_to_features
from app.attacks.task_adapters import TASK_ADAPTERS

logger = logging.getLogger(__name__)


class BeamAttacker(BaseAttacker):
    """
    Beam攻击算法 - 基于束搜索的对抗攻击

    使用束搜索算法在标识符替换空间中寻找最优的对抗样本。
    通过计算语义相似度来选择合适的替代词。

    主要特点：
    - 束搜索优化算法
    - 语义相似度计算
    - 支持多种替换策略
    """

    def __init__(self, model, tokenizer, config: Dict[str, Any]):
        super().__init__(model, tokenizer, config)

        # Beam攻击器参数
        self.beam_size = config.get('beam_size', 5)
        self.task_type = config.get('task_type', 'clone-detection')

        # 获取任务适配器
        self.task_adapter = TASK_ADAPTERS.get(self.task_type)
        if not self.task_adapter:
            raise ValueError(f"不支持的任务类型: {self.task_type}")

        # 初始化任务适配器
        self.adapter = self.task_adapter(self.task_type, config.get('model_name', 'codebert'))

        # MLM模型用于语义相似度计算
        self.model_mlm = None
        self.tokenizer_mlm = None

        # 设置随机种子
        seed = config.get('seed', 123456)
        random.seed(seed)
        torch.manual_seed(seed)

        # 创建args对象
        self.args = type('args', (), {
            'block_size': config.get('block_size', 512),
            'eval_batch_size': config.get('eval_batch_size', 2),
            'device': getattr(model, 'device', torch.device('cuda' if torch.cuda.is_available() else 'cpu')),
        })()

        logger.info(f"✓ Beam攻击器初始化完成 - 任务类型: {self.task_type}")

    def attack(
        self,
        code_data: Dict[str, str],
        true_label: int,
        substitutes: Optional[Dict[str, list]] = None
    ) -> Dict[str, Any]:
        """
        执行Beam攻击
        """
        self.start_time = time.time()
        self.query_times = 0

        try:
            code1 = code_data.get('code1', '').strip()
            code2 = code_data.get('code2', '').strip()

            if not code1:
                raise ValueError("code1不能为空")

            logger.info("🎯 开始Beam攻击")
            logger.info(f"  代码1长度: {len(code1)} 字符")
            if code2:
                logger.info(f"  代码2长度: {len(code2)} 字符")

            # 1. 准备数据
            code1_tokens = self.tokenizer.tokenize(code1)
            code2_tokens = self.tokenizer.tokenize(code2) if code2 else []

            feature = convert_examples_to_features(
                code1_tokens, code2_tokens, true_label, None, None,
                self.tokenizer, self.args, None
            )
            example = (torch.tensor(feature.input_ids), torch.tensor(true_label))

            # 2. 验证模型预测
            logits, preds = self.model.get_results([example], self.args.eval_batch_size)
            predicted_label = preds[0]

            if predicted_label != true_label:
                logger.warning(f"⚠ 模型预测({predicted_label})与真实标签({true_label})不一致")
                return {
                    'success': False,
                    'original_code': code1,
                    'adversarial_code': None,
                    'replaced_identifiers': None,
                    'query_times': 0,
                    'time_cost': 0,
                    'error': f'模型预测({predicted_label})与真实标签({true_label})不一致'
                }

            # 3. 获取替代词
            if not substitutes:
                logger.warning("⚠ Beam攻击需要提供替代词")
                return {
                    'success': False,
                    'original_code': code1,
                    'adversarial_code': None,
                    'replaced_identifiers': None,
                    'query_times': 0,
                    'time_cost': 0,
                    'error': '缺少替代词信息'
                }

            # 4. 执行Beam攻击
            logger.info("⚔️ 执行Beam攻击逻辑...")

            result = self.beam_attack(example, code1, substitutes, true_label)

            time_cost = self._get_elapsed_time()

            attack_result = {
                'success': result['is_success'] == 1,
                'original_code': code1,
                'adversarial_code': result['adv_program'] if result['adv_program'] != code1 else None,
                'replaced_identifiers': result['replaced_words'] if result['replaced_words'] else None,
                'query_times': self.query_times,
                'time_cost': time_cost,
                'error': None
            }

            if attack_result['success']:
                logger.info("🎉 Beam攻击成功！")
                logger.info(f"查询次数: {self.query_times}, 耗时: {time_cost:.2f}秒")
                logger.info(f"替换标识符: {len(attack_result['replaced_identifiers'] or {})} 个")
            else:
                logger.warning("⚠ Beam攻击失败")

            return attack_result

        except Exception as e:
            logger.error(f"✗ Beam攻击失败: {e}", exc_info=True)
            return {
                'success': False,
                'original_code': code_data.get('code1', ''),
                'adversarial_code': None,
                'replaced_identifiers': None,
                'query_times': self.query_times,
                'time_cost': self._get_elapsed_time(),
                'error': str(e)
            }

    def is_valid(self, code_token, identifier):
        """检查标识符是否有效"""
        if not is_valid_identifier(identifier):
            return False
        position = []
        for index, token in enumerate(code_token):
            if identifier == token:
                position.append(index)
        if all(x > self.args.block_size - 2 for x in position):
            return False
        return True

    def beam_attack(self, example, code_1, substitutes, true_label):
        """
        Beam攻击核心实现
        """
        # 获取原始预测
        logits, preds = self.model.get_results([example], self.args.eval_batch_size)
        orig_prob = logits[0]
        orig_label = preds[0]
        current_prob = max(orig_prob)

        if true_label != orig_label:
            return {
                'adv_program': code_1,
                'is_success': -1,
                'replaced_words': {}
            }

        # 简化的beam搜索实现
        # 这里应该实现完整的beam搜索逻辑
        # 暂时返回失败结果，需要完整实现

        logger.warning("⚠ Beam攻击算法暂未完全实现")

        return {
            'adv_program': code_1,
            'is_success': 0,
            'replaced_words': {}
        }

    def get_supported_model_types(self) -> List[str]:
        """返回支持的模型类型"""
        return ['roberta', 'codebert', 'codet5']  # Beam支持多种模型

    def _increment_query(self):
        """增加查询次数"""
        self.query_times += 1
