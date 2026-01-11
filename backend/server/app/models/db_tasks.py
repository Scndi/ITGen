"""任务数据库模型定义 - 重新设计的任务管理系统"""
from datetime import datetime
from typing import Dict, Any, Optional
from app.extensions import db


class Task(db.Model):
    """任务表（重新设计的任务管理系统）"""
    __tablename__ = 'tasks'

    # 基本信息
    id = db.Column(db.String(100), primary_key=True, comment='任务ID（UUID）')
    task_type = db.Column(db.String(100), nullable=False, comment='任务类型: attack/single_attack/batch_attack/generate_report/finetune/evaluate_model')
    sub_task_type = db.Column(db.String(100), comment='子任务类型（如攻击方法: itgen, beam, alert, mhm, wir, rnns, bayes, style）')

    # 关联信息
    model_id = db.Column(db.Integer, db.ForeignKey('models.id'), nullable=True, comment='使用的模型ID')
    model_name = db.Column(db.String(200), comment='模型名称')
    dataset_name = db.Column(db.String(200), comment='数据集名称')

    # 任务状态和进度
    status = db.Column(db.String(50), default='pending', comment='任务状态: pending/queued/running/completed/failed/cancelled')
    priority = db.Column(db.Integer, default=5, comment='优先级（1-10，10最高）')
    progress = db.Column(db.Float, default=0.0, comment='进度(0-100)')
    progress_message = db.Column(db.String(500), comment='进度消息')

    # 任务参数和输入
    parameters = db.Column(db.JSON, comment='任务参数（JSON格式）')
    input_data = db.Column(db.JSON, comment='输入数据（代码、数据集等）')

    # 任务结果
    result = db.Column(db.JSON, comment='任务结果（JSON格式）')
    output_files = db.Column(db.JSON, comment='输出文件路径列表')
    metrics = db.Column(db.JSON, comment='评估指标')
    statistics = db.Column(db.JSON, comment='统计信息')

    # 错误处理
    error_message = db.Column(db.Text, comment='错误信息')
    error_code = db.Column(db.String(100), comment='错误代码')

    # 资源使用
    resource_usage = db.Column(db.JSON, comment='资源使用情况（CPU、内存、GPU等）')
    execution_time = db.Column(db.Float, comment='执行时间（秒）')

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    queued_at = db.Column(db.DateTime, comment='进入队列时间')
    started_at = db.Column(db.DateTime, comment='开始执行时间')
    completed_at = db.Column(db.DateTime, comment='完成时间')

    # 队列管理
    queue_name = db.Column(db.String(100), default='default', comment='队列名称')
    worker_id = db.Column(db.String(100), comment='执行任务的worker ID')
    retry_count = db.Column(db.Integer, default=0, comment='重试次数')
    max_retries = db.Column(db.Integer, default=3, comment='最大重试次数')

    # 用户关联
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, comment='创建任务的用户ID')

    # 兼容性字段（保留旧字段名）
    message = db.Column(db.String(500), comment='状态消息（兼容性字段）')

    # 向后兼容字段（微调任务）
    dataset = db.Column(db.String(200), comment='数据集名称（兼容性字段）')
    attack_method = db.Column(db.String(100), comment='攻击方法（兼容性字段）')
    training_samples = db.Column(db.Integer, comment='训练样本数（兼容性字段）')
    old_metrics = db.Column(db.JSON, comment='微调前的指标（兼容性字段）')
    new_metrics = db.Column(db.JSON, comment='微调后的指标（兼容性字段）')
    comparison = db.Column(db.JSON, comment='指标对比（兼容性字段）')

    # 批量测试任务专用字段
    result_file = db.Column(db.String(500), comment='结果文件路径（兼容性字段）')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = {
            # 基本信息
            'id': self.id,
            'task_type': self.task_type,
            'sub_task_type': self.sub_task_type,

            # 关联信息
            'model_id': self.model_id,
            'model_name': self.model_name,
            'dataset_name': self.dataset_name,

            # 任务状态和进度
            'status': self.status,
            'priority': self.priority,
            'progress': self.progress,
            'progress_message': self.progress_message,

            # 任务参数和输入
            'parameters': self.parameters,
            'input_data': self.input_data,

            # 任务结果
            'result': self.result,
            'output_files': self.output_files,
            'metrics': self.metrics,
            'statistics': self.statistics,

            # 错误处理
            'error_message': self.error_message,
            'error_code': self.error_code,

            # 资源使用
            'resource_usage': self.resource_usage,
            'execution_time': self.execution_time,

            # 时间戳
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'queued_at': self.queued_at.isoformat() if self.queued_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,

            # 队列管理
            'queue_name': self.queue_name,
            'worker_id': self.worker_id,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,

            # 用户关联
            'user_id': self.user_id
        }

        # 移除None值，保持API清洁
        return {k: v for k, v in base_dict.items() if v is not None}

    def update_status(self, status: str, progress: Optional[float] = None,
                     progress_message: Optional[str] = None,
                     error_message: Optional[str] = None,
                     error_code: Optional[str] = None) -> None:
        """更新任务状态"""
        self.status = status

        if progress is not None:
            self.progress = progress
        if progress_message is not None:
            self.progress_message = progress_message
        if error_message is not None:
            self.error_message = error_message
        if error_code is not None:
            self.error_code = error_code

        # 更新时间戳
        now = datetime.utcnow()
        if status == 'queued' and not self.queued_at:
            self.queued_at = now
        elif status == 'running' and not self.started_at:
            self.started_at = now
        elif status in ['completed', 'failed', 'cancelled']:
            if not self.completed_at:
                self.completed_at = now
                if self.started_at:
                    self.execution_time = (self.completed_at - self.started_at).total_seconds()

    def mark_queued(self, queue_name: Optional[str] = None) -> None:
        """标记任务已进入队列"""
        if queue_name:
            self.queue_name = queue_name
        self.update_status('queued')

    def mark_running(self, worker_id: Optional[str] = None) -> None:
        """标记任务开始运行"""
        if worker_id:
            self.worker_id = worker_id
        self.update_status('running')

    def mark_completed(self, result: Optional[Dict[str, Any]] = None,
                      metrics: Optional[Dict[str, Any]] = None,
                      statistics: Optional[Dict[str, Any]] = None) -> None:
        """标记任务完成"""
        self.result = result
        self.metrics = metrics
        self.statistics = statistics
        self.update_status('completed', progress=100.0, progress_message='任务完成')

    def mark_failed(self, error_message: str, error_code: Optional[str] = None) -> None:
        """标记任务失败"""
        self.update_status('failed', error_message=error_message, error_code=error_code)

    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """增加重试次数"""
        self.retry_count += 1
    
    def __repr__(self):
        return f'<Task {self.id}: {self.task_type} ({self.status})>'

