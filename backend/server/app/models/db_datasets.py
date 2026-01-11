"""数据集数据库模型定义"""
from datetime import datetime
from app.extensions import db


class Dataset(db.Model):
    """数据集表"""
    __tablename__ = 'datasets'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='数据集ID（自增）')
    dataset_name = db.Column(db.String(200), nullable=False, comment='数据集名称（唯一）')
    task_type = db.Column(db.String(100), nullable=False, comment='任务类型（clone-detection, vulnerability-prediction, code-summarization）')
    description = db.Column(db.Text, comment='数据集描述')
    dataset_path = db.Column(db.String(500), nullable=False, comment='数据集存储路径（目录路径）')
    file_count = db.Column(db.Integer, default=0, comment='文件数量')
    file_types = db.Column(db.JSON, comment='文件类型列表（JSON数组，如 ["jsonl", "txt"]）')
    total_size = db.Column(db.BigInteger, default=0, comment='总大小（字节）')
    source = db.Column(db.String(50), default='user', comment='数据集来源: official(官方)/user(用户上传)')
    status = db.Column(db.String(50), default='available', comment='状态: available/unavailable')
    is_predefined = db.Column(db.Boolean, default=False, comment='是否预定义')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, comment='上传/创建用户ID')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'dataset_name': self.dataset_name,
            'task_type': self.task_type,
            'description': self.description,
            'dataset_path': self.dataset_path,
            'file_count': self.file_count,
            'file_types': self.file_types if isinstance(self.file_types, list) else [],
            'total_size': self.total_size,
            'source': self.source,
            'status': self.status,
            'is_predefined': self.is_predefined,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Dataset {self.id}: {self.dataset_name}>'

