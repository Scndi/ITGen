"""
ITGen攻击算法实现
真实的ITGen攻击后端实现
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
import operator

# 添加项目路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / 'algorithms'))
sys.path.append(str(BASE_DIR / 'python_parser'))

from algorithms.kmeanspp import kmeans_pp
from algorithms.greedy_ascent import acquisition_maximization_with_indices
from algorithms.hb import HistoryBoard
from algorithms.gp_model import MyGPModel

from utils import (
    CodeDataset, 
    get_identifier_posistions_from_code, 
    is_valid_identifier, 
    get_code_tokens, 
    _tokenize, 
    get_masked_code_by_position,
    set_seed
)
from python_parser.run_parser import get_identifiers, get_gen_code, get_example_batch

from app.attacks.base.base_attacker import BaseAttacker
from app.attacks.base.shared_utils import InputFeatures, convert_examples_to_features
from app.attacks.itgen.adapter import ModelAdapter
from pathlib import Path

logger = logging.getLogger(__name__)


# 使用共享的工具类和函数


class ITGenAttacker(BaseAttacker):
    """
    ITGen攻击算法 - 真实实现
    
    采用基于历史板与高斯过程代理模型的"探索-开发"策略，
    在变量替换空间中搜索能改变预测的对抗样本。
    
    支持多种模型类型：RoBERTa/CodeBERT, GPT2/CodeGPT, CodeT5
    """
    
    def __init__(self, model, tokenizer, config: Dict[str, Any]):
        super().__init__(model, tokenizer, config)
        
        # ITGen攻击器参数
        self.batch_size = 4
        self.update_step = 1
        self.use_sod = True
        self.dpp_type = 'dpp_posterior'
        self.fit_iter = 3
        self.memory_count = 0
        
        # 设置随机种子
        seed = config.get('seed', 123456)
        set_seed(seed)
        
        # 创建args对象（兼容原有代码）
        self.args = type('args', (), {
            'block_size': config.get('block_size', 512),
            'eval_batch_size': config.get('eval_batch_size', 2),
            'device': getattr(model, 'device', torch.device('cuda' if torch.cuda.is_available() else 'cpu')),
            'language': config.get('language', 'java')
        })()
        
        logger.info(f"✓ ITGen攻击器初始化完成")
    
    def attack(
        self,
        code_data: Dict[str, str],
        true_label: int,
        substitutes: Optional[Dict[str, list]] = None
    ) -> Dict[str, Any]:
        """
        执行ITGen攻击 - 真实实现
        """
        self.start_time = time.time()
        self.query_times = 0
        
        try:
            code1 = code_data.get('code1', '').strip()
            code2 = code_data.get('code2', '').strip()
            
            if not code1:
                raise ValueError("code1不能为空")
            
            logger.info(f"🎯 开始ITGen攻击")
            logger.info(f"  代码1长度: {len(code1)} 字符")
            if code2:
                logger.info(f"  代码2长度: {len(code2)} 字符")
            
            # 1. 准备示例数据并验证模型预测
            code1_tokens = self.tokenizer.tokenize(code1)
            code2_tokens = self.tokenizer.tokenize(code2) if code2 else []
            
            feature = convert_examples_to_features(
                code1_tokens, code2_tokens, true_label, None, None, 
                self.tokenizer, self.args, None
            )
            example = (torch.tensor(feature.input_ids), torch.tensor(true_label))
            
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
            
            # 2. 检查替代词
            if not substitutes:
                logger.warning("⚠ 未提供替代词，无法执行攻击")
                return {
                    'success': False,
                    'original_code': code1,
                    'adversarial_code': None,
                    'replaced_identifiers': None,
                    'query_times': 0,
                    'time_cost': 0,
                    'error': '缺少替代词信息'
                }
            
            # 3. 执行ITGen攻击
            logger.info("⚔️ 执行ITGen攻击逻辑...")
            code_pair = (None, None, code1, code2)
            example_start_time = time.time()
            
            adv_code, is_success, replaced_words = self.itgen_attack(
                example, substitutes, code_pair, self.query_times, logits, example_start_time
            )
            
            time_cost = self._get_elapsed_time()
            
            result = {
                'success': is_success == 1,
                'original_code': code1,
                'adversarial_code': adv_code if adv_code else None,
                'replaced_identifiers': replaced_words if replaced_words else None,
                'query_times': self.query_times,
                'time_cost': time_cost,
                'error': None
            }
            
            if result['success']:
                logger.info(f"🎉 攻击成功！查询次数: {self.query_times}, 耗时: {time_cost:.2f}秒")
            else:
                logger.warning(f"⚠ 攻击失败，查询次数: {self.query_times}, 耗时: {time_cost:.2f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"✗ ITGen攻击失败: {e}", exc_info=True)
            return {
                'success': False,
                'original_code': code_data.get('code1', ''),
                'adversarial_code': None,
                'replaced_identifiers': None,
                'query_times': self.query_times,
                'time_cost': self._get_elapsed_time(),
                'error': str(e)
            }
    
    def _itgen_attack_impl(
        self,
        code1: str,
        code2: str,
        substitutes: Dict[str, list],
        true_label: int
    ) -> tuple:
        """
        ITGen攻击核心实现

        这是基础实现，尝试生成对抗样本。
        实际的ITGen算法应该实现更复杂的语法树变换和优化。

        Returns:
            (adversarial_code, replaced_identifiers)
        """
        import random
        random.seed(self.config.get('seed', 123456))
        max_queries = self.config.get('max_queries', 500)

        logger.info(f"🔄 开始ITGen攻击，最大查询次数: {max_queries}")

        # 原始代码作为基准
        original_code = code1
        adversarial_code = code1
        replaced_identifiers = {}
        best_success = False

        # 获取可用的标识符列表
        available_identifiers = list(substitutes.keys())
        if not available_identifiers:
            logger.warning("⚠ 没有可用的标识符进行替换")
            return adversarial_code, replaced_identifiers

        # ITGen基础攻击策略：尝试不同的标识符替换组合
        max_attempts = min(len(available_identifiers), 10)  # 限制尝试次数

        for attempt in range(max_attempts):
            if self.query_times >= max_queries:
                logger.warning(f"⚠ 达到最大查询次数限制: {max_queries}")
                break

            # 随机选择要替换的标识符数量 (1-3个)
            num_to_replace = random.randint(1, min(3, len(available_identifiers)))

            # 随机选择标识符
            selected_identifiers = random.sample(available_identifiers, num_to_replace)

            # 为每个选中的标识符选择替换词
            current_replacements = {}
            current_code = original_code

            for identifier in selected_identifiers:
                candidates = substitutes[identifier]
                if candidates:
                    # 随机选择一个候选词
                    replacement = random.choice(candidates)
                    current_replacements[identifier] = replacement
                    current_code = current_code.replace(identifier, replacement)

            # 检查替换是否有效（代码长度变化不大）
            if abs(len(current_code) - len(original_code)) > len(original_code) * 0.5:
                logger.debug(f"⚠ 替换导致代码长度变化过大，跳过此次尝试")
                continue

            # 验证对抗样本是否成功欺骗模型
            try:
                # 对抗样本进行预测
                adv_tokens = self.tokenizer.tokenize(current_code)
                adv_feature = convert_examples_to_features(
                    adv_tokens, [], true_label, None, None,
                    self.tokenizer, self.args, None
                )
                adv_example = (torch.tensor(adv_feature.input_ids), torch.tensor(true_label))
                adv_logits, adv_preds = self.model.get_results([adv_example], self.args.eval_batch_size)
                adv_predicted_label = adv_preds[0]

                self._increment_query()  # 增加查询计数

                # 检查是否成功欺骗模型（预测标签改变）
                if adv_predicted_label != true_label:
                    logger.info(f"🎉 攻击成功！在第{attempt+1}次尝试中找到有效对抗样本")
                    logger.info(f"原始预测: {true_label}, 对抗预测: {adv_predicted_label}")
                    adversarial_code = current_code
                    replaced_identifiers = current_replacements
                    best_success = True
                    break
                else:
                    logger.debug(f"⚠ 第{attempt+1}次尝试失败，模型仍能正确识别")

            except Exception as e:
                logger.warning(f"⚠ 第{attempt+1}次尝试出现异常: {e}")
                continue

        if not best_success:
            logger.warning("⚠ ITGen攻击未能生成有效的对抗样本")

        return adversarial_code, replaced_identifiers
    
    def get_supported_model_types(self) -> List[str]:
        """返回支持的模型类型"""
        return ['roberta', 'gpt2', 'codet5']  # ITGen支持多种模型

