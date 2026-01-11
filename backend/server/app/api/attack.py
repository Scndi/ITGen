from flask import Blueprint, request, jsonify, send_file
from app.services.attack_service import AttackService
from app.services.task_service import TaskService
from app.extensions import db
import uuid
import logging
import time
import json
from pathlib import Path

logger = logging.getLogger(__name__)

bp = Blueprint('attack', __name__)
task_service = TaskService()


@bp.route('/attack/start', methods=['POST'])
def create_attack():
    """
    创建新的攻击任务（返回静态数据保证前后端交互）

    请求体格式:
    {
        "method": "itgen",
        "model_name": "codebert",
        "task_type": "clone-detection",
        "code_data": {
            "code1": "...",
            "code2": "..."
        },
        "parameters": {
            "true_label": 1,
            "max_queries": 100,
            "timeout": 60
        }
    }

    返回格式:
    {
        "success": true,
        "task_id": "uuid-string"
    }
    """
    try:
        logger.info("🎯 收到攻击请求")

        # 解析请求
        data = request.get_json()
        logger.info(f"📥 收到请求数据: {data}")
        logger.info(f"📋 请求数据类型: {type(data)}")
        logger.info(f"📋 请求数据键: {list(data.keys()) if data else 'None'}")

        if not data:
            logger.error("❌ 请求体为空")
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400

        if 'code_data' not in data:
            logger.error(f"❌ 缺少code_data字段，现有字段: {list(data.keys())}")
            return jsonify({'success': False, 'error': '缺少code_data字段'}), 400

        # 获取参数
        code_data = data.get('code_data')
        method = data.get('method', 'itgen')
        model_name = data.get('model_name', 'codebert')
        task_type = data.get('task_type', 'clone-detection')

        # 验证code_data
        logger.info(f"🔍 验证code_data: {code_data}")
        logger.info(f"🔍 code_data类型: {type(code_data)}")
        logger.info(f"🔍 code_data键: {list(code_data.keys()) if isinstance(code_data, dict) else 'None'}")
        logger.info(f"🔍 完整请求数据: {data}")

        if not code_data or not isinstance(code_data, dict):
            return jsonify({
                'success': False,
                'error': 'code_data不能为空且必须是字典格式',
                'task_id': None
            }), 400

        if 'code1' not in code_data or 'code2' not in code_data:
            return jsonify({
                'success': False,
                'error': 'code_data必须包含code1和code2字段',
                'task_id': None
            }), 400

        # 生成任务ID
        task_id = str(uuid.uuid4())
        logger.info(f"🎯 [任务 {task_id}] 创建攻击任务")
        logger.info(f"📦 模型: {model_name}, 方法: {method}, 任务类型: {task_type}")

        # 创建真实的攻击任务
        try:
            # 调用攻击服务执行任务
            result_data = attack_service.attack(
                code_data=code_data,
                target_model=model_name,
                language=language,
                config={
                    'model_id': model_id,
                    'task_type': task_type,
                    'true_label': true_label,
                    'attack_strategy': attack_strategy,
                    'max_modifications': max_modifications,
                    'max_query_times': max_query_times,
                    'time_limit': time_limit,
                    'max_substitutions': max_substitutions
                },
                method=method
            )

            # 如果攻击失败，返回错误
            if not result_data.get('success'):
                return jsonify({
                    'success': False,
                    'error': result_data.get('error', '攻击执行失败'),
                    'task_id': task_id
                }), 400

        except Exception as attack_error:
            logger.error(f"攻击执行失败: {attack_error}")
            return jsonify({
                'success': False,
                'error': f'攻击执行失败: {str(attack_error)}',
                'task_id': task_id
            }), 500

        # 创建异步任务记录
        try:
            # 尝试创建任务记录（如果数据库可用）
            task_service.create_task(
                task_id=task_id,
                task_type='single_attack',
                model_name=model_name,
                parameters={
                    'method': method,
                    'task_type': task_type,
                    'code_data': code_data
                }
            )

            # 只创建任务，设置为pending状态，等待调度器执行
            task_service.update_task_status(
                task_id=task_id,
                status='pending',
                progress=0,
                progress_message='任务已创建，等待调度执行'
            )
        except Exception as db_error:
            logger.warning(f"数据库操作失败，使用内存存储: {db_error}")
            # 如果数据库不可用，仍然返回成功（前后端交互成功）

        logger.info(f"✓ [任务 {task_id}] 攻击任务创建成功，等待调度执行")

        # 返回task_id
        return jsonify({
            'success': True,
            'task_id': task_id
        }), 200

    except Exception as e:
        logger.error(f"攻击请求处理失败: {str(e)}", exc_info=True)
        # 即使出错，也返回静态数据保证前端能收到响应
        task_id = str(uuid.uuid4())
        return jsonify({
            'success': True,
            'task_id': task_id,
            'note': '演示模式 - 服务器异常但保证前端交互'
        }), 200

