"""攻击API接口 - 重新设计的任务管理系统"""
from flask import Blueprint, request, jsonify
from app.services.attack_service import AttackService
from app.services.task_service import TaskService
import uuid
import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

bp = Blueprint('new_attack', __name__)
attack_service = AttackService()
task_service = TaskService()


@bp.route('/attack/start', methods=['POST'])
def create_attack():
    """
    创建新的攻击任务（立即返回任务ID，异步执行）

    请求体格式:
    {
        "method": "itgen",              # 攻击方法（itgen, beam, alert, mhm, wir, rnns, bayes, style）
        "model_name": "codebert",       # 模型名称（可选，与model_id二选一）
        "model_id": 1,                  # 模型ID（可选，与model_name二选一）
        "code_data": {
            "code1": "...",             # 第一个代码片段
            "code2": "..."              # 第二个代码片段（克隆检测需要）
        },
        "parameters": {
            "true_label": 1,            # 真实标签（0或1）
            "substitutes": {...},       # 替代词字典（可选，会自动生成）
            "max_queries": 100,         # 最大查询次数（可选）
            "timeout": 60,              # 超时时间（秒，可选）
            "seed": 123456              # 随机种子（可选）
        }
    }

    返回格式:
    {
        "success": true,
        "task_id": "uuid-string",
        "message": "攻击任务已创建，正在后台异步执行",
        "task_info": {
            "type": "single_attack/itgen",
            "status": "pending",
            "queue": "attack",
            "created_at": "2024-01-01T00:00:00"
        }
    }
    """
    try:
        # 用户认证检查
        from flask import request
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': '需要有效的认证token'
            }), 401

        import jwt
        from flask import current_app
        from app.models.db_users import User
        token = auth_header[7:]  # 移除 'Bearer ' 前缀

        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = payload['user_id']
            current_user = User.query.get(current_user_id)

            if not current_user or not current_user.is_active():
                return jsonify({
                    'success': False,
                    'error': '用户不存在或已被禁用'
                }), 401

        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': 'token已过期'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'error': '无效的token'
            }), 401

        logger.info("🎯 收到攻击请求")
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400

        # 验证必需字段
        if 'code_data' not in data:
            return jsonify({'success': False, 'error': '缺少code_data字段'}), 400

        code_data = data.get('code_data')
        if 'code1' not in code_data or not code_data.get('code1', '').strip():
            return jsonify({'success': False, 'error': 'code1不能为空'}), 400

        # 解析参数
        method = data.get('method', 'itgen')
        model_name = data.get('model_name', 'codebert').lower()
        model_id = data.get('model_id')
        parameters = data.get('parameters', {})

        # 验证攻击方法
        from app.attacks import get_supported_attacks
        supported_methods = get_supported_attacks()
        if method not in supported_methods:
            return jsonify({
                'success': False,
                'error': f'不支持的攻击方法: {method}',
                'supported_methods': supported_methods
            }), 400

        logger.info(f"📋 攻击请求参数:")
        logger.info(f"   方法: {method}")
        logger.info(f"   模型: {model_name} (ID: {model_id})")
        logger.info(f"   代码长度: {len(code_data.get('code1', ''))}")

        # 准备任务参数
        task_parameters = {
            'method': method,
            'model_name': model_name,
            'true_label': parameters.get('true_label', 1),
            'max_queries': parameters.get('max_queries', 500),
            'timeout': parameters.get('timeout', 3600),
            'seed': parameters.get('seed', 123456),
            'language': 'java'  # 当前只支持Java
        }

        # 处理替代词
        substitutes = parameters.get('substitutes')
        if substitutes:
            task_parameters['substitutes'] = substitutes
            logger.info(f"   外部替代词: {len(substitutes)} 个标识符")
        else:
            task_parameters['generate_substitutes'] = True
            logger.info("   将自动生成替代词")

        # 创建任务（立即返回任务ID）
        task = task_service.create_task(
            task_type='single_attack',
            sub_task_type=method,
            model_id=model_id,
            model_name=model_name,
            parameters=task_parameters,
            input_data=code_data,
            priority=8,  # 攻击任务较高优先级
            user_id=current_user.id  # 设置任务创建者
        )

        logger.info(f"✅ 任务创建成功: {task.id}")
        logger.info(f"   类型: {task.task_type}/{task.sub_task_type}")
        logger.info(f"   队列: {task.queue_name}")
        logger.info(f"   优先级: {task.priority}")

        # 异步执行攻击任务
        def execute_attack_async():
            try:
                logger.info(f"🔄 开始异步执行攻击任务: {task.id}")

                # 标记任务开始运行
                task_service.mark_task_running(task.id, worker_id='api-server')

                # 设置超时控制
                import signal

                def timeout_handler(signum, frame):
                    raise TimeoutError("攻击任务执行超时")

                # 设置信号处理器
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(parameters.get('timeout', 3600))  # 默认1小时超时

                try:
                    # 执行攻击
                    result = attack_service.attack(
                        code_data=code_data,
                        target_model=model_name,
                        language='java',
                        config={
                            'model_id': model_id,
                            'model_name': model_name,
                            'method': method,
                            'true_label': parameters.get('true_label', 1),
                            'max_queries': parameters.get('max_queries', 500),
                            'timeout': parameters.get('timeout', 3600),
                            'seed': parameters.get('seed', 123456),
                            'substitutes': substitutes
                        },
                        method=method
                    )

                    # 取消超时
                    signal.alarm(0)

                except TimeoutError:
                    logger.warning(f"⏰ 攻击任务超时: {task.id}")
                    result = {
                        'success': False,
                        'error': '任务执行超时',
                        'original_code': code_data.get('code1', ''),
                        'adversarial_code': None,
                        'replaced_identifiers': None,
                        'query_times': 0,
                        'time_cost': parameters.get('timeout', 3600) * 60  # 转换为秒
                    }

                # 更新任务结果
                if result.get('success'):
                    task_service.mark_task_completed(
                        task.id,
                        result=result,
                        metrics={
                            'query_times': result.get('query_times', 0),
                            'execution_time': result.get('time_cost', 0)
                        }
                    )
                    logger.info(f"✅ 攻击任务完成: {task.id}")
                else:
                    task_service.mark_task_failed(
                        task.id,
                        error_message=result.get('error', '攻击失败'),
                        error_code='ATTACK_FAILED'
                    )
                    logger.warning(f"⚠️ 攻击任务失败: {task.id}")

            except Exception as e:
                logger.error(f"❌ 异步攻击执行异常: {task.id} - {str(e)}")
                task_service.mark_task_failed(
                    task.id,
                    error_message=str(e),
                    error_code='EXECUTION_ERROR'
                )

        # 启动异步任务
        import threading
        thread = threading.Thread(target=execute_attack_async, daemon=True)
        thread.start()

        # 立即返回任务ID
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '攻击任务已创建，正在后台异步执行',
            'task_info': {
                'type': f'{task.task_type}/{task.sub_task_type}',
                'status': task.status,
                'queue': task.queue_name,
                'created_at': task.created_at.isoformat()
            }
        })

    except Exception as e:
        logger.error(f"❌ 创建攻击任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'创建攻击任务失败: {str(e)}'
        }), 500


