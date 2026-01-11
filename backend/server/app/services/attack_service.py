import sys
import os

# ========== 重要：必须在导入任何 huggingface 相关模块之前设置镜像站 ==========
# 配置 Hugging Face 镜像站（必须在导入 huggingface_hub 或 transformers 之前设置）
# 优先使用环境变量，如果没有则使用默认镜像站
if 'HF_ENDPOINT' not in os.environ:
    # 尝试从配置文件读取，如果无法导入则使用默认值
    try:
        # 延迟导入 Config，避免循环依赖
        import importlib.util
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')
        spec = importlib.util.spec_from_file_location("config", config_path)
        if spec and spec.loader:
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            hf_endpoint = getattr(config_module.Config, 'HF_ENDPOINT', 'https://hf-mirror.com')
        else:
            hf_endpoint = 'https://hf-mirror.com'
    except Exception:
        hf_endpoint = 'https://hf-mirror.com'
    
    os.environ['HF_ENDPOINT'] = hf_endpoint
    # 同时设置 HF_HUB_ENDPOINT（某些版本可能需要）
    os.environ['HF_HUB_ENDPOINT'] = hf_endpoint
else:
    hf_endpoint = os.environ['HF_ENDPOINT']
# ========== 镜像站配置结束 ==========

import json
import random
import re
import torch
import numpy as np
from pathlib import Path
import time
import logging
from typing import Dict, Any, List

# 导入脚本执行服务
from app.services.script_execution_service import ScriptExecutionService
from app.config import Config
from app.utils.device import get_device_from_config
from app.models.db_models import Model as DBModel
from pathlib import Path

logger = logging.getLogger(__name__)

# 如果配置文件中有不同的设置，且之前使用的是默认值，则更新为配置文件的值
# 注意：此时 transformers 可能已经导入，但环境变量仍会影响后续的模型下载
if hasattr(Config, 'HF_ENDPOINT') and Config.HF_ENDPOINT != hf_endpoint:
    os.environ['HF_ENDPOINT'] = Config.HF_ENDPOINT
    os.environ['HF_HUB_ENDPOINT'] = Config.HF_ENDPOINT
    hf_endpoint = Config.HF_ENDPOINT
    logger.info(f"✓ 更新 Hugging Face 镜像站为配置文件中的值: {hf_endpoint}")
else:
    logger.info(f"✓ Hugging Face 镜像站: {hf_endpoint}")

# 添加项目路径到sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))

# 支持的任务类型路径
SUPPORTED_TASK_TYPES = [
    'clone-detection',
    'code-summarization',
    'vulnerability-prediction',
    'authorship-attribution',
    'vulnerability-detection'
]

# 为所有支持的任务类型添加路径
for task_type in SUPPORTED_TASK_TYPES:
    task_code_path = BASE_DIR / 'roberta' / task_type / 'code'
    if task_code_path.exists():
        sys.path.append(str(task_code_path))

sys.path.append(str(BASE_DIR / 'python_parser'))

# 导入ITGen相关模块
# ITGen现在通过统一接口使用，不再需要直接导入


