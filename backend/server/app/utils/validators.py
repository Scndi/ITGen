"""数据验证工具"""
from typing import Any, Dict

def validate_attack_request(data: Dict[str, Any]) -> bool:
    """
    验证攻击请求数据
    
    Args:
        data: 请求数据字典
        
    Returns:
        bool: 验证是否通过
    """
    required_fields = ['code', 'language']
    
    # 检查必需字段
    for field in required_fields:
        if field not in data:
            raise ValueError(f'缺少必需字段: {field}')
    
    # 检查代码长度
    code = data.get('code', '')
    if len(code) == 0 or len(code) > 50000:
        raise ValueError('代码长度必须在1-50000字符之间')
    
    # 检查语言
    valid_languages = ['java', 'python', 'c', 'cpp']
    language = data.get('language', '')
    if language not in valid_languages:
        raise ValueError(f'不支持的语言: {language}. 支持的语言: {", ".join(valid_languages)}')
    
    return True

