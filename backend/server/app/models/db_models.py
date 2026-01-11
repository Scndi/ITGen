"""数据库模型定义"""
from datetime import datetime
from typing import Dict, Any
from app.extensions import db


class Model(db.Model):
    """模型表"""
    __tablename__ = 'models'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='模型ID（自增）')
    model_name = db.Column(db.String(200), nullable=False, comment='模型名称')
    model_type = db.Column(db.String(100), nullable=False, comment='模型类型')
    description = db.Column(db.Text, comment='模型描述')
    model_path = db.Column(db.String(500), nullable=False, comment='模型路径（官方HuggingFace路径或本地路径）')
    tokenizer_path = db.Column(db.String(500), nullable=False, comment='Tokenizer路径（官方HuggingFace路径或本地路径）')
    mlm_model_path = db.Column(db.String(500), comment='MLM模型路径（用于生成替代词，官方路径或本地路径）')
    checkpoint_path = db.Column(db.String(500), comment='微调权重路径（本地路径，可选）')
    model_source = db.Column(db.String(50), default='official', comment='模型来源: official(官方)/user(用户上传)')
    max_length = db.Column(db.Integer, default=512, comment='最大长度')
    status = db.Column(db.String(50), default='available', comment='状态: available/unavailable')
    supported_tasks = db.Column(db.JSON, comment='支持的任务')
    is_predefined = db.Column(db.Boolean, default=False, comment='是否预定义')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, comment='上传/创建用户ID')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    

    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'description': self.description,
            'model_path': self.model_path,
            'tokenizer_path': self.tokenizer_path,
            'mlm_model_path': self.mlm_model_path,
            'checkpoint_path': self.checkpoint_path,
            'model_source': self.model_source,
            'max_length': self.max_length,
            'supported_tasks': self.supported_tasks if isinstance(self.supported_tasks, list) else [],
            'status': self.status,
            'is_predefined': self.is_predefined,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Model {self.id}: {self.model_name}>'

