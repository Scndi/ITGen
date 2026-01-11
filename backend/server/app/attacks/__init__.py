"""
攻击算法模块
统一管理所有攻击算法的接口
"""

from typing import Dict, Type
import importlib

# 攻击方法注册表
ATTACK_REGISTRY = {
    # 已完整实现的攻击方法
    'itgen': 'app.attacks.itgen.attacker.ITGenAttacker',
    'alert': 'app.attacks.alert.attacker.ALERTAttacker',
    'beam': 'app.attacks.beam.attacker.BeamAttacker',

    # 框架已创建，算法待完善的攻击方法
    'mhm': 'app.attacks.mhm.attacker.MHMAttacker',
    'wir': 'app.attacks.wir.attacker.WIRAttacker',
    'rnns': 'app.attacks.rnns.attacker.RNNSAttacker',

    # 其他攻击方法（style等）待开发
}


def get_attacker_class(method: str):
    """
    获取攻击器类
    
    Args:
        method: 攻击方法名称
        
    Returns:
        攻击器类
    """
    if method not in ATTACK_REGISTRY:
        raise ValueError(f"不支持的攻击方法: {method}。支持的方法: {list(ATTACK_REGISTRY.keys())}")
    
    module_path, class_name = ATTACK_REGISTRY[method].rsplit('.', 1)
    module = importlib.import_module(module_path)
    attacker_class = getattr(module, class_name)
    
    return attacker_class


def get_supported_attacks() -> list:
    """获取支持的攻击方法列表"""
    return list(ATTACK_REGISTRY.keys())


def get_attack_descriptions() -> Dict[str, Dict]:
    """获取攻击方法的详细信息"""
    return {
        'itgen': {
            'name': 'ITGen',
            'description': '基于生成对抗网络的代码变异攻击方法，通过学习代码模式生成对抗性示例',
            'category': 'generative',
            'parameters': {
                'max_queries': '最大查询次数',
                'timeout': '超时时间(秒)',
                'true_label': '真实标签(0或1)',
                'substitutes': '自定义替代词典'
            }
        },
        'alert': {
            'name': 'ALERT',
            'description': '基于抽象语法树的代码重构攻击，通过语义等价变换生成对抗样本',
            'category': 'transformation',
            'parameters': {
                'max_queries': '最大查询次数',
                'timeout': '超时时间(秒)',
                'true_label': '真实标签(0或1)'
            }
        },
        'beam': {
            'name': 'Beam Search',
            'description': '基于束搜索的贪婪攻击方法，通过局部最优搜索找到最佳的代码变异',
            'category': 'search',
            'parameters': {
                'max_queries': '最大查询次数',
                'timeout': '超时时间(秒)',
                'true_label': '真实标签(0或1)',
                'beam_width': '束宽度'
            }
        },
        'mhm': {
            'name': 'MHM',
            'description': '基于马尔可夫链蒙特卡洛的攻击方法，使用概率模型进行代码变异',
            'category': 'probabilistic',
            'parameters': {
                'max_queries': '最大查询次数',
                'timeout': '超时时间(秒)',
                'true_label': '真实标签(0或1)',
                'chain_length': '马尔可夫链长度'
            }
        },
        'wir': {
            'name': 'WIR',
            'description': '基于信息检索的攻击方法，通过代码相似度搜索生成对抗样本',
            'category': 'retrieval',
            'parameters': {
                'max_queries': '最大查询次数',
                'timeout': '超时时间(秒)',
                'true_label': '真实标签(0或1)',
                'similarity_threshold': '相似度阈值'
            }
        },
        'rnns': {
            'name': 'RNNS',
            'description': '基于循环神经网络的序列到序列攻击方法',
            'category': 'neural',
            'parameters': {
                'max_queries': '最大查询次数',
                'timeout': '超时时间(秒)',
                'true_label': '真实标签(0或1)',
                'model_path': 'RNN模型路径'
            }
        }
    }


__all__ = [
    'ATTACK_REGISTRY',
    'get_attacker_class',
    'get_supported_attacks',
    'get_attack_descriptions',
]

