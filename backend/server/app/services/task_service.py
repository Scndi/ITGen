"""任务服务 - 重新设计的任务管理系统"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
from app.models.db_tasks import Task
from app.models.db_models import Model
from app.models.db_datasets import Dataset
from app.extensions import db
import logging

logger = logging.getLogger(__name__)

class TaskService:
    """任务服务类 - 重新设计的任务管理系统"""

    # 任务类型定义
    TASK_TYPES = {
        'attack': {
            'description': '单次攻击任务',
            'queue': 'attack',
            'priority': 8,
            'sub_types': ['itgen', 'beam', 'alert', 'mhm', 'wir', 'rnns', 'bayes', 'style']
        },
        'single_attack': {
            'description': '单次攻击任务',
            'queue': 'attack',
            'priority': 8,
            'sub_types': ['itgen', 'beam', 'alert', 'mhm', 'wir', 'rnns', 'bayes', 'style']
        },
        'batch_attack': {
            'description': '批量攻击任务',
            'queue': 'batch',
            'priority': 7,
            'sub_types': ['itgen', 'beam', 'alert', 'mhm', 'wir', 'rnns', 'bayes', 'style']
        },
        'generate_report': {
            'description': '生成评估报告',
            'queue': 'evaluation',
            'priority': 6,
            'sub_types': ['attack_report', 'model_comparison', 'dataset_analysis']
        },
        'finetune': {
            'description': '模型微调任务',
            'queue': 'finetune',
            'priority': 5,
            'sub_types': ['attack_resistance', 'performance_optimization']
        },
        'evaluate_model': {
            'description': '模型评估任务',
            'queue': 'evaluation',
            'priority': 7,
            'sub_types': ['robustness_test', 'performance_benchmark']
        }
    }

    # 任务状态定义
    TASK_STATUSES = ['pending', 'queued', 'running', 'completed', 'failed', 'cancelled']

    # 队列定义
    QUEUES = ['attack', 'finetune', 'evaluation', 'batch', 'default']

    @staticmethod
    def create_task(
        task_type: str,
        sub_task_type: Optional[str] = None,
        model_id: Optional[int] = None,
        model_name: Optional[str] = None,
        dataset_name: Optional[str] = None,
        parameters: Optional[Dict] = None,
        input_data: Optional[Dict] = None,
        priority: Optional[int] = None,
        task_id: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Task:
        """
        创建新任务

        Args:
            task_type: 任务类型 (attack/single_attack/batch_attack/generate_report/finetune/evaluate_model)
            sub_task_type: 子任务类型（如攻击方法）
            model_id: 模型ID
            model_name: 模型名称
            dataset_name: 数据集名称
            parameters: 任务参数
            input_data: 输入数据
            priority: 优先级（1-10）
            task_id: 自定义任务ID，如果不提供则自动生成

        Returns:
            Task对象
        """
        try:
            # 验证任务类型
            if task_type not in TaskService.TASK_TYPES:
                raise ValueError(f"不支持的任务类型: {task_type}")

            # 生成任务ID
            if not task_id:
                task_id = str(uuid.uuid4())

            # 获取任务配置
            task_config = TaskService.TASK_TYPES[task_type]

            # 设置默认优先级
            if priority is None:
                priority = task_config['priority']

            # 创建任务对象
            task = Task(
                id=task_id,
                task_type=task_type,
                sub_task_type=sub_task_type,
                model_id=model_id,
                model_name=model_name,
                dataset_name=dataset_name,
                status='pending',
                priority=priority,
                progress=0.0,
                parameters=parameters,
                input_data=input_data,
                queue_name=task_config['queue'],
                user_id=user_id,  # 设置任务创建者
                created_at=datetime.utcnow()
            )

            db.session.add(task)
            db.session.commit()

            logger.info(f"✓ 创建任务: {task_id} ({task_type}/{sub_task_type})")
            return task

        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ 创建任务失败: {str(e)}")
            raise
    
    @staticmethod
    def get_task(task_id: str) -> Optional[Task]:
        """获取任务"""
        return Task.query.filter_by(id=task_id).first()
    
    @staticmethod
    def update_task_status(
        task_id: str,
        status: str,
        progress: Optional[float] = None,
        progress_message: Optional[str] = None,
        result: Optional[Dict] = None,
        metrics: Optional[Dict] = None,
        statistics: Optional[Dict] = None,
        output_files: Optional[List] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        worker_id: Optional[str] = None
    ):
        """
        更新任务状态 - 新的任务管理系统

        Args:
            task_id: 任务ID
            status: 任务状态
            progress: 进度（0-100）
            progress_message: 进度消息
            result: 任务结果
            metrics: 评估指标
            statistics: 统计信息
            output_files: 输出文件列表
            error_message: 错误信息
            error_code: 错误代码
            worker_id: 执行任务的worker ID
        """
        task = Task.query.filter_by(id=task_id).first()
        if not task:
            raise ValueError(f'任务 {task_id} 不存在')

        try:
            # 使用Task模型的新方法更新状态
            task.update_status(status, progress, progress_message, error_message, error_code)

            # 更新其他字段
            if result is not None:
                task.result = result
            if metrics is not None:
                task.metrics = metrics
            if statistics is not None:
                task.statistics = statistics
            if output_files is not None:
                task.output_files = output_files
            if worker_id is not None:
                task.worker_id = worker_id

            db.session.commit()
            logger.debug(f"✓ 更新任务状态: {task_id} -> {status} (进度: {progress}%)")
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ 更新任务状态失败: {str(e)}")
            raise
    
    @staticmethod
    def get_all_tasks(
        task_type: Optional[str] = None,
        sub_task_type: Optional[str] = None,
        status: Optional[str] = None,
        queue_name: Optional[str] = None,
        model_id: Optional[int] = None,
        priority_min: Optional[int] = None,
        priority_max: Optional[int] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Task]:
        """
        获取所有任务 - 增强版查询

        Args:
            task_type: 任务类型筛选
            sub_task_type: 子任务类型筛选
            status: 状态筛选
            queue_name: 队列名称筛选
            model_id: 模型ID筛选
            priority_min: 最小优先级
            priority_max: 最大优先级
            created_after: 创建时间之后
            created_before: 创建时间之前
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            任务列表
        """
        query = Task.query

        # 应用筛选条件
        if task_type:
            query = query.filter_by(task_type=task_type)
        if sub_task_type:
            query = query.filter_by(sub_task_type=sub_task_type)
        if status:
            query = query.filter_by(status=status)
        if queue_name:
            query = query.filter_by(queue_name=queue_name)
        if model_id:
            query = query.filter_by(model_id=model_id)

        # 优先级范围筛选
        if priority_min is not None:
            query = query.filter(Task.priority >= priority_min)
        if priority_max is not None:
            query = query.filter(Task.priority <= priority_max)

        # 时间范围筛选
        if created_after:
            query = query.filter(Task.created_at >= created_after)
        if created_before:
            query = query.filter(Task.created_at <= created_before)

        # 排序和分页
        query = query.order_by(Task.priority.desc(), Task.created_at.desc())

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def get_pending_tasks(queue_name: Optional[str] = None, limit: Optional[int] = None) -> List[Task]:
        """
        获取待处理任务

        Args:
            queue_name: 队列名称筛选
            limit: 返回数量限制

        Returns:
            待处理任务列表
        """
        query = Task.query.filter_by(status='pending')

        if queue_name:
            query = query.filter_by(queue_name=queue_name)

        # 按优先级和创建时间排序
        query = query.order_by(Task.priority.desc(), Task.created_at.asc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def get_next_task(queue_name: Optional[str] = None) -> Optional[Task]:
        """
        获取下一个要执行的任务

        Args:
            queue_name: 队列名称

        Returns:
            下一个任务，如果没有则返回None
        """
        query = Task.query.filter_by(status='pending')

        if queue_name:
            query = query.filter_by(queue_name=queue_name)

        # 按优先级和创建时间排序，取第一个
        task = query.order_by(Task.priority.desc(), Task.created_at.asc()).first()

        if task:
            # 标记为已排队
            task.mark_queued()
            db.session.commit()
            logger.info(f"✓ 任务 {task.id} 已进入队列")

        return task

    @staticmethod
    def get_next_pending_task() -> Optional[Task]:
        """
        获取下一个待执行的全局任务（根据优先级选择）
        优先选择pending状态的任务，如果没有则选择queued状态的任务（可能是之前调度失败的任务）

        Returns:
            下一个优先级最高的任务，如果没有则返回None
        """
        try:
            logger.debug("🔍 开始查询下一个待执行任务...")

            # 强制清除所有缓存，确保获取最新数据
            db.session.expire_all()

            # 首先尝试获取pending状态的任务（明确排除已完成、失败、取消的任务）
            task = Task.query.filter(
                Task.status == 'pending'
            ).order_by(Task.priority.desc(), Task.created_at.asc()).first()

            # 如果没有pending任务，尝试获取queued状态的任务（可能是之前调度失败的任务）
            if not task:
                queued_task = Task.query.filter(
                    Task.status == 'queued'
                ).order_by(Task.priority.desc(), Task.created_at.asc()).first()

                if queued_task:
                    # 强制刷新任务状态，确保获取最新状态
                    db.session.refresh(queued_task)

                    # 双重检查：确保任务状态仍然是可执行的
                    current_status = queued_task.status

                    # 如果任务状态已经不是queued或pending，说明任务已被处理
                    if current_status not in ['pending', 'queued']:
                        logger.info(f"⚠️ queued状态的任务 {queued_task.id} 实际状态为 {current_status}，已被其他进程处理，跳过")
                        return None

                    # 再次从数据库重新查询，确认状态
                    fresh_task = Task.query.filter_by(id=queued_task.id).first()
                    if not fresh_task or fresh_task.status not in ['pending', 'queued']:
                        logger.info(f"⚠️ 重新查询任务 {queued_task.id} 状态为 {fresh_task.status if fresh_task else 'None'}，跳过")
                        return None

                    task = fresh_task
                    logger.info(f"🔄 发现queued状态的任务 {task.id}，重新调度")

            if task:
                # 刷新任务状态，确保获取最新状态（从数据库重新加载）
                db.session.refresh(task)
                
                # 严格检查：只接受pending或queued状态的任务，明确排除已完成、失败、取消的任务
                if task.status in ['completed', 'failed', 'cancelled']:
                    logger.warning(f"⚠️ 任务 {task.id} 状态为 {task.status}（已完成/失败/取消），不应该被调度，跳过")
                    return None
                
                if task.status not in ['pending', 'queued']:
                    logger.warning(f"⚠️ 任务 {task.id} 状态为 {task.status}（未知状态），跳过调度")
                    return None
                
                # 如果任务还是pending状态，标记为已排队（queued状态）
                if task.status == 'pending':
                    try:
                        # 再次刷新，确保状态没有变化
                        db.session.refresh(task)
                        if task.status == 'pending':
                            task.mark_queued()
                            db.session.commit()
                            logger.info(f"✅ 任务 {task.id} 已标记为queued状态")
                        else:
                            logger.warning(f"⚠️ 任务 {task.id} 状态在标记前已变为 {task.status}，跳过")
                            return None
                    except Exception as e:
                        logger.error(f"❌ 标记任务 {task.id} 为queued状态失败: {e}")
                        db.session.rollback()
                        # 如果标记失败，重新刷新状态
                        db.session.refresh(task)
                        # 如果状态已经改变，返回None
                        if task.status not in ['pending', 'queued']:
                            logger.warning(f"⚠️ 任务 {task.id} 状态已变为 {task.status}，跳过调度")
                            return None
                
                # 最后一次检查，确保任务状态仍然是pending或queued（不是已完成、失败、取消）
                db.session.refresh(task)
                if task.status in ['completed', 'failed', 'cancelled']:
                    logger.warning(f"⚠️ 任务 {task.id} 在标记为queued后状态变为 {task.status}，跳过调度")
                    return None
                
                if task.status not in ['pending', 'queued']:
                    logger.warning(f"⚠️ 任务 {task.id} 状态为 {task.status}（未知状态），跳过调度")
                    return None
                
                logger.info(f"🎯 调度器选中任务 {task.id} (类型: {task.task_type}, 状态: {task.status}, 优先级: {task.priority})")

            if task:
                logger.debug(f"✅ 找到待执行任务: {task.id} (类型: {task.task_type}, 状态: {task.status})")
            else:
                logger.debug("ℹ️ 没有找到待执行的任务")
            
            return task

        except Exception as e:
            logger.error(f"❌ 获取下一个待执行任务失败: {e}", exc_info=True)
            import traceback
            logger.error(f"完整错误堆栈:\n{traceback.format_exc()}")
            try:
                db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"❌ 回滚数据库事务失败: {rollback_error}")
            return None

    @staticmethod
    def mark_task_running(task_id: str, worker_id: Optional[str] = None) -> bool:
        """
        标记任务开始运行

        Args:
            task_id: 任务ID
            worker_id: 执行任务的worker ID

        Returns:
            是否成功
        """
        try:
            task = Task.query.filter_by(id=task_id).first()
            if not task:
                return False

            task.mark_running(worker_id)
            db.session.commit()
            logger.info(f"✓ 任务 {task_id} 开始运行 (Worker: {worker_id})")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ 标记任务运行失败: {str(e)}")
            return False

    @staticmethod
    def mark_task_completed(
        task_id: str,
        result: Optional[Dict] = None,
        metrics: Optional[Dict] = None,
        statistics: Optional[Dict] = None,
        output_files: Optional[List] = None
    ) -> bool:
        """
        标记任务完成

        Args:
            task_id: 任务ID
            result: 任务结果
            metrics: 评估指标
            statistics: 统计信息
            output_files: 输出文件列表

        Returns:
            是否成功
        """
        try:
            task = Task.query.filter_by(id=task_id).first()
            if not task:
                return False

            task.mark_completed(result, metrics, statistics)
            if output_files:
                task.output_files = output_files

            db.session.commit()
            logger.info(f"✓ 任务 {task_id} 已完成")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ 标记任务完成失败: {str(e)}")
            return False

    @staticmethod
    def mark_task_failed(task_id: str, error_message: str, error_code: Optional[str] = None) -> bool:
        """
        标记任务失败

        Args:
            task_id: 任务ID
            error_message: 错误信息
            error_code: 错误代码

        Returns:
            是否成功
        """
        try:
            task = Task.query.filter_by(id=task_id).first()
            if not task:
                return False

            task.mark_failed(error_message, error_code)

            # 检查是否可以重试
            if task.can_retry():
                task.increment_retry()
                task.status = 'pending'  # 重置为待处理状态
                logger.info(f"✓ 任务 {task_id} 失败，将重试 (第{task.retry_count}次)")
            else:
                logger.warning(f"⚠ 任务 {task_id} 失败，已达到最大重试次数")

            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ 标记任务失败失败: {str(e)}")
            return False

    @staticmethod
    def cancel_task(task_id: str, reason: Optional[str] = None) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID
            reason: 取消原因

        Returns:
            是否成功
        """
        try:
            logger.info(f"🔄 尝试取消任务: {task_id}, 原因: {reason}")
            task = Task.query.filter_by(id=task_id).first()
            if not task:
                logger.warning(f"❌ 任务不存在: {task_id}")
                return False

            logger.info(f"📋 任务当前状态: {task.status}, 进度: {task.progress}")
            task.update_status('cancelled', progress_message=reason or '任务已取消')
            db.session.commit()
            logger.info(f"✓ 任务 {task_id} 已取消")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ 取消任务失败: {str(e)}")
            logger.error(f"🔍 错误详情: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"🔍 完整堆栈: {traceback.format_exc()}")
            return False

    @staticmethod
    def delete_task(task_id: str) -> bool:
        """删除任务"""
        task = Task.query.filter_by(id=task_id).first()
        if not task:
            return False

        try:
            db.session.delete(task)
            db.session.commit()
            logger.info(f"✓ 删除任务: {task_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ 删除任务失败: {str(e)}")
            raise

    @staticmethod
    def cleanup_old_tasks(
        days: int = 30,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        keep_failed: bool = True
    ) -> int:
        """
        清理旧任务 - 增强版

        Args:
            days: 保留天数（默认30天）
            task_type: 任务类型筛选
            status: 状态筛选
            keep_failed: 是否保留失败的任务（用于分析）

        Returns:
            删除的任务数量
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = Task.query.filter(Task.created_at < cutoff_date)

        if task_type:
            query = query.filter_by(task_type=task_type)

        # 根据状态筛选
        if status:
            query = query.filter_by(status=status)
        elif keep_failed:
            # 如果keep_failed为True，保留失败和运行中的任务
            query = query.filter(Task.status.in_(['completed', 'cancelled']))
        else:
            # 否则清理所有完成状态的任务
            query = query.filter(Task.status.in_(['completed', 'failed', 'cancelled']))

        tasks_to_delete = query.all()
        count = len(tasks_to_delete)

        if count > 0:
            try:
                for task in tasks_to_delete:
                    db.session.delete(task)
                db.session.commit()
                logger.info(f"✓ 清理了 {count} 个旧任务（{days} 天前）")
            except Exception as e:
                db.session.rollback()
                logger.error(f"✗ 清理旧任务失败: {str(e)}")
                raise

        return count

    @staticmethod
    def get_task_statistics(
        task_type: Optional[str] = None,
        queue_name: Optional[str] = None,
        days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取任务统计信息 - 增强版

        Args:
            task_type: 任务类型筛选
            queue_name: 队列名称筛选
            days: 统计最近N天的任务

        Returns:
            统计信息字典
        """
        try:
            query = Task.query

            # 应用筛选条件
            if task_type:
                query = query.filter_by(task_type=task_type)
            if queue_name:
                query = query.filter_by(queue_name=queue_name)
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                query = query.filter(Task.created_at >= cutoff_date)

            # 基本统计
            total = query.count()
            stats = {
                'total': total,
                'time_range': f'最近{days}天' if days else '全部时间',
                'by_type': {},
                'by_status': {},
                'by_queue': {},
                'performance': {}
            }

            if total == 0:
                return stats

            # 按任务类型统计
            task_types = db.session.query(Task.task_type, db.func.count(Task.id)).filter(
                Task.id.in_(query.with_entities(Task.id))
            ).group_by(Task.task_type).all()

            for task_type_name, count in task_types:
                stats['by_type'][task_type_name] = count

            # 按状态统计
            statuses = db.session.query(Task.status, db.func.count(Task.id)).filter(
                Task.id.in_(query.with_entities(Task.id))
            ).group_by(Task.status).all()

            for status, count in statuses:
                stats['by_status'][status] = count

            # 按队列统计
            queues = db.session.query(Task.queue_name, db.func.count(Task.id)).filter(
                Task.id.in_(query.with_entities(Task.id))
            ).group_by(Task.queue_name).all()

            for queue, count in queues:
                stats['by_queue'][queue or 'default'] = count

            # 性能统计
            completed_tasks = query.filter_by(status='completed').all()
            if completed_tasks:
                execution_times = [t.execution_time for t in completed_tasks if t.execution_time]
                if execution_times:
                    stats['performance'] = {
                        'avg_execution_time': sum(execution_times) / len(execution_times),
                        'min_execution_time': min(execution_times),
                        'max_execution_time': max(execution_times),
                        'completed_count': len(completed_tasks)
                    }

            return stats

        except Exception as e:
            logger.error(f"✗ 获取任务统计失败: {str(e)}")
            return {'error': str(e)}

    @staticmethod
    def get_queue_status(queue_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取队列状态

        Args:
            queue_name: 队列名称，如果为None则返回所有队列状态

        Returns:
            队列状态字典
        """
        try:
            if queue_name:
                # 单个队列状态
                active_count = Task.query.filter_by(
                    queue_name=queue_name,
                    status='running'
                ).count()

                pending_count = Task.query.filter_by(
                    queue_name=queue_name,
                    status='pending'
                ).count()

                return {
                    'queue_name': queue_name,
                    'active_tasks': active_count,
                    'pending_tasks': pending_count,
                    'total_tasks': active_count + pending_count
                }
            else:
                # 所有队列状态
                queues = {}
                for q_name in TaskService.QUEUES:
                    queues[q_name] = TaskService.get_queue_status(q_name)

                return queues

        except Exception as e:
            logger.error(f"✗ 获取队列状态失败: {str(e)}")
            return {'error': str(e)}

