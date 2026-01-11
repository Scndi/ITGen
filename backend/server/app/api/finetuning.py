from flask import Blueprint, request, jsonify
from app.services.finetuning_service import FinetuningService
from app.services.task_service import TaskService
from app.extensions import db
import uuid
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('finetuning', __name__)

finetuning_service = FinetuningService()
task_service = TaskService()

@bp.route('/finetuning/start', methods=['POST'])
def start_finetuning():
    """
    开始对抗性微调（异步处理）

    请求体格式:
    {
        "model_name": "codebert",
        "task_type": "clone-detection",
        "dataset": "finetuning-dataset",
        "attack_methods": ["itgen", "alert"],
        "sub_task_type": "attack_resistance",
        "parameters": {
            "learning_rate": 2e-5,
            "epochs": 3,
            "batch_size": 16,
            "max_queries": 100
        }
    }

    返回格式:
    {
        "success": true,
        "task_id": "uuid-string",
        "message": "微调任务已创建，正在后台执行"
    }
    """
    try:
        logger.info("🎯 收到微调请求")
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400

        # 从请求中获取参数
        model_name = data.get('model_name')
        task_type = data.get('task_type')
        dataset_name = data.get('dataset')
        attack_methods = data.get('attack_methods', ['itgen', 'alert'])
        sub_task_type = data.get('sub_task_type', 'attack_resistance')
        parameters = data.get('parameters', {
            'learning_rate': 2e-5,
            'epochs': 3,
            'batch_size': 16
        })

        # 验证必填参数
        if not model_name or not task_type or not dataset_name:
            return jsonify({
                'success': False,
                'error': '缺少必填参数: model_name, task_type, dataset'
            }), 400

        # 验证攻击方法
        from app.attacks import get_supported_attacks
        supported_methods = get_supported_attacks()
        invalid_methods = [m for m in attack_methods if m not in supported_methods]
        if invalid_methods:
            return jsonify({
                'success': False,
                'error': f'不支持的攻击方法: {invalid_methods}',
                'supported_methods': supported_methods
            }), 400

        logger.info(f"📋 微调请求参数:")
        logger.info(f"   模型: {model_name}")
        logger.info(f"   任务类型: {task_type}")
        logger.info(f"   数据集: {dataset_name}")
        logger.info(f"   攻击方法: {attack_methods}")
        logger.info(f"   子任务类型: {sub_task_type}")

        # 查找模型ID
        model_id = None
        try:
            from app.models.db_models import Model as DBModel
            db_model = DBModel.query.filter_by(model_name=model_name).first()
            if db_model:
                model_id = db_model.id
        except Exception as e:
            logger.warning(f"从数据库查找模型ID失败: {e}")

        # 准备任务参数
        task_parameters = {
            'task_type': task_type,
            'dataset_name': dataset_name,
            'attack_methods': attack_methods,
            'sub_task_type': sub_task_type,
            **parameters
        }

        # 创建任务（立即返回任务ID）
        task = task_service.create_task(
            task_type='finetune',
            sub_task_type=sub_task_type,
            model_id=model_id,
            model_name=model_name,
            dataset_name=dataset_name,
            parameters=task_parameters,
            priority=5  # 微调任务较低优先级
        )

        logger.info(f"✅ 微调任务创建成功: {task.id}")
        logger.info(f"   类型: {task.task_type}/{task.sub_task_type}")
        logger.info(f"   队列: {task.queue_name}")
        logger.info(f"   优先级: {task.priority}")

        # 任务将由调度器异步执行，这里直接返回任务ID
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '微调任务已创建，正在后台异步执行',
            'task_info': {
                'type': f'{task.task_type}/{task.sub_task_type}',
                'status': task.status,
                'queue': task.queue_name,
                'created_at': task.created_at.isoformat()
            }
        })

    except Exception as e:
        logger.error(f"❌ 创建微调任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'创建微调任务失败: {str(e)}'
        }), 500

@bp.route('/finetuning/status/<task_id>', methods=['GET'])
def get_finetuning_status(task_id):
    """获取微调状态"""
    try:
        task = task_service.get_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'status': task.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"获取状态失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/finetuning/results/<task_id>', methods=['GET'])
def get_finetuning_result(task_id):
    """获取微调结果"""
    try:
        task = task_service.get_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404
        
        # 构建结果数据
        result_data = task.to_dict()
        
        return jsonify({
            'success': True,
            'result': result_data
        }), 200
        
    except Exception as e:
        logger.error(f"获取微调结果失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

