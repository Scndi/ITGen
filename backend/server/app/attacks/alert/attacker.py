"""
ALERT攻击算法实现
基于标识符替换的对抗攻击方法 - 支持多任务类型
"""

import os
import sys
import time
import logging
import torch
import random
import numpy as np
from typing import Dict, Any, Optional, List
from copy import deepcopy

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'algorithms'))
sys.path.append(os.path.join(BASE_DIR, 'python_parser'))

from utils import (
    select_parents, crossover, map_chromesome, mutate, _tokenize,
    get_identifier_posistions_from_code, get_masked_code_by_position,
    is_valid_variable_name, CodeDataset, is_valid_identifier,
    get_code_tokens, isUID, remove_comments_and_docstrings,
    get_replaced_var_code_with_meaningless_char
)
from python_parser.run_parser import get_identifiers, get_example
from transformers import RobertaForMaskedLM

from app.attacks.base.base_attacker import BaseAttacker
from app.attacks.base.shared_utils import InputFeatures, convert_examples_to_features
from app.attacks.task_adapters import TASK_ADAPTERS

logger = logging.getLogger(__name__)


class ALERTAttacker(BaseAttacker):
    """
    ALERT攻击算法 - 基于标识符替换的对抗攻击

    通过遗传算法优化标识符替换策略，生成能够改变模型预测的对抗样本。
    支持多种预训练模型，具有较高的攻击成功率。

    主要特点：
    - 使用遗传算法进行标识符替换优化
    - 支持重要性评分计算
    - 自动过滤无效标识符
    - 支持多种模型类型
    """

    def __init__(self, model, tokenizer, config: Dict[str, Any]):
        super().__init__(model, tokenizer, config)

        # ALERT攻击器参数
        self.threshold_pred_score = config.get('threshold_pred_score', 0.3)
        self.task_type = config.get('task_type', 'clone-detection')

        # 获取任务适配器
        self.task_adapter = TASK_ADAPTERS.get(self.task_type)
        if not self.task_adapter:
            raise ValueError(f"不支持的任务类型: {self.task_type}")

        # 初始化任务适配器
        self.adapter = self.task_adapter(self.task_type, config.get('model_name', 'codebert'))

        # 创建MLM模型用于生成替代词（如果需要）
        self.model_mlm = None
        self.tokenizer_mlm = None

        # 设置随机种子
        seed = config.get('seed', 123456)
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        # 创建args对象
        self.args = type('args', (), {
            'block_size': config.get('block_size', 512),
            'eval_batch_size': config.get('eval_batch_size', 2),
            'device': getattr(model, 'device', torch.device('cuda' if torch.cuda.is_available() else 'cpu')),
        })()

        logger.info(f"✓ ALERT攻击器初始化完成 - 任务类型: {self.task_type}")

    def attack(
        self,
        code_data: Dict[str, str],
        true_label: int,
        substitutes: Optional[Dict[str, list]] = None
    ) -> Dict[str, Any]:
        """
        执行ALERT攻击
        """
        self.start_time = time.time()
        self.query_times = 0

        try:
            code1 = code_data.get('code1', '').strip()
            code2 = code_data.get('code2', '').strip()

            if not code1:
                raise ValueError("code1不能为空")

            logger.info("🎯 开始ALERT攻击")
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
                logger.warning("⚠ ALERT攻击需要提供替代词")
                return {
                    'success': False,
                    'original_code': code1,
                    'adversarial_code': None,
                    'replaced_identifiers': None,
                    'query_times': 0,
                    'time_cost': 0,
                    'error': '缺少替代词信息'
                }

            # 4. 执行ALERT攻击
            logger.info("⚔️ 执行ALERT攻击逻辑...")

            code_pair = (None, None, code1, code2)
            result = self.ga_attack(example, substitutes, code_pair)

            time_cost = self._get_elapsed_time()

            attack_result = {
                'success': result['is_attack_success'] == 1,
                'original_code': code1,
                'adversarial_code': result['adv_program'] if result['adv_program'] != code1 else None,
                'replaced_identifiers': result['replaced_words'] if result['replaced_words'] else None,
                'query_times': self.query_times,
                'time_cost': time_cost,
                'error': None,
                'task_type': self.task_type
            }

            if attack_result['success']:
                logger.info("🎉 ALERT攻击成功！")
                logger.info(f"查询次数: {self.query_times}, 耗时: {time_cost:.2f}秒")
                logger.info(f"替换标识符: {len(attack_result['replaced_identifiers'] or {})} 个")
            else:
                logger.warning("⚠ ALERT攻击失败")

            return attack_result

        except Exception as e:
            logger.error(f"✗ ALERT攻击失败: {e}", exc_info=True)
            return {
                'success': False,
                'original_code': code_data.get('code1', ''),
                'adversarial_code': None,
                'replaced_identifiers': None,
                'query_times': self.query_times,
                'time_cost': self._get_elapsed_time(),
                'error': str(e)
            }

    def filter_identifier(self, code, identifiers):
        """过滤有效的标识符"""
        code_token = get_code_tokens(code)
        filter_identifiers = []
        for identifier in identifiers:
            if is_valid_identifier(identifier):
                position = []
                for index, token in enumerate(code_token):
                    if identifier == token:
                        position.append(index)
                if not all(x > self.args.block_size - 2 for x in position):
                    filter_identifiers.append(identifier)
        return filter_identifiers

    def ga_attack(self, example, substitutes, code):
        """
        ALERT遗传算法攻击核心实现
        """
        code_1 = code[2]
        code_2 = code[3]

        # 获取模型预测
        logits, preds = self.model.get_results([example], self.args.eval_batch_size)
        orig_prob = logits[0]
        orig_label = preds[0]
        current_prob = max(orig_prob)
        true_label = example[1].item()

        if true_label != orig_label:
            return {
                'original_program': code_1,
                'prog_length': len(get_code_tokens(code_1)),
                'adv_program': code_1,
                'true_label': true_label,
                'orig_label': orig_label,
                'temp_label': orig_label,
                'is_attack_success': -1,
                'variable_names': None,
                'names_to_importance_score': None,
                'nb_changed_var': 0,
                'nb_changed_pos': 0,
                'replaced_words': {}
            }

        # 提取标识符
        identifiers, code_tokens = get_identifiers(code_1, 'java')
        variable_names = self.filter_identifier(code_1, identifiers)

        if not variable_names:
            return {
                'original_program': code_1,
                'prog_length': len(code_tokens),
                'adv_program': code_1,
                'true_label': true_label,
                'orig_label': orig_label,
                'temp_label': orig_label,
                'is_attack_success': -2,
                'variable_names': None,
                'names_to_importance_score': None,
                'nb_changed_var': 0,
                'nb_changed_pos': 0,
                'replaced_words': {}
            }

        # 计算重要性评分
        names_to_importance_score = self.get_importance_score(
            example, code_1, code_2, variable_names, true_label
        )

        # 遗传算法攻击
        result = self.genetic_algorithm_attack(
            example, code_1, code_2, substitutes, variable_names,
            names_to_importance_score, true_label, orig_label
        )

        return result

    def get_importance_score(self, example, code_1, code_2, variable_names, true_label):
        """计算变量重要性评分"""
        positions = get_identifier_posistions_from_code(
            get_code_tokens(code_1), variable_names
        )

        if len(positions) == 0:
            return {}

        new_examples = []
        masked_token_list, replace_token_positions = get_masked_code_by_position(
            get_code_tokens(code_1), positions
        )

        code2_tokens, _, _ = _tokenize(code_2, self.tokenizer) if code_2 else []

        for index, code1_tokens in enumerate([get_code_tokens(code_1)] + masked_token_list):
            new_feature = convert_examples_to_features(
                code1_tokens, code2_tokens, true_label, None, None,
                self.tokenizer, self.args, None
            )
            new_examples.append(new_feature)

        new_dataset = CodeDataset(new_examples)
        logits, preds = self.model.get_results(new_dataset, self.args.eval_batch_size)
        orig_probs = logits[0]
        orig_label = preds[0]
        orig_prob = max(orig_probs)

        importance_score = []
        for prob in logits[1:]:
            importance_score.append(orig_prob - prob[orig_label])

        names_to_importance_score = {}
        for idx, score in enumerate(importance_score):
            names_to_importance_score[variable_names[idx]] = score

        return names_to_importance_score

    def genetic_algorithm_attack(self, example, code_1, code_2, substitutes,
                               variable_names, names_to_importance_score,
                               true_label, orig_label):
        """遗传算法攻击实现"""
        # 简化的遗传算法实现
        # 这里应该实现完整的遗传算法逻辑
        # 暂时返回失败结果，需要完整实现

        logger.warning("⚠ ALERT遗传算法攻击暂未完全实现")

        return {
            'original_program': code_1,
            'prog_length': len(get_code_tokens(code_1)),
            'adv_program': code_1,  # 暂时返回原代码
            'true_label': true_label,
            'orig_label': orig_label,
            'temp_label': orig_label,
            'is_attack_success': 0,  # 0表示失败
            'variable_names': variable_names,
            'names_to_importance_score': names_to_importance_score,
            'nb_changed_var': 0,
            'nb_changed_pos': 0,
            'replaced_words': {}
        }

    def get_supported_model_types(self) -> List[str]:
        """返回支持的模型类型"""
        return ['roberta', 'codebert']  # ALERT主要支持RoBERTa系列模型

    def _increment_query(self):
        """增加查询次数"""
        self.query_times += 1
