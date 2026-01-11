from flask import Blueprint, request, jsonify
from app.services.evaluation_service import EvaluationService
from app.services.task_service import TaskService
import uuid
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('evaluation', __name__)

evaluation_service = EvaluationService()
task_service = TaskService()

@bp.route('/evaluation/start', methods=['POST'])
def start_evaluation():
    """
    开始鲁棒性评估（异步处理）

    请求体格式:
    {
        "model_name": "codebert",
        "task_type": "clone-detection",
        "attack_methods": ["itgen", "beam"],
        "evaluation_metrics": ["asr", "ami", "art"],
        "dataset_name": "test-dataset"
    }

    返回格式:
    {
        "success": true,
        "task_id": "uuid-string",
        "message": "评估任务已创建，正在后台执行"
    }
    """
    try:
        logger.info("📊 收到评估请求")
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400

        # 解析参数
        model_name = data.get('model_name')
        task_type = data.get('task_type', 'clone-detection')
        attack_methods = data.get('attack_methods', ['itgen'])
        evaluation_metrics = data.get('evaluation_metrics', ['asr', 'ami', 'art'])
        dataset_name = data.get('dataset_name')

        # 验证必填参数
        if not model_name:
            return jsonify({'success': False, 'error': 'model_name不能为空'}), 400

        # 查找模型ID
        model_id = None
        try:
            from app.models.db_models import Model as DBModel
            db_model = DBModel.query.filter_by(model_name=model_name).first()
            if db_model:
                model_id = db_model.id
        except Exception as e:
            logger.warning(f"从数据库查找模型ID失败: {e}")

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

        logger.info(f"📋 评估请求参数:")
        logger.info(f"   模型: {model_name} (ID: {model_id})")
        logger.info(f"   任务类型: {task_type}")
        logger.info(f"   攻击方法: {attack_methods}")
        logger.info(f"   评估指标: {evaluation_metrics}")
        logger.info(f"   数据集: {dataset_name}")

        # 准备任务参数
        task_parameters = {
            'task_type': task_type,
            'attack_methods': attack_methods,
            'evaluation_metrics': evaluation_metrics,
            'dataset_name': dataset_name
        }

        # 创建任务（立即返回任务ID）
        task = task_service.create_task(
            task_type='generate_report',
            sub_task_type='robustness_evaluation',
            model_id=model_id,
            model_name=model_name,
            dataset_name=dataset_name,
            parameters=task_parameters,
            priority=6  # 评估任务中等优先级
        )

        logger.info(f"✅ 评估任务创建成功: {task.id}")
        logger.info(f"   类型: {task.task_type}/{task.sub_task_type}")
        logger.info(f"   队列: {task.queue_name}")
        logger.info(f"   优先级: {task.priority}")

        # 任务将由调度器执行，不需要在这里异步执行
        logger.info(f"✅ 评估任务已创建，等待调度器执行: {task.id}")

        # 立即返回任务ID
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '评估任务已创建，正在后台异步执行',
            'task_info': {
                'type': f'{task.task_type}/{task.sub_task_type}',
                'status': task.status,
                'queue': task.queue_name,
                'created_at': task.created_at.isoformat()
            }
        })

    except Exception as e:
        logger.error(f"❌ 创建评估任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'创建评估任务失败: {str(e)}'
        }), 500

@bp.route('/evaluation/reports', methods=['GET'])
def get_evaluation_reports():
    """获取评估报告列表"""
    try:
        reports = evaluation_service.get_all_reports()
        return jsonify({
            'success': True,
            'data': reports  # reports 已经是字典列表
        }), 200
    except Exception as e:
        logger.error(f"获取报告列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/evaluation/results/<result_id>', methods=['GET'])
def get_evaluation_report(result_id):
    """获取评估报告 - 支持任务ID和报告ID"""
    try:
        import re

        # 检查是否是UUID格式的任务ID
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        is_task_id = bool(re.match(uuid_pattern, result_id))

        if is_task_id:
            # 如果是任务ID，尝试从任务结果中获取
            logger.info(f"🔍 检测到任务ID格式，尝试从任务结果获取: {result_id}")
            task = task_service.get_task(result_id)
            if task and task.result:
                logger.info(f"✅ 从任务 {result_id} 获取结果成功")
                return jsonify({
                    'success': True,
                    'data': task.result
                }), 200
            else:
                logger.warning(f"⚠️ 任务 {result_id} 不存在或没有结果")
                return jsonify({
                    'success': False,
                    'error': '任务不存在或没有结果'
                }), 404

        else:
            # 如果不是任务ID，当作报告ID处理
            logger.info(f"🔍 检测到报告ID格式，从评估报告数据库获取: {result_id}")
            report = evaluation_service.get_report(result_id)
            if report:
                return jsonify({
                    'success': True,
                    'data': report
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': '报告不存在'
                }), 404

    except Exception as e:
        logger.error(f"获取评估结果失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/evaluation/status/<task_id>', methods=['GET'])
def get_evaluation_status(task_id):
    """获取评估任务状态"""
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

@bp.route('/evaluation/generate-report', methods=['POST'])
def generate_report():
    """从批量攻击结果生成鲁棒性评估报告"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        
        # 获取必需参数
        model_name = data.get('model_name')
        task_type = data.get('task_type')
        attack_methods = data.get('attack_methods', ['itgen','alert'])
        evaluation_metrics = data.get('evaluation_metrics', ['asr', 'ami', 'art'])
        
        # 参数验证
        if not model_name:
            return jsonify({'success': False, 'error': '缺少model_name参数'}), 400
        if not task_type:
            return jsonify({'success': False, 'error': '缺少task_type参数'}), 400
        if not isinstance(attack_methods, list) or len(attack_methods) == 0:
            return jsonify({'success': False, 'error': 'attack_methods必须是非空列表'}), 400
        
        logger.info(f"为模型 {model_name} 的任务 {task_type} 生成评估报告...")
        logger.info(f"攻击方法: {attack_methods}, 评估指标: {evaluation_metrics}")
        
        result = evaluation_service.generate_report_from_results(
            model_name=model_name,
            task_type=task_type,
            attack_methods=attack_methods,
            evaluation_metrics=evaluation_metrics
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'report_id': result['report_id'],
                'report': result['report']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"生成报告失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