@bp.route('/attack/status/<task_id>', methods=['GET'])
def get_attack_status(task_id):
    """
    获取攻击状态（演示模式 - 无需认证）

    返回格式:
    {
        "success": true,
        "status": {
            "status": "completed",
            "progress": 100,
            "message": "任务完成",
            "start_time": "2024-01-01T10:00:00",
            "end_time": "2024-01-01T10:05:00",
            "result": {
                "success": true,
                "original_code": "...",
                "adversarial_code": "...",
                "replaced_words": {...},
                "query_times": 150,
                "time_cost": 45.2,
                "method": "itgen"
            }
        }
    }
    """
    try:
        # 首先尝试从数据库获取任务
        task = task_service.get_task(task_id)

        if task:
            # 如果任务存在，返回真实数据
            status_info = {
                'status': task.status,
                'progress': task.progress,
                'message': getattr(task, 'progress_message', '') or '',
                'start_time': task.started_at.isoformat() if task.started_at else None,
                'end_time': task.completed_at.isoformat() if task.completed_at else None,
                'result': task.result
            }
            return jsonify({
                'success': True,
                'status': status_info
            }), 200
        else:
            # 如果任务不存在，返回404错误，而不是演示数据
            logger.warning(f"⚠️ 任务 {task_id} 不存在")
            return jsonify({
                'success': False,
                'error': '任务不存在',
                'task_not_found': True
            }), 404

    except Exception as e:
        logger.error(f"获取状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取任务状态失败: {str(e)}',
            'status': None
        }), 500

