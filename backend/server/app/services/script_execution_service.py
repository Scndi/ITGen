import os
import subprocess
import shlex
import logging
import torch
from pathlib import Path
from typing import Dict, Any, Optional
from app.models.db_models import Model as DBModel
from flask import has_app_context
from app.extensions import db

logger = logging.getLogger(__name__)


class ScriptExecutionService:
    """脚本执行服务 - 用于调用后台攻击脚本"""
    
    # 模型配置映射
    MODEL_CONFIGS = {
        'codebert': {
            'model_type': 'roberta',
            'model_name': 'codebert',
            'model_path': 'microsoft/codebert-base',
            'base_model': 'microsoft/codebert-base-mlm',
            'tokenizer_path': 'microsoft/codebert-base'
        },
        'codegpt': {
            'model_type': 'gpt2',
            'model_name': 'microsoft/CodeGPT-small-java-adaptedGPT2',
            'base_model': 'microsoft/codebert-base-mlm'
        },
        'codet5': {
            'model_type': 'codet5',
            'model_name': 'Salesforce/codet5-base-multi-sum',
            'base_model': 'microsoft/codebert-base-mlm'
        },
        'graphcodebert': {
            'model_type': 'roberta',
            'model_name': 'microsoft/graphcodebert-base',
            'base_model': 'microsoft/codebert-base-mlm'
        }
    }
    
    # 攻击方法映射
    ATTACK_METHODS = {
        'itgen': {
            'script': 'attack_itgen.py',
            'params': []
        },
        'beam': {
            'script': 'attack_beam.py',
            'params': ['beam_size']
        },
        'alert': {
            'script': 'attack_alert.py',
            'params': []
        },
        'mhm': {
            'script': 'attack_mhm.py',
            'params': []
        },
        'wir': {
            'script': 'attack_wir.py',
            'params': []
        },
        'rnns': {
            'script': 'attack_rnns.py',
            'params': []
        },
        'bayes': {
            'script': 'attack_bayes.py',
            'params': []
        },
        'style': {
            'script': 'attack_style.py',
            'params': []
        }
    }
    
    # 任务类型直接使用（目录结构已统一为小写）
    # 不再需要映射，直接使用 task_type 作为目录名
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent
    
    def _get_model_config_from_db(self, model_name: str = None, model_id: int = None) -> Optional[Dict[str, Any]]:
        """
        从数据库获取模型配置
        
        Args:
            model_name: 模型名称（可选）
            model_id: 模型ID（可选，优先级高于model_name）
            
        Returns:
            模型配置字典，如果不存在则返回None
        """
        try:
            db_model = None
            if model_id:
                db_model = DBModel.query.filter_by(id=model_id, status='available').first()
            elif model_name:
                db_model = DBModel.query.filter_by(model_name=model_name, status='available').first()
            
            if db_model:
                # 使用数据库中的mlm_model_path，如果没有则使用默认值
                mlm_model_path = db_model.mlm_model_path or 'microsoft/codebert-base-mlm'
                
                return {
                    'model_type': db_model.model_type,
                    'model_name': db_model.model_name,
                    'model_path': db_model.model_path,  # 数据库中的model_path（本地或HuggingFace）
                    'tokenizer_path': db_model.tokenizer_path,  # 数据库中的tokenizer_path
                    'mlm_model_path': mlm_model_path,  # MLM模型路径
                    'checkpoint_path': db_model.checkpoint_path,  # 微调权重路径（可选）
                    'model_source': db_model.model_source,  # 模型来源
                    'supported_tasks': db_model.supported_tasks if isinstance(db_model.supported_tasks, list) else []  # 支持的任务列表
                }
        except Exception as e:
            logger.warning(f"从数据库获取模型配置失败: {e}")
        return None
    
    def get_attack_script_path(self, model_name: str, task_type: str, attack_method: str, model_type: str = None) -> Path:
        """
        获取攻击脚本路径
        
        Args:
            model_name: 模型名称 (codebert, codegpt, codet5, graphcodebert 或自定义模型名称)
            task_type: 任务类型 (clone-detection, vulnerability-detection, etc.)
            attack_method: 攻击方法 (itgen, beam, alert, etc.)
            model_type: 模型类型 (roberta, gpt2, codet5, etc.)，如果提供则用于确定脚本目录
        
        Returns:
            脚本文件路径
        """
        # 获取任务目录（直接使用 task_type，因为目录结构已统一为小写）
        task_dir = task_type if task_type else 'clone-detection'
        
        # 确定模型目录（直接使用 model_type，因为目录结构已统一为小写）
        # 如果提供了 model_type，直接使用；否则尝试从 model_name 推断，最后默认使用 'roberta'
        if model_type:
            model_dir = model_type.lower()
            logger.info(f"使用模型类型作为目录: {model_dir}")
        else:
            # 尝试从 model_name 推断（兼容旧代码）
            model_name_lower = model_name.lower()
            if 'roberta' in model_name_lower or 'codebert' in model_name_lower or 'graphcodebert' in model_name_lower:
                model_dir = 'roberta'
            elif 'gpt' in model_name_lower or 'codegpt' in model_name_lower:
                model_dir = 'gpt2'  # 或 'gpt'，根据实际目录调整
            elif 'codet5' in model_name_lower or 't5' in model_name_lower:
                model_dir = 'codet5'
            else:
                model_dir = 'roberta'  # 默认使用 roberta（最常见）
                logger.warning(f"无法从模型名称 {model_name} 推断目录，使用默认目录: {model_dir}")
        
        script_path = self.base_dir / model_dir / task_dir / 'attack' / self.ATTACK_METHODS[attack_method]['script']
        
        return script_path
    
    def build_command(
        self,
        model_name: str,
        task_type: str,
        attack_method: str,
        config: Dict[str, Any]
    ) -> str:
        """
        构建命令行命令
        
        Args:
            model_name: 模型名称
            task_type: 任务类型
            attack_method: 攻击方法
            config: 配置参数字典（可能包含model_id）
        
        Returns:
            完整的命令行字符串
        """
        # 从config中获取model_id（如果提供）
        model_id = config.get('model_id')
        
        # 优先从数据库获取模型配置
        model_config = self._get_model_config_from_db(model_name=model_name, model_id=model_id)
        
        # 如果数据库中没有，使用默认配置
        if model_config is None:
            model_config = self.MODEL_CONFIGS.get(model_name.lower(), self.MODEL_CONFIGS['codebert'])
            # 确保默认配置有base_model字段
            if 'base_model' not in model_config:
                model_config['base_model'] = 'microsoft/codebert-base-mlm'
            logger.info(f"使用默认模型配置: {model_name}")
        else:
            logger.info(f"✓ 从数据库获取模型配置: {model_name} (ID: {model_id})")
            logger.info(f"  - model_path: {model_config.get('model_path')}")
            logger.info(f"  - tokenizer_path: {model_config.get('tokenizer_path')}")
            logger.info(f"  - mlm_model_path: {model_config.get('mlm_model_path')}")
            logger.info(f"  - checkpoint_path: {model_config.get('checkpoint_path', 'None')}")
            # 为了兼容，将mlm_model_path映射到base_model
            if 'base_model' not in model_config:
                model_config['base_model'] = model_config.get('mlm_model_path', 'microsoft/codebert-base-mlm')
        
        attack_config = self.ATTACK_METHODS.get(attack_method, self.ATTACK_METHODS['itgen'])
        
        # 获取脚本路径（传入 model_type 以支持自定义模型）
        script_path = self.get_attack_script_path(
            model_name=model_name, 
            task_type=task_type, 
            attack_method=attack_method,
            model_type=model_config.get('model_type')
        )
        
        # 获取 eval_data_file 路径
        # 如果 config 中已经是完整路径（从数据集服务获取），直接使用
        # 否则使用相对路径
        eval_data_file = config.get('eval_data_file')
        if not eval_data_file:
            raise ValueError("缺少必需参数: eval_data_file")
        
        # 判断是否为绝对路径或已包含完整路径
        eval_data_path = Path(eval_data_file)
        if eval_data_path.is_absolute() or '/' in eval_data_file:
            # 已经是完整路径，直接使用
            eval_data_file_arg = eval_data_file
        else:
            # 使用相对路径（兼容旧方式）
            eval_data_file_arg = f"../../../dataset/{task_type}/{eval_data_file}"
        
        # 构建结果文件名（从原始文件名提取，不包含路径）
        eval_data_filename = Path(eval_data_file).name if '/' in eval_data_file else eval_data_file
        result_filename = f"{model_name}_{task_type}_{attack_method}_{eval_data_filename}.jsonl"
        
        # 基本参数（Linux 兼容格式）
        # 使用列表格式，subprocess 会自动处理参数转义
        # 注意：参数使用 = 格式（--param=value），在列表中作为单个字符串元素
        cmd_parts = [
            "python3",  # Linux 系统通常使用 python3
            str(script_path),
            "--output_dir=../saved_models",
            f"--model_type={model_config['model_type']}",
            f"--tokenizer_name={model_config['tokenizer_path']}",
            f"--model_name_or_path={model_config['model_path']}",
            f"--base_model={model_config['base_model']}",
            f"--eval_data_file={eval_data_file_arg}",
            f"--block_size={config.get('block_size', 512)}",
            f"--eval_batch_size={config.get('eval_batch_size', 2)}",
            f"--seed={config.get('seed', 123456)}",
            f"--csv_store_path=../../../result/{result_filename}"
        ]
        
        # 记录使用的路径信息（用于调试）
        logger.info(f"📦 模型路径配置:")
        logger.info(f"  - model_type: {model_config['model_type']}")
        logger.info(f"  - model_path: {model_config['model_path']}")
        logger.info(f"  - tokenizer_path: {model_config['tokenizer_path']}")
        logger.info(f"  - base_model (MLM): {model_config['base_model']}")
        
        # 如果提供了替代词文件路径，添加参数
        if config.get('substitutes_file'):
            cmd_parts.append(f"--substitutes_file={config.get('substitutes_file')}")
            logger.info(f"✓ 使用替代词文件: {config.get('substitutes_file')}")
        
        # 如果数据库中有checkpoint_path，添加checkpoint参数
        if model_config.get('checkpoint_path'):
            cmd_parts.append(f"--checkpoint_path={model_config['checkpoint_path']}")
            logger.info(f"✓ 使用微调权重: {model_config['checkpoint_path']}")
        # 创建结果文件夹
        os.makedirs(f"../../../result/attack", exist_ok=True)
        # 添加方法特定参数（Linux 兼容格式：使用 = 格式保持一致性）
        for param in attack_config.get('params', []):
            if param in config:
                cmd_parts.append(f"--{param}={config[param]}")  # 使用 = 格式，与基本参数保持一致
        
        # 添加额外标志
        if 'use_ga' in config and config['use_ga']:
            cmd_parts.append('--use_ga')
        
        if 'original' in config and config['original']:
            cmd_parts.append('--original')
        
        # 如果是 CodeT5，添加 config_name
        if model_name == 'codet5':
            cmd_parts.insert(2, f"--config_name={model_config['model_name']}")  # 使用 = 格式
        
        # Linux 兼容：返回列表格式，subprocess 会自动处理
        # 如果必须返回字符串（用于日志等），则使用 shlex.quote 转义
        return cmd_parts
    
    def execute_attack_script(
        self,
        model_name: str,
        task_type: str,
        attack_method: str,
        config: Dict[str, Any],
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行攻击脚本
        
        Args:
            model_name: 模型名称
            task_type: 任务类型
            attack_method: 攻击方法
            config: 配置参数字典
            cwd: 工作目录（如果为None，使用脚本所在目录）
        
        Returns:
            执行结果字典
        """
        logger.info("=" * 60)
        logger.info(f"🎯 开始执行攻击脚本")
        logger.info(f"📦 模型: {model_name}, 任务: {task_type}, 方法: {attack_method}")
        logger.info("=" * 60)
        
        # 从config中获取model_id（如果提供），用于确定model_type
        model_id = config.get('model_id')
        model_config = self._get_model_config_from_db(model_name=model_name, model_id=model_id)
        model_type = model_config.get('model_type') if model_config else None
        
        # 获取脚本路径并设置工作目录（传入 model_type 以支持自定义模型）
        script_path = self.get_attack_script_path(
            model_name=model_name, 
            task_type=task_type, 
            attack_method=attack_method,
            model_type=model_type
        )
        
        if not script_path.exists():
            error_msg = f"攻击脚本不存在: {script_path}"
            logger.error(f"✗ {error_msg}")
            logger.error(f"  请检查模型名称 {model_name} 和模型类型 {model_type} 是否正确")
            return {
                'success': False,
                'error': error_msg
            }
        
        # 如果没有指定cwd，使用脚本所在目录
        if cwd is None:
            cwd = str(script_path.parent)
        
        # 构建命令
        command = self.build_command(model_name, task_type, attack_method, config)
        
        logger.info(f"📝 工作目录: {cwd}")
        # 将命令列表转换为字符串用于日志显示（Linux 兼容）
        if isinstance(command, list):
            cmd_str = " ".join(shlex.quote(str(arg)) for arg in command)
            logger.info(f"📝 执行命令: {cmd_str}...")
        else:
            logger.info(f"📝 执行命令: {command}...")
        
        try:
            # 准备环境变量（用于CUDA设备设置）
            env = os.environ.copy()
            
            # 确保config是字典类型
            if not isinstance(config, dict):
                config = {}
            
            # 根据配置自动检测GPU，找不到则使用CPU
            # 从配置中读取，默认启用GPU检测
            use_gpu = config.get('use_gpu', True)  # 默认启用GPU检测
            if use_gpu and torch.cuda.is_available():
                cuda_device = config.get('cuda_device', 0)
                if cuda_device is not None:
                    env['CUDA_VISIBLE_DEVICES'] = str(cuda_device)
                    logger.info(f"✓ 设置CUDA设备: {cuda_device}")
            else:
                # 使用 CPU
                env['CUDA_VISIBLE_DEVICES'] = ''
                logger.info("✓ 使用 CPU（GPU不可用或已禁用）")
            
            # 执行命令（Linux 兼容：支持列表和字符串格式）
            if isinstance(command, list):
                # 使用列表格式，shell=False（更安全，自动处理参数转义）
                result = subprocess.run(
                    command,
                    shell=False,
                    cwd=cwd,
                    env=env,  # 传递环境变量
                    capture_output=True,
                    text=True,
                    timeout=config.get('timeout', 3600)
                )
            else:
                # 字符串格式，使用 shell=True（向后兼容）
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=cwd,
                    env=env,  # 传递环境变量
                    capture_output=True,
                    text=True,
                    timeout=config.get('timeout', 3600)
                )
            
            # 检查返回码
            if result.returncode == 0:
                logger.info("✓ 脚本执行成功")
                # 打印部分输出用于调试
                if result.stdout:
                    logger.info(f"✓ 输出信息: {result.stdout[:500]}")
                return {
                    'success': True,
                    'state': 'completed',
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'config': config
                }
            else:
                error_msg = f"脚本执行失败，返回码: {result.returncode}"
                logger.error(f"✗ {error_msg}")
                
                # 打印完整的stdout和stderr用于调试
                if result.stdout:
                    logger.error(f"标准输出: {result.stdout[-2000:]}")
                if result.stderr:
                    logger.error(f"错误输出: {result.stderr[-2000:]}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
        
        except subprocess.TimeoutExpired:
            error_msg = f"脚本执行超时（超过{config.get('timeout', 3600)}秒）"
            logger.error(f"✗ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        
        except Exception as e:
            error_msg = f"执行脚本时出错: {str(e)}"
            logger.error(f"✗ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_supported_models(self) -> list:
        """获取支持的模型列表（优先从数据库获取）"""
        try:
            # 从数据库获取所有可用模型
            db_models = DBModel.query.filter_by(status='available').all()
            if db_models:
                models = [model.model_name for model in db_models]
                logger.info(f"从数据库获取模型列表: {len(models)} 个模型")
                return models
        except Exception as e:
            logger.warning(f"从数据库获取模型列表失败: {e}，使用默认配置")
        
        # 如果数据库中没有，返回默认配置的模型列表
        return list(self.MODEL_CONFIGS.keys())
    
    def get_supported_attacks(self) -> list:
        """获取支持的攻击方法列表"""
        return list(self.ATTACK_METHODS.keys())
    
    def get_supported_tasks(self) -> list:
        """获取支持的任务类型列表"""
        # 返回常见的任务类型列表（目录结构已统一为小写）
        return [
            'clone-detection',
            'vulnerability-detection',
            'vulnerability-prediction',
            'code-summarization',
            'authorship-attribution'
        ]