class AttackService:
    """攻击服务类 - 统一攻击接口，支持多种攻击方法"""

    def __init__(self):
        """初始化攻击服务"""
        self.models = {}  # 模型缓存
        self.attackers = {}  # 统一攻击器缓存
        self.mlm_model = None  # MLM模型缓存
        self.mlm_tokenizer = None  # MLM tokenizer缓存
        self.id2token_cache = None  # id2token缓存
        self.script_executor = ScriptExecutionService()  # 脚本执行器（兼容旧接口）
        
    def _load_model(self, model_name='codebert', model_id: int = None, task_type: str = 'clone-detection'):
        """
        加载模型（从数据库或使用默认配置）

        Args:
            model_name: 模型名称
            model_id: 模型ID（如果提供，从数据库加载）
            task_type: 任务类型 (clone-detection, code-summarization, vulnerability-prediction, authorship-attribution, vulnerability-detection)
        """
        # 验证任务类型
        if task_type not in SUPPORTED_TASK_TYPES:
            raise ValueError(f"不支持的任务类型: {task_type}。支持的任务类型: {SUPPORTED_TASK_TYPES}")
        # 尝试使用本地缓存，避免网络问题
        cache_dir = os.environ.get('HF_HOME', os.path.expanduser('~/.cache/huggingface'))
        
        # 从数据库加载模型信息
        model_path = None
        tokenizer_path = None
        checkpoint_path = None
        mlm_model_path = None
        
        # 如果提供了model_id，直接使用；否则通过model_name查找
        db_model = None
        if model_id:
            db_model = DBModel.query.filter_by(id=model_id).first()
        elif model_name:
            # 通过model_name查找模型
            db_model = DBModel.query.filter_by(model_name=model_name).first()
            if db_model:
                model_id = db_model.id
        
        if db_model:
            model_path = db_model.model_path
            tokenizer_path = db_model.tokenizer_path
            checkpoint_path = db_model.checkpoint_path
            mlm_model_path = db_model.mlm_model_path
            logger.info(f"✓ 从数据库加载模型信息: {db_model.model_name} (ID: {db_model.id})")
        else:
            if model_id:
                logger.warning(f"⚠ 模型ID {model_id} 不存在，使用默认配置")
            elif model_name:
                logger.warning(f"⚠ 模型名称 {model_name} 不存在，使用默认配置")
        
        # 如果没有从数据库获取，使用默认路径
        if not model_path:
            model_path = 'microsoft/codebert-base'
        if not tokenizer_path:
            tokenizer_path = 'microsoft/codebert-base'
        
        # 判断是本地路径还是HuggingFace路径
        def is_local_path(path: str) -> bool:
            """判断是否为本地路径"""
            return os.path.exists(path) or Path(path).is_absolute() or not '/' in path or path.startswith('./') or path.startswith('../')
        
        try:
            # 加载tokenizer
            if is_local_path(tokenizer_path):
                tokenizer = RobertaTokenizer.from_pretrained(
                    tokenizer_path,
                    local_files_only=True
                )
                logger.info(f"✓ Tokenizer从本地加载: {tokenizer_path}")
            else:
                tokenizer = RobertaTokenizer.from_pretrained(
                    tokenizer_path,
                    cache_dir=cache_dir
                )
                logger.info(f"✓ Tokenizer从HuggingFace加载: {tokenizer_path}")
            
            # 加载配置
            if is_local_path(model_path):
                config = RobertaConfig.from_pretrained(
                    model_path,
                    local_files_only=True
                )
                logger.info(f"✓ 配置从本地加载: {model_path}")
            else:
                config = RobertaConfig.from_pretrained(
                    model_path,
                    cache_dir=cache_dir
                )
                logger.info(f"✓ 配置从HuggingFace加载: {model_path}")
            
            # 根据任务类型设置标签数量
            if task_type in ['clone-detection', 'vulnerability-prediction', 'vulnerability-detection']:
                config.num_labels = 2  # 二分类任务
            elif task_type == 'authorship-attribution':
                config.num_labels = 10  # 多分类任务（根据数据集调整）
            elif task_type == 'code-summarization':
                config.num_labels = 1  # 生成任务
            else:
                config.num_labels = 2  # 默认二分类

            logger.info(f"✓ 任务类型: {task_type}, 标签数量: {config.num_labels}")
            
            # 加载模型
            if is_local_path(model_path):
                encoder = RobertaModel.from_pretrained(
                    model_path,
                    local_files_only=True
                )
                logger.info(f"✓ 模型编码器从本地加载: {model_path}")
            else:
                encoder = RobertaModel.from_pretrained(
                    model_path,
                    cache_dir=cache_dir
                )
                logger.info(f"✓ 模型编码器从HuggingFace加载: {model_path}")
            
        except Exception as e:
            logger.error(f"✗ 加载模型失败: {e}")
            raise
        
        # 获取计算设备（优先GPU，找不到则CPU）
        device = get_device_from_config(Config)
        args = type('args', (), {
            'block_size': 512,
            'device': device,
            'model_name': model_name,
            'eval_batch_size': 4,
            'tokenizer': tokenizer,
            'language': 'java'
        })()
        
        model = Model(encoder, config, tokenizer, args)
        
        # 加载训练好的权重（检查点）
        if checkpoint_path and Path(checkpoint_path).exists():
            try:
                model.load_state_dict(torch.load(checkpoint_path, map_location=device), strict=False)
                logger.info(f"✓ 加载微调权重: {checkpoint_path}")
            except Exception as e:
                logger.warning(f"⚠ 加载模型权重失败: {e}, 使用预训练模型")
        else:
            # 根据任务类型尝试加载默认检查点
            default_checkpoint = None

            # 尝试多个可能的检查点路径
            possible_paths = [
                BASE_DIR / model_name / task_type / 'saved_models' / 'checkpoint-best-f1' / f'{model_name}_model.bin',
                BASE_DIR / model_name / task_type / 'saved_models' / 'checkpoint-best-f1' / 'pytorch_model.bin',
                BASE_DIR / 'saved_models' / model_name / task_type / 'checkpoint-best-f1' / f'{model_name}_model.bin',
                BASE_DIR / 'CodeBERT' / task_type / 'saved_models' / 'checkpoint-best-f1' / 'codebert_model.bin',  # 向后兼容
            ]

            for checkpoint_path in possible_paths:
                if checkpoint_path.exists():
                    default_checkpoint = checkpoint_path
                    break

            if default_checkpoint:
                try:
                    model.load_state_dict(torch.load(default_checkpoint, map_location=device), strict=False)
                    logger.info(f"✓ 加载默认微调权重: {default_checkpoint}")
                except Exception as e:
                    logger.warning(f"⚠ 加载默认权重失败: {e}")
            else:
                logger.info("ℹ 未找到检查点文件，使用预训练模型")
        
        # 移动到GPU
        model.to(device)
        model.eval()
        logger.info(f"✓ 模型已加载到: {device}")
        
        # 缓存模型
        self.models[model_name] = {
            'model': model,
            'tokenizer': tokenizer,
            'config': config,
            'args': args
        }
        
        return self.models[model_name]
    
    def _create_attacker(self, model_name='codebert', model_id: int = None, task_type: str = 'clone-detection'):
        """
        创建攻击器（旧方法，保持向后兼容）
        """
        logger.warning("⚠ 使用旧的攻击器创建方法，建议使用_create_unified_attacker")
        return self._create_unified_attacker('itgen', None, None, {'model_id': model_id, 'task_type': task_type})

    def _create_unified_attacker(self, method: str, model=None, tokenizer=None, config: Dict[str, Any] = None):
        """
        创建统一攻击器

        Args:
            method: 攻击方法 ('itgen', 'beam', 'alert', etc.)
            model: 模型实例（如果为None，会从config中获取）
            tokenizer: tokenizer实例（如果为None，会从config中获取）
            config: 配置参数

        Returns:
            统一攻击器实例
        """
        if config is None:
            config = {}

        model_id = config.get('model_id')
        model_name = config.get('model_name', 'codebert')
        task_type = config.get('task_type', 'clone-detection')

        # 如果没有提供model和tokenizer，需要加载
        if model is None or tokenizer is None:
            model_data = self._load_model(model_name, model_id=model_id, task_type=task_type)
            model = model_data['model']
            tokenizer = model_data['tokenizer']

        # 创建缓存key
        cache_key = f"{method}_{model_name}_{model_id}" if model_id else f"{method}_{model_name}"
        if cache_key in self.attackers:
            logger.debug(f"使用缓存的攻击器: {cache_key}")
            return self.attackers[cache_key]

        logger.info(f"创建统一攻击器: {method}")

        try:
            # 获取攻击器类
            from app.attacks import get_attacker_class
            attacker_class = get_attacker_class(method)

            # 创建攻击器
            attacker = attacker_class(model, tokenizer, config)
            self.attackers[cache_key] = attacker
            logger.info(f"✓ {method.upper()}攻击器创建成功")

            return attacker

        except Exception as e:
            logger.error(f"✗ 创建{method.upper()}攻击器失败: {e}")
            raise
    
    def _load_mlm_model(self, base_model='microsoft/codebert-base-mlm', model_id: int = None, model_name: str = None):
        """
        加载CodeBERT MLM模型（带缓存）
        
        Args:
            base_model: 默认MLM模型路径
            model_id: 模型ID（如果提供，从数据库加载MLM模型路径）
            model_name: 模型名称（如果提供且model_id为None，通过名称查找）
        """
        if self.mlm_model is not None and model_id is None and model_name is None:
            logger.debug("使用缓存的MLM模型")
            return self.mlm_model, self.mlm_tokenizer
        
        # 从数据库加载MLM模型路径
        mlm_model_path = base_model
        db_model = None
        if model_id:
            db_model = DBModel.query.filter_by(id=model_id).first()
        elif model_name:
            db_model = DBModel.query.filter_by(model_name=model_name).first()
        
        if db_model and db_model.mlm_model_path:
            mlm_model_path = db_model.mlm_model_path
            logger.info(f"✓ 从数据库获取MLM模型路径: {mlm_model_path}")
        
        logger.info(f"加载MLM模型: {mlm_model_path}")
        try:
            from transformers import RobertaForMaskedLM, RobertaTokenizer
            
            # 判断是本地路径还是HuggingFace路径
            def is_local_path(path: str) -> bool:
                return os.path.exists(path) or Path(path).is_absolute() or not '/' in path or path.startswith('./') or path.startswith('../')
            
            cache_dir = os.environ.get('HF_HOME', os.path.expanduser('~/.cache/huggingface'))
            
            # 加载tokenizer
            if is_local_path(mlm_model_path):
                tokenizer = RobertaTokenizer.from_pretrained(
                    mlm_model_path,
                    local_files_only=True
                )
                logger.info(f"✓ MLM Tokenizer从本地加载: {mlm_model_path}")
            else:
                tokenizer = RobertaTokenizer.from_pretrained(
                    mlm_model_path,
                    cache_dir=cache_dir
                )
                logger.info(f"✓ MLM Tokenizer从HuggingFace加载: {mlm_model_path}")
            
            # 加载MLM模型
            if is_local_path(mlm_model_path):
                model = RobertaForMaskedLM.from_pretrained(
                    mlm_model_path,
                    local_files_only=True
                )
                logger.info(f"✓ MLM模型从本地加载: {mlm_model_path}")
            else:
                model = RobertaForMaskedLM.from_pretrained(
                    mlm_model_path,
                    cache_dir=cache_dir
                )
                logger.info(f"✓ MLM模型从HuggingFace加载: {mlm_model_path}")
            
            # 获取计算设备（优先GPU，找不到则CPU）
            device = get_device_from_config(Config)
            model.to(device)
            model.eval()
            
            logger.info(f"✓ MLM模型加载成功，设备: {device}")
            
            self.mlm_model = model
            self.mlm_tokenizer = tokenizer
            
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"✗ 加载MLM模型失败: {e}")
            raise
    
    def build_id2token_from_code(self, code_data, language='java', vocab_size=5000):
        """
        从输入代码中提取标识符构建词汇库（id2token）
        
        Args:
            code_data: 代码数据字典，包含code1和code2
            language: 编程语言
            vocab_size: 词汇库大小限制
        
        Returns:
            id2token: 词汇列表
            token2idx: 词汇到索引的映射
        """
        logger.info(f"🔤 从代码中提取标识符构建词汇库（最多{vocab_size}个）...")
        
        try:
            from utils import build_vocab
            
            code_tokens = []
            processed_count = 0
            
            # for idx, code_data in enumerate(code_data_list):
            #     if not isinstance(code_data, dict):
            #         continue
                    
            code1 = code_data.get('code1', '')
            code2 = code_data.get('code2', '')
                
            # 提取code1的标识符
            try:
                identifiers, tokens = get_identifiers(code1, language)
                code_tokens.append(tokens)
                processed_count += 1
                logger.debug(f"✓ 从code1提取了 {len(tokens)} 个token")
            except Exception as e:
                logger.warning(f"⚠ 提取code1标识符失败: {e}")
            
            # 提取code2的标识符
            if code2:
                try:
                    identifiers, tokens = get_identifiers(code2, language)
                    code_tokens.append(tokens)
                    processed_count += 1
                    logger.debug(f"✓ 从code2提取了 {len(tokens)} 个token")
                except Exception as e:
                    logger.warning(f"⚠ 提取code2标识符失败: {e}")
        
            if len(code_tokens) == 0:
                logger.error("✗ 未能提取任何标识符")
                return [], {}
            
            # 构建词汇库
            id2token, token2idx = build_vocab(code_tokens, vocab_size)
            
            logger.info(f"✓ 成功处理 {processed_count} 段代码")
            logger.info(f"✓ 词汇库大小: {len(id2token)} 个标识符")
            logger.debug(f"  示例词汇（前10个）: {id2token[:10]}")
            
            # 缓存结果
            self.id2token_cache = id2token
            
            return id2token, token2idx
            
        except Exception as e:
            logger.error(f"✗ 构建id2token失败: {e}", exc_info=True)
            return [], {}
    
    def sample_random_substitutes(self, code, substitutes, id2token, num_random_per_key=50):
        """
        为每个变量采样随机替换词（模拟attack_itgen.py的逻辑）
        
        Args:
            code: 原始代码
            substitutes: 原始替换词字典 {identifier: [candidates]}
            id2token: 词汇库列表
            num_random_per_key: 每个变量分配多少个随机词
        
        Returns:
            sampled_substitutes: 采样后的替换词字典
        """
        import re
        
        if not id2token:
            logger.warning("⚠ id2token为空，返回原始替换词")
            return substitutes
        
        logger.info("🎲 采样随机替换词...")
        
        # 正则表达式匹配有效标识符
        uid_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        
        # 计算需要的总词数
        total_needed = len(substitutes.keys()) * num_random_per_key
        
        if len(id2token) < total_needed:
            logger.warning(f"⚠ 词汇库({len(id2token)})不足以采样{total_needed}个词，使用全部词汇")
            total_needed = len(id2token)
        
        # 随机采样
        selected_tmp_sub = random.sample(id2token, min(total_needed, len(id2token)))
        
        # 分组：每个变量分配num_random_per_key个词
        sublists = [selected_tmp_sub[i:i+num_random_per_key] for i in range(0, len(selected_tmp_sub), num_random_per_key)]
        
        tmp_sub = []
        for sub in sublists:
            tmp = []
            for s in sub:
                # 过滤条件：
                # 1. 符合标识符格式
                # 2. 不在原始代码中出现
                if bool(uid_pattern.match(s)) and code.find(s) == -1:
                    tmp.append(s)
            tmp_sub.append(tmp)
        
        # 创建新的替换词字典
        sampled_substitutes = dict(zip(substitutes.keys(), tmp_sub))
        
        # 统计信息
        total_sampled = sum(len(v) for v in sampled_substitutes.values())
        logger.info(f"✓ 采样完成")
        logger.info(f"  原始变量数: {len(substitutes)}")
        logger.info(f"  采样后的替换词总数: {total_sampled}")
        logger.debug(f"  示例: {dict(list(sampled_substitutes.items())[:2])}")
        
        return sampled_substitutes
    
    def generate_substitutes_with_algorithm(self, code1, code2, language='java', block_size=512, top_k=60, base_model='microsoft/codebert-base-mlm', model_id=None, model_name=None, **kwargs):
        """
        使用算法生成替代词（基于CodeBERT MLM）
        
        Args:
            code1: 代码1
            code2: 代码2
            language: 编程语言
            block_size: 代码块大小
            top_k: 每位置候选词数量
            base_model: 默认MLM模型路径
            model_id: 模型ID（可选）
            model_name: 模型名称（可选）
            **kwargs: 其他参数
        
        Returns:
            替代词字典 {identifier: [candidates]}
        
        算法流程（参考get_substitutes.py）:
        1. 提取代码标识符
        2. 使用CodeBERT MLM预测top-k候选词
        3. 使用cosine similarity筛选最相似的候选词
        4. 转换为实际词并验证
        """
        import copy
        
        # 注意：此函数没有显式设置随机种子，因为MLM预测本身是确定性的
        # 但与get_substitutes.py保持一致，避免其他潜在的非确定性操作
        from python_parser.run_parser import get_identifiers, remove_comments_and_docstrings
        from utils import (
            _tokenize, 
            get_identifier_posistions_from_code,
            get_substitues,
            is_valid_variable_name,
            is_valid_substitue
        )
        
        logger.info("🔧 开始使用算法生成替代词...")
        
        try:
            # 加载MLM模型（支持通过model_id或model_name）
            mlm_model, tokenizer_mlm = self._load_mlm_model(
                base_model, 
                model_id=model_id,
                model_name=model_name
            )
            device = next(mlm_model.parameters()).device
            
            # 步骤1: 提取标识符
            try:
                identifiers, code_tokens = get_identifiers(
                    remove_comments_and_docstrings(code1, language),
                    language
                )
            except:
                identifiers, code_tokens = get_identifiers(code1, language)
            
            processed_code = " ".join(code_tokens)
            
            # 步骤2: Tokenize
            words, sub_words, keys = _tokenize(processed_code, tokenizer_mlm)
            
            # 步骤3: 提取有效的变量名
            variable_names = []
            for name in identifiers:
                if ' ' in name[0].strip():
                    continue
                variable_names.append(name[0])
            
            logger.info(f"✓ 提取到 {len(variable_names)} 个变量名")
            
            # 步骤4: 准备输入
            sub_words = [tokenizer_mlm.cls_token] + sub_words[:block_size - 2] + [tokenizer_mlm.sep_token]
            input_ids_ = torch.tensor([tokenizer_mlm.convert_tokens_to_ids(sub_words)])
            input_ids_ = input_ids_.to(device)
            
            # 步骤5: MLM预测
            logger.info("🤖 使用MLM模型预测候选词...")
            logger.info(f"  输入序列长度: {len(sub_words)}")
            with torch.no_grad():
                word_predictions = mlm_model(input_ids_)[0].squeeze()  # seq-len(sub) vocab
                word_pred_scores_all, word_predictions = torch.topk(word_predictions, top_k, -1)  # seq-len k
            
            word_predictions = word_predictions[1:len(sub_words) + 1, :]
            word_pred_scores_all = word_pred_scores_all[1:len(sub_words) + 1, :]
            logger.info(f"✓ MLM预测完成，候选词形状: {word_predictions.shape}")
            
            # 步骤6: 获取标识符位置
            names_positions_dict = get_identifier_posistions_from_code(words, variable_names)
            logger.info(f"✓ 获取到 {len(names_positions_dict)} 个标识符的位置信息")
            
            # 步骤7: 为每个标识符生成替代词
            variable_substitue_dict = {}
            
            logger.info("🔍 计算原始embeddings...")
            with torch.no_grad():
                orig_embeddings = mlm_model.roberta(input_ids_)[0]
            logger.info("✓ 原始embeddings计算完成")
            
            cos = torch.nn.CosineSimilarity(dim=1, eps=1e-6)
            
            total_vars = len(names_positions_dict)
            processed_vars = 0
            start_time_loop = time.time()
            for tgt_word in names_positions_dict.keys():
                processed_vars += 1
                tgt_positions = names_positions_dict[tgt_word]
                
                if not is_valid_variable_name(tgt_word, lang=language):
                    logger.debug(f"  跳过变量 {processed_vars}/{total_vars}: {tgt_word} (无效变量名)")
                    continue
                
                logger.info(f"  处理变量 {processed_vars}/{total_vars}: {tgt_word} (共 {len(tgt_positions)} 个位置)")
                
                # 收集所有位置的替代词
                all_substitues = []
                
                for pos_idx, one_pos in enumerate(tgt_positions):
                    logger.debug(f"    处理位置 {pos_idx+1}/{len(tgt_positions)}: {one_pos}")
                    if keys[one_pos][0] >= word_predictions.size()[0]:
                        continue
                    
                    substitutes = word_predictions[keys[one_pos][0]:keys[one_pos][1]]  # L, k
                    word_pred_scores = word_pred_scores_all[keys[one_pos][0]:keys[one_pos][1]]
                    
                    # 确保 substitutes 在 device/id 上与 input_ids_ 一致（防止设备不匹配）
                    # 注意：word_predictions 应该已在 device 上，但保险起见加此检查
                    if substitutes.device != device:
                        logger.warning(f"设备不匹配: substitutes 在 {substitutes.device}, device 是 {device}")
                        substitutes = substitutes.to(device)
                        word_pred_scores = word_pred_scores.to(device)
                    
                    orig_word_embed = orig_embeddings[0][keys[one_pos][0]+1:keys[one_pos][1]+1].to(device)
                    
                    # 使用cosine similarity筛选
                    similar_substitutes = []
                    similar_word_pred_scores = []
                    sims = []
                    subwords_leng, nums_candis = substitutes.size()
                    logger.info(f"    位置 {one_pos}: 需要计算 {nums_candis} 个候选词的相似度（这可能需要一些时间...）")
                    
                    # 批量处理候选词，每批处理一部分以减少日志输出
                    batch_size = max(10, nums_candis // 10)  # 每批至少10个，或总数的10%
                    pos_start_time = time.time()
                    for batch_start in range(0, nums_candis, batch_size):
                        batch_end = min(batch_start + batch_size, nums_candis)
                        if batch_start == 0 or (batch_start + batch_size) % (batch_size * 5) == 0:
                            elapsed = time.time() - pos_start_time
                            logger.info(f"    处理候选词 {batch_start+1}-{batch_end}/{nums_candis} (已用时: {elapsed:.1f}秒)")
                        
                        for i in range(batch_start, batch_end):
                            new_ids_ = copy.deepcopy(input_ids_)
                            # 确保 new_ids_ 在正确的设备上
                            if new_ids_.device != device:
                                new_ids_ = new_ids_.to(device)
                            # 替换词得到新embeddings
                            new_ids_[0][keys[one_pos][0]+1:keys[one_pos][1]+1] = substitutes[:, i]
                            
                            with torch.no_grad():
                                new_embeddings = mlm_model.roberta(new_ids_)[0]
                            new_word_embed = new_embeddings[0][keys[one_pos][0]+1:keys[one_pos][1]+1]
                            
                            sim = sum(cos(orig_word_embed, new_word_embed)) / subwords_leng
                            sims.append((i, sim.item()))
                    
                    pos_elapsed = time.time() - pos_start_time
                    logger.info(f"    ✓ 位置 {one_pos} 处理完成，用时: {pos_elapsed:.1f}秒")
                    
                    # 排序取top 30
                    sims = sorted(sims, key=lambda x: x[1], reverse=True)
                    
                    for i in range(int(nums_candis / 2)):
                        similar_substitutes.append(substitutes[:, sims[i][0]].reshape(subwords_leng, -1))
                        similar_word_pred_scores.append(word_pred_scores[:, sims[i][0]].reshape(subwords_leng, -1))
                    
                    if len(similar_substitutes) == 0:
                        continue
                        
                    similar_substitutes = torch.cat(similar_substitutes, 1).to(device)
                    similar_word_pred_scores = torch.cat(similar_word_pred_scores, 1).to(device)
                    
                    # 转换为实际词
                    substitutes = get_substitues(
                        similar_substitutes,
                        tokenizer_mlm,
                        mlm_model,
                        1,  # use_bpe
                        similar_word_pred_scores,
                        0   # threshold
                    )
                    all_substitues += substitutes
                
                all_substitues = set(all_substitues)
                
                # 验证并添加替代词
                for tmp_substitue in all_substitues:
                    if tmp_substitue.strip() in variable_names:
                        continue
                    if not is_valid_substitue(tmp_substitue.strip(), tgt_word, language):
                        continue
                    if tgt_word not in variable_substitue_dict:
                        variable_substitue_dict[tgt_word] = []
                    variable_substitue_dict[tgt_word].append(tmp_substitue)
                
                var_elapsed = time.time() - start_time_loop
                logger.info(f"  ✓ 变量 {tgt_word} 处理完成，生成 {len(variable_substitue_dict.get(tgt_word, []))} 个替代词 (总用时: {var_elapsed:.1f}秒)")
            
            total_elapsed = time.time() - start_time_loop
            logger.info(f"✓ 成功生成替代词，包含 {len(variable_substitue_dict)} 个标识符 (总用时: {total_elapsed:.1f}秒)")
            for var, subs in list(variable_substitue_dict.items())[:3]:
                logger.debug(f"  {var}: {len(subs)} 个候选词")
            
            return variable_substitue_dict
            
        except Exception as e:
            logger.error(f"✗ 算法生成替代词失败: {e}", exc_info=True)
            return {}
    
    def load_substitutes_from_file(self, file_path=None):
        """
        从文件加载替代词
        
        Args:
            file_path: 替代词文件路径，默认为dataset/preprocess/test_subs_clone.jsonl
        
        Returns:
            替代词列表，每个元素是一个包含substitutes字段的字典
        """
        if file_path is None:
            # 默认路径
            file_path = BASE_DIR / 'dataset' / 'preprocess' / 'test_subs_clone.jsonl'
        
        substitutes_list = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    substitutes_list.append(data.get('substitutes', {}))
            
            logger.info(f"✓ 从文件加载了 {len(substitutes_list)} 个样本的替代词: {file_path}")
            return substitutes_list
        except Exception as e:
            logger.error(f"✗ 加载替代词文件失败: {e}")
            return []
    
    def get_substitutes_for_code(self, code_data, strategy='a', **kwargs):
        """
        获取代码的替代词（统一接口）
        
        Args:
            code_data: 包含code1和code2的字典
            strategy: 获取策略 ('file' 或 'algorithm')
            **kwargs: 其他参数
                - file_index: 文件中的索引（当strategy='file'时）
                - language: 编程语言（当strategy='algorithm'时）
        
        Returns:
            替代词字典
        """
        # if strategy == 'file':
        #     # 从文件加载
        #     substitutes_list = self.load_substitutes_from_file()
        #     file_index = kwargs.get('file_index', 0)
            
        #     if 0 <= file_index < len(substitutes_list):
        #         return substitutes_list[file_index]
        #     elif len(substitutes_list) > 0:
        #         logger.warning("⚠️ 未指定file_index，使用第一个替代词")
        #         return substitutes_list[0]
        #     else:
        #         logger.error("✗ 文件中没有替代词")
        #         return {}
        if strategy == 'algorithm':
            # 使用算法生成
            code1 = code_data.get('code1')
            code2 = code_data.get('code2', '')
            language = kwargs.get('language', 'java')
            
            return self.generate_substitutes_with_algorithm(code1, code2, language)
        else:
            logger.error(f"✗ 未知的获取策略: {strategy}")
            return {}
    
    def attack(self, code_data: Dict[str, str], target_model='codebert', language='java', config=None, method='itgen'):
        """
        执行单组数据攻击 - 使用统一攻击接口

        Args:
            code_data: 包含code1和code2的字典
            target_model: 目标模型名称
            language: 编程语言
            config: 攻击配置参数
            method: 攻击方法 ('itgen', 'beam', 'alert', etc.)

        Returns:
            攻击结果字典
        """
        start_time = time.time()
        logger.info("=" * 60)
        logger.info("🎯 开始单次攻击任务")
        logger.info(f"模型: {target_model}, 方法: {method}, 语言: {language}")
        logger.info("=" * 60)

        try:
            # ========== 步骤1: 验证输入数据 ==========
            logger.info("📝 步骤1: 验证输入数据")
            code1 = code_data.get('code1', '').strip()
            code2 = code_data.get('code2', '').strip()

            if not code1:
                raise ValueError("code1不能为空")

            logger.info(f"✓ 代码1长度: {len(code1)} 字符")
            if code2:
                logger.info(f"✓ 代码2长度: {len(code2)} 字符")

            # 验证配置参数
            if config is None:
                config = {}
            true_label = config.get('true_label', 1)

            logger.info(f"✓ 真实标签: {true_label}")
            logger.info(f"✓ 攻击方法: {method}")

            # ========== 步骤2: 加载模型和创建统一攻击器 ==========
            logger.info("\n📦 步骤2: 加载模型和攻击器")
            model_id = config.get('model_id')
            task_type = config.get('task_type', 'clone-detection')

            # 加载模型
            model_data = self._load_model(target_model, model_id=model_id, task_type=task_type)
            model = model_data['model']
            tokenizer = model_data['tokenizer']

            # 创建统一攻击器
            attacker = self._create_unified_attacker(method, model, tokenizer, config)
            logger.info("✓ 模型和攻击器准备就绪")

            # ========== 步骤3: 准备替代词 ==========
            logger.info("\n🔤 步骤3: 准备替代词")

            if 'substitutes' in config and config['substitutes']:
                substitutes = config['substitutes']
                logger.info(f"✓ 使用外部提供的替代词，包含 {len(substitutes)} 个标识符")
                for identifier, candidates in list(substitutes.items())[:3]:
                    logger.debug(f"  - {identifier}: {len(candidates)} 个候选词")
            else:
                logger.warning("⚠ 未提供替代词，尝试生成替代词")
                # 尝试使用算法生成替代词
                try:
                    substitutes = self.generate_substitutes_with_algorithm(
                        code1, code2, language=language, model_id=model_id, model_name=target_model
                    )
                    if substitutes:
                        logger.info(f"✓ 使用算法生成替代词，包含 {len(substitutes)} 个标识符")
                    else:
                        logger.warning("⚠ 算法生成替代词失败")
                        substitutes = {}
                except Exception as e:
                    logger.warning(f"⚠ 生成替代词失败: {e}")
                    substitutes = {}

            if len(substitutes) == 0:
                logger.warning("⚠ 替代词为空")
                return {
                    'success': False,
                    'original_code': code1,
                    'adversarial_code': None,
                    'replaced_identifiers': None,
                    'query_times': 0,
                    'time_cost': round((time.time() - start_time) / 60, 2),
                    'error': '替代词为空'
                }

            # ========== 步骤4: 执行统一攻击 ==========
            logger.info(f"\n⚔️ 步骤4: 执行{method.upper()}攻击")

            # 使用统一攻击接口
            result = attacker.attack(
                code_data=code_data,
                true_label=true_label,
                substitutes=substitutes
            )

            # 更新时间成本
            result['time_cost'] = round((time.time() - start_time) / 60, 2)

            if result['success']:
                logger.info("🎉 攻击成功！生成了有效的对抗样本")
                logger.info(f"查询次数: {result['query_times']}")
                logger.info(f"耗时: {result['time_cost']:.2f} 分钟")

                if result['replaced_identifiers']:
                    logger.info(f"替换了 {len(result['replaced_identifiers'])} 个标识符:")
                    for old, new in list(result['replaced_identifiers'].items())[:3]:
                        logger.info(f"  - {old} → {new}")
            else:
                logger.warning("⚠ 攻击失败，未能生成有效的对抗样本")
                logger.warning(f"查询次数: {result['query_times']}")
                logger.warning(f"耗时: {result['time_cost']:.2f} 分钟")
                if result['error']:
                    logger.warning(f"错误信息: {result['error']}")

            return result

        except Exception as e:
            logger.error(f"\n✗ 攻击失败: {str(e)}", exc_info=True)

            # 返回错误结果
            return {
                'success': False,
                'original_code': code_data.get('code1', ''),
                'adversarial_code': None,
                'replaced_identifiers': None,
                'query_times': 0,
                'time_cost': round((time.time() - start_time) / 60, 2),
                'error': str(e)
            }
        finally:
            logger.info("\n" + "=" * 60)
            logger.info("✓ 攻击任务结束")
            logger.info("=" * 60)
    
# execute_script_attack 方法已移除，统一使用 attack() 方法
 