@bp.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id: str):
    """
    获取任务状态和结果（需要用户权限检查）

    返回格式:
    {
        "success": true,
        "task": {
            "id": "uuid",
            "task_type": "single_attack",
            "sub_task_type": "itgen",
            "status": "completed",
            "progress": 100,
            "progress_message": "任务完成",
            "result": {...},
            "metrics": {...},
            "created_at": "2024-01-01T00:00:00",
            "started_at": "2024-01-01T00:00:01",
            "completed_at": "2024-01-01T00:01:23"
        }
    }
    """
    try:
        # 权限检查：需要有效的用户token
        from flask import request
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': '需要有效的认证token'
            }), 401

        from app.controllers.auth_controller import token_required, User
        # 这里我们需要一个简化的权限检查
        # 由于这个函数不在Blueprint中，我们直接使用JWT解码

        import jwt
        from flask import current_app
        token = auth_header[7:]  # 移除 'Bearer ' 前缀

        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = payload['user_id']
            current_user = User.query.get(current_user_id)

            if not current_user or not current_user.is_active():
                return jsonify({
                    'success': False,
                    'error': '用户不存在或已被禁用'
                }), 401

        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': 'token已过期'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'error': '无效的token'
            }), 401

        task = task_service.get_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404

        # 权限检查：用户只能查看自己的任务，管理员可以查看所有任务
        if not current_user.is_admin() and task.user_id != current_user.id:
            return jsonify({
                'success': False,
                'error': '无权查看此任务'
            }), 403

        return jsonify({
            'success': True,
            'task': task.to_dict()
        })

    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取任务状态失败: {str(e)}'
        }), 500


