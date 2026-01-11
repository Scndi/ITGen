"""
共享的攻击工具函数
整合所有攻击方法共用的工具类和函数
"""

from typing import List, Tuple
import logging
import torch

logger = logging.getLogger(__name__)


class InputFeatures(object):
    """统一的输入特征类 - 用于所有攻击方法"""

    def __init__(self,
                 input_tokens: List[str],
                 input_ids: List[int],
                 label: int,
                 url1: str = None,
                 url2: str = None):
        self.input_tokens = input_tokens
        self.input_ids = input_ids
        self.label = label
        self.url1 = url1
        self.url2 = url2


def convert_examples_to_features(code1_tokens: List[str],
                                code2_tokens: List[str],
                                label: int,
                                url1: str = None,
                                url2: str = None,
                                tokenizer=None,
                                args=None,
                                cache=None) -> InputFeatures:
    """
    统一的代码特征转换函数

    将成对代码的token序列转换为模型输入特征
    支持所有任务类型：clone-detection, code-summarization, vulnerability-prediction

    Args:
        code1_tokens: 第一段代码的tokens
        code2_tokens: 第二段代码的tokens（对于单代码任务可以为空）
        label: 标签
        url1: 可选的URL1
        url2: 可选的URL2
        tokenizer: tokenizer对象
        args: 参数对象（需要包含block_size等）
        cache: 可选的缓存

    Returns:
        InputFeatures对象
    """
    if tokenizer is None or args is None:
        raise ValueError("tokenizer和args参数是必需的")

    # 处理第一段代码
    code1_tokens = code1_tokens[:args.block_size - 2]
    code1_tokens = [tokenizer.cls_token] + code1_tokens + [tokenizer.sep_token]

    code1_ids = tokenizer.convert_tokens_to_ids(code1_tokens)
    padding_length = args.block_size - len(code1_ids)
    code1_ids += [tokenizer.pad_token_id] * padding_length

    # 如果有第二段代码，也进行处理
    if code2_tokens:
        code2_tokens = code2_tokens[:args.block_size - 2]
        code2_tokens = [tokenizer.cls_token] + code2_tokens + [tokenizer.sep_token]

        code2_ids = tokenizer.convert_tokens_to_ids(code2_tokens)
        padding_length = args.block_size - len(code2_ids)
        code2_ids += [tokenizer.pad_token_id] * padding_length

        # 拼接两个序列
        source_tokens = code1_tokens + code2_tokens
        source_ids = code1_ids + code2_ids
    else:
        # 单代码任务
        source_tokens = code1_tokens
        source_ids = code1_ids

    return InputFeatures(source_tokens, source_ids, label, url1, url2)


def create_args_from_config(config: dict) -> object:
    """
    从配置字典创建args对象

    Args:
        config: 配置字典

    Returns:
        args对象
    """
    class Args:
        def __init__(self, config):
            self.block_size = config.get('block_size', 512)
            self.eval_batch_size = config.get('eval_batch_size', 2)
            self.device = config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
            self.language = config.get('language', 'java')

    return Args(config)


# 为了兼容性，提供别名
def convert_examples_to_features_roberta(code1_tokens, code2_tokens, label, url1, url2, tokenizer, args, cache):
    """RoBERTa风格的特征转换（别名）"""
    return convert_examples_to_features(code1_tokens, code2_tokens, label, url1, url2, tokenizer, args, cache)


def convert_examples_to_features_gpt2(code1_tokens, code2_tokens, label, url1, url2, tokenizer, args, cache):
    """GPT-2风格的特征转换（别名）"""
    return convert_examples_to_features(code1_tokens, code2_tokens, label, url1, url2, tokenizer, args, cache)


def convert_examples_to_features_codet5(code1_tokens, code2_tokens, label, url1, url2, tokenizer, args, cache):
    """CodeT5风格的特征转换（别名）"""
    return convert_examples_to_features(code1_tokens, code2_tokens, label, url1, url2, tokenizer, args, cache)