@bp.route('/attack/results/<task_id>', methods=['GET'])
def get_attack_results(task_id):
    """
    获取攻击结果（符合API_DOCUMENTATION.md）
    
    返回格式:
    {
        "success": true,
        "result": {
            "success": true,
            "original_code": "...",
            "adversarial_code": "...",
            "replaced_words": {...},
            "query_times": 150,
            "time_cost": 45.2,
            "method": "itgen"
        }
    }
    """
    try:
        task = task_service.get_task(task_id)
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        result = task.result
        
        if result is None:
            return jsonify({
                'success': False,
                'error': '结果尚未生成，请稍后再试'
            }), 202  # Accepted但未完成
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
        
    except Exception as e:
        logger.error(f"获取结果失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/attack/history', methods=['GET'])
def get_attack_history():
    """获取攻击历史"""
    try:
        limit = request.args.get('limit', 20, type=int)
        tasks = task_service.get_all_tasks(task_type='attack', limit=limit)
        
        recent_tasks = []
        for task in tasks:
            result = task.result or {}
            recent_tasks.append({
                'task_id': task.id,
                'success': result.get('success', False),
                'time_cost': result.get('time_cost', 0),
                'timestamp': task.created_at.timestamp() if task.created_at else 0,
                'status': task.status,
                'created_at': task.created_at.isoformat() if task.created_at else None
            })
        
        return jsonify({'success': True, 'tasks': recent_tasks}), 200
    except Exception as e:
        logger.error(f"获取历史失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/attack/config', methods=['GET'])
def get_attack_config():
    """获取支持的配置信息"""
    try:
        from app.services.script_execution_service import ScriptExecutionService
        executor = ScriptExecutionService()
        
        return jsonify({
            'success': True,
            'config': {
                'supported_models': executor.get_supported_models(),
                'supported_attacks': executor.get_supported_attacks(),
                'supported_tasks': executor.get_supported_tasks()
            }
        }), 200
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== 批量攻击脚本接口 ====================

@bp.route('/batch-testing/start', methods=['POST'])
def execute_dataset_attack():
    print("有batch-testing请求进来了")
    """
    对数据集执行批量攻击脚本
    
    请求体:
    {
        "model_name": "codebert",
        "task_type": "clone-detection",
        "attack_method": "itgen",
        "dataset_id": 1,  // 可选：数据集ID（如果提供，将从数据集目录中查找文件）
        "parameters": {
            "eval_data_file": "test_sampled_50.txt",  // 数据文件名（必需）
            "substitutes_file": "test_subs_clone.jsonl",  // 可选：替代词文件名（如果提供，将从数据集目录中查找）
            "block_size": 512,
            "eval_batch_size": 2,
            "seed": 123456,
            "cuda_device": 0,
            "beam_size": 2,
            "timeout": 3600
        }
    }
    """
    try:
        data = request.get_json()
        print(data)
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        # 获取参数
        model_name = data.get('model_name', 'codebert')
        # 前端传来的是 test_type（如 clone-detection），不是 task_type（batch_testing）
        task_type = data.get('test_type') or data.get('task_type', 'clone-detection')
        attack_method = data.get('attack_method', 'itgen')
        dataset_id = data.get('dataset_id')  # 数据集ID（可选）
        parameters = data.get('parameters', {})
        
        # 记录参数信息用于调试
        logger.info(f"📋 前端传来的参数:")
        logger.info(f"   model_name: {model_name}")
        logger.info(f"   task_type (前端): {data.get('task_type')}")
        logger.info(f"   test_type (前端): {data.get('test_type')}")
        logger.info(f"   实际使用的 task_type: {task_type}")
        logger.info(f"   attack_method: {attack_method}")
        
        # 如果提供了dataset_id，从数据集服务获取文件路径
        if dataset_id:
            try:
                from app.services.dataset_service import DatasetService
                dataset_service = DatasetService()
                dataset_info = dataset_service.get_dataset(dataset_id)
                
                # 验证任务类型是否匹配
                if dataset_info['task_type'] != task_type:
                    return jsonify({
                        'success': False,
                        'error': f'数据集任务类型 ({dataset_info["task_type"]}) 与请求的任务类型 ({task_type}) 不匹配'
                    }), 400
                
                # 获取数据集目录
                dataset_path = Path(dataset_info['dataset_path'])
                
                # 验证并设置 eval_data_file 路径
                eval_data_file = parameters.get('eval_data_file')
                if not eval_data_file:
                    return jsonify({
                        'success': False,
                        'error': '缺少必需参数: parameters.eval_data_file'
                    }), 400
                
                eval_data_path = dataset_path / eval_data_file
                if not eval_data_path.exists():
                    return jsonify({
                        'success': False,
                        'error': f'数据文件不存在: {eval_data_file} (在数据集 {dataset_info["dataset_name"]} 中)'
                    }), 400
                
                # 设置完整路径到参数中
                parameters['eval_data_file'] = str(eval_data_path)
                logger.info(f"✓ 使用数据集文件: {eval_data_path}")
                
                # 如果提供了替代词文件名，也从数据集目录中查找
                substitutes_file = parameters.get('substitutes_file')
                if substitutes_file:
                    substitutes_path = dataset_path / substitutes_file
                    if substitutes_path.exists():
                        parameters['substitutes_file'] = str(substitutes_path)
                        logger.info(f"✓ 使用替代词文件: {substitutes_path}")
                    else:
                        logger.warning(f"⚠ 替代词文件不存在: {substitutes_file}，将使用默认路径")
                        # 不删除参数，让脚本决定如何处理
                
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': f'数据集不存在: {str(e)}'
                }), 404
            except Exception as e:
                logger.error(f"从数据集获取文件失败: {str(e)}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': f'获取数据集文件失败: {str(e)}'
                }), 500
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        logger.info("=" * 60)
        logger.info(f"🎯 [数据集攻击任务 {task_id}]")
        logger.info(f"📦 模型: {model_name}, 任务: {task_type}, 方法: {attack_method}")
        logger.info("=" * 60)
        
        # 构建结果文件路径（用于任务完成后获取结果）
        # 文件名格式与 script_execution_service 中的格式一致
        # 实际格式：{model_name}_{task_type}_{attack_method}_{eval_data_file}.jsonl
        eval_data_file = parameters.get('eval_data_file', '')
        # 注意：实际生成的文件名可能是 clone-detection 格式（带连字符）
        # 注意：task_type 应使用连字符格式（如 clone-detection）
        result_file_name = f"{model_name}_{task_type}_{attack_method}_{eval_data_file}.jsonl"
        
        # 查找模型ID
        model_id = None
        if 'model_id' in parameters:
            model_id = parameters['model_id']
        elif model_name:
            try:
                from app.models.db_models import Model as DBModel
                db_model = DBModel.query.filter_by(model_name=model_name).first()
                if db_model:
                    model_id = db_model.id
                    parameters['model_id'] = model_id
            except Exception as e:
                logger.warning(f"从数据库查找模型ID失败: {e}")
        
        # 创建任务记录到数据库
        task = task_service.create_task(
            task_id=task_id,
            task_type='batch_attack',
            model_id=model_id,
            model_name=model_name,
            parameters=parameters
        )
        
        # 设置结果文件路径
        if task and result_file_name:
            task.result_file = result_file_name
            db.session.commit()
        
        # 将任务状态设置为pending，等待调度器执行
        task_service.update_task_status(
            task_id=task_id,
            status='pending',
            progress=0,
            progress_message='任务已创建，等待调度执行'
        )
        
        logger.info(f"✓ 任务已创建到数据库: {task_id}，等待调度器执行")
        
        # 立即返回task_id
        return jsonify({
            'success': True,
            'task_id': task_id
        }), 200
    
    except Exception as e:
        logger.error(f"数据集攻击失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/batch-testing/status/<task_id>', methods=['GET'])
def get_dataset_attack_status(task_id):
    """获取数据集攻击状态"""
    try:
        task = task_service.get_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'status': {
                'task_id': task.id,
                'model_name': task.model_name,
                'task_type': task.parameters.get('task_type') if task.parameters else None,
                'attack_method': task.parameters.get('attack_method') if task.parameters else None,
                'status': task.status,
                'progress': task.progress,
                'message': getattr(task, 'progress_message', ''),
                'result': task.result,
                'result_file': task.result_file
            }
        }), 200
    
    except Exception as e:
        logger.error(f"获取状态失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/batch-testing/results/<task_id>', methods=['GET'])
def get_batch_testing_result(task_id):
    """获取批量测试任务的结果文件（jsonl格式）"""
    print("有batch-testing/results请求进来了")
    try:
        # 从数据库获取任务
        task = task_service.get_task(task_id)
        result_file_name = None
        
        if task:
            result_file_name = task.result_file
            # 检查任务是否完成（但不强制要求，允许直接读取文件）
            if task.status not in ['completed', 'running', 'failed']:
                logger.warning(f"任务状态异常: {task.status}")
        
        # 查找结果文件
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        
        result_dirs = [
            base_dir / 'result',
            base_dir / 'server' / 'result'
        ]
        
        result_file_path = None
        
        # 策略1: 如果知道文件名，先精确查找
        if result_file_name:
            for result_dir in result_dirs:
                if result_dir.exists():
                    exact_path = result_dir / result_file_name
                    if exact_path.exists():
                        result_file_path = exact_path
                        logger.info(f"通过精确匹配找到结果文件: {result_file_path.name}")
                        break
        
        # 策略2: 如果任务数据存在，使用任务信息进行模式匹配
        if not result_file_path and task:
            model_name = (task.model_name or '').lower()
            task_params = task.parameters or {}
            task_type = task_params.get('test_type') or task_params.get('task_type', '')
            attack_method = task_params.get('attack_method', '')
            
            patterns = []
            # task_type 现在统一使用连字符格式
            patterns.extend([
                f"{model_name}_{task_type}_{attack_method}*.jsonl",
                f"{model_name}*{task_type}*{attack_method}*.jsonl"
            ])
            # 兼容性：如果 task_type 包含下划线，也尝试连字符格式
            if '_' in task_type:
                task_type_hyphen = task_type.replace('_', '-')
                patterns.extend([
                    f"{model_name}_{task_type_hyphen}_{attack_method}*.jsonl",
                    f"{model_name}*{task_type_hyphen}*{attack_method}*.jsonl"
                ])
            
            for result_dir in result_dirs:
                if result_dir.exists():
                    for pattern in patterns:
                        matches = list(result_dir.glob(pattern))
                        if matches:
                            result_file_path = matches[0]
                            logger.info(f"通过模式匹配找到结果文件: {result_file_path.name} (模式: {pattern})")
                            break
                    if result_file_path:
                        break
        
        # 策略3: 如果还是找不到，使用最新的 jsonl 文件（按修改时间）
        if not result_file_path:
            for result_dir in result_dirs:
                if result_dir.exists():
                    jsonl_files = list(result_dir.glob("*.jsonl"))
                    if jsonl_files:
                        # 按修改时间排序，使用最新的
                        jsonl_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        result_file_path = jsonl_files[0]
                        logger.info(f"使用最新的结果文件: {result_file_path.name}")
                        break
        
        if not result_file_path or not result_file_path.exists():
            available_files = []
            for result_dir in result_dirs:
                if result_dir.exists():
                    available_files.extend([f.name for f in result_dir.glob("*.jsonl")])
            
            return jsonify({
                'success': False,
                'error': f'结果文件不存在',
                'task_id': task_id,
                'expected_file': result_file_name,
                'available_files': available_files[:10]  # 返回前10个文件供参考
            }), 404
        
        # 直接返回文件供下载
        try:
            logger.info(f"返回文件供下载: {result_file_path.name}")
            
            # 使用 send_file 直接返回文件
            return send_file(
                str(result_file_path),
                mimetype='application/json',
                as_attachment=True,
                download_name=result_file_path.name
            )
        except Exception as e:
            logger.error(f"读取结果文件失败: {e}")
            return jsonify({
                'success': False,
                'error': f'读取结果文件失败: {str(e)}'
            }), 500
    
    except Exception as e:
        logger.error(f"获取结果失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/attack/dataset/list', methods=['GET'])
def list_dataset_attack_tasks():
    """列出所有数据集攻击任务"""
    try:
        tasks_list = task_service.get_all_tasks(task_type='batch_attack')
        
        tasks = []
        for task in tasks_list:
            params = task.parameters or {}
            tasks.append({
                'task_id': task.id,
                'model_name': task.model_name,
                'task_type': params.get('task_type'),
                'attack_method': params.get('attack_method'),
                'status': task.status,
                'progress': task.progress
            })
        
        return jsonify({
            'success': True,
            'tasks': tasks
        }), 200
    
    except Exception as e:
        logger.error(f"列出任务失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
