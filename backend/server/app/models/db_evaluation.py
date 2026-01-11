"""评估报告数据库模型定义"""
from datetime import datetime
from typing import Dict, Any, List
from app.extensions import db


class EvaluationReport(db.Model):
    """评估报告表"""
    __tablename__ = 'evaluation_reports'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='报告ID（自增）')
    report_id = db.Column(db.String(200), unique=True, nullable=False, comment='报告ID（唯一标识）')
    model_name = db.Column(db.String(200), nullable=False, comment='模型名称')
    task_type = db.Column(db.String(100), nullable=False, comment='任务类型')
    attack_methods = db.Column(db.JSON, comment='攻击方法列表')
    evaluation_metrics = db.Column(db.JSON, comment='评估指标列表')
    
    # 总体指标
    total_samples = db.Column(db.Integer, default=0, comment='总样本数')
    successful_attacks = db.Column(db.Integer, default=0, comment='成功攻击数')
    failed_attacks = db.Column(db.Integer, default=0, comment='失败攻击数')
    
    # ASR - Attack Success Rate (攻击成功率)
    asr = db.Column(db.Float, default=0.0, comment='攻击成功率')
    # AMI - Average Model Invocations (平均模型调用次数)
    ami = db.Column(db.Float, default=0.0, comment='平均模型调用次数')
    # ART - Average Response Time (平均响应时间)
    art = db.Column(db.Float, default=0.0, comment='平均响应时间（分钟）')
    
    # 额外统计
    avg_program_length = db.Column(db.Float, default=0.0, comment='平均程序长度')
    avg_identifiers = db.Column(db.Float, default=0.0, comment='平均标识符数量')
    
    # 详细结果
    method_metrics = db.Column(db.JSON, comment='各攻击方法的详细指标')
    summary_stats = db.Column(db.JSON, comment='汇总统计')
    sample_results = db.Column(db.JSON, comment='样本结果')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'report_id': self.report_id,
            'model_name': self.model_name,
            'task_type': self.task_type,
            'attack_methods': self.attack_methods if isinstance(self.attack_methods, list) else [],
            'evaluation_metrics': self.evaluation_metrics if isinstance(self.evaluation_metrics, list) else [],
            'total_samples': self.total_samples,
            'successful_attacks': self.successful_attacks,
            'failed_attacks': self.failed_attacks,
            'asr': self.asr,
            'ami': self.ami,
            'art': self.art,
            'avg_program_length': self.avg_program_length,
            'avg_identifiers': self.avg_identifiers,
            'method_metrics': self.method_metrics,
            'summary_stats': self.summary_stats,
            'sample_results': self.sample_results,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<EvaluationReport {self.report_id}: {self.model_name} ({self.task_type})>'