@bp.route('/tasks', methods=['GET'])
def list_tasks():
    """
    获取任务列表

    查询参数:
    - task_type: 任务类型筛选
    - status: 状态筛选
    - limit: 返回数量限制（默认20）
    - offset: 偏移量（默认0）

    返回格式:
    {
        "success": true,
        "tasks": [...],
        "total": 100,
        "pagination": {
            "limit": 20,
            "offset": 0,
            "has_more": true
        }
    }
    """
    try:
        # 解析查询参数
        task_type = request.args.get('task_type')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))

        # 获取任务列表
        tasks = task_service.get_all_tasks(
            task_type=task_type,
            status=status,
            limit=limit,
            offset=offset
        )

        # 转换为字典格式
        task_dicts = [task.to_dict() for task in tasks]

        return jsonify({
            'success': True,
            'tasks': task_dicts,
            'total': len(task_dicts),
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': len(task_dicts) == limit
            }
        })

    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取任务列表失败: {str(e)}'
        }), 500


@bp.route('/tasks/stats', methods=['GET'])
def get_task_stats():
    """
    获取任务统计信息

    查询参数:
    - days: 统计最近N天的任务（默认7天）

    返回格式:
    {
        "success": true,
        "stats": {
            "total": 100,
            "by_type": {"attack": 50, "finetune": 30, ...},
            "by_status": {"completed": 80, "running": 10, ...},
            "performance": {
                "avg_execution_time": 45.2,
                "total_execution_time": 4520
            }
        }
    }
    """
    try:
        days = int(request.args.get('days', 7))

        stats = task_service.get_task_statistics(days=days)

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"获取任务统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取任务统计失败: {str(e)}'
        }), 500


@bp.route('/task/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id: str):
    """
    取消任务（用户只能取消自己的任务，管理员可以取消所有任务）

    返回格式:
    {
        "success": true,
        "message": "任务已取消"
    }
    """
    try:
        # 权限检查：需要有效的用户token
        from flask import request
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': '需要有效的认证token'
            }), 401

        import jwt
        from flask import current_app
        from app.models.db_users import User
        token = auth_header[7:]  # 移除 'Bearer ' 前缀

        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = payload['user_id']
            current_user = User.query.get(current_user_id)

            if not current_user or not current_user.is_active():
                return jsonify({
                    'success': False,
                    'error': '用户不存在或已被禁用'
                }), 401

        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': 'token已过期'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'error': '无效的token'
            }), 401

        # 获取任务并检查权限
        task = task_service.get_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404

        # 权限检查：用户只能取消自己的任务，管理员可以取消所有任务
        if not current_user.is_admin() and task.user_id != current_user.id:
            return jsonify({
                'success': False,
                'error': '无权取消此任务'
            }), 403

        success = task_service.cancel_task(task_id, reason="用户主动取消")

        if success:
            return jsonify({
                'success': True,
                'message': '任务已取消'
            })
        else:
            return jsonify({
                'success': False,
                'error': '任务不存在或无法取消'
            }), 404

    except Exception as e:
        logger.error(f"取消任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'取消任务失败: {str(e)}'
        }), 500


@bp.route('/queues/status', methods=['GET'])
def get_queue_status():
    """
    获取队列状态

    返回格式:
    {
        "success": true,
        "queues": {
            "attack": {
                "active_tasks": 2,
                "pending_tasks": 5,
                "total_tasks": 7
            },
            ...
        }
    }
    """
    try:
        queue_status = task_service.get_queue_status()

        return jsonify({
            'success': True,
            'queues': queue_status
        })

    except Exception as e:
        logger.error(f"获取队列状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取队列状态失败: {str(e)}'
        }), 500


@bp.route('/attack/methods', methods=['GET'])
def get_supported_methods():
    """
    获取支持的攻击方法

    返回格式:
    {
        "success": true,
        "methods": ["itgen", "beam", "alert", "mhm", "wir", "rnns", "bayes", "style"]
    }
    """
    try:
        from app.attacks import get_supported_attacks
        methods = get_supported_attacks()

        return jsonify({
            'success': True,
            'methods': methods
        })

    except Exception as e:
        logger.error(f"获取支持的攻击方法失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取支持的攻击方法失败: {str(e)}'
        }), 500
