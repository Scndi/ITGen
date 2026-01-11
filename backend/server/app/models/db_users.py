"""用户数据库模型定义"""
from datetime import datetime
from typing import Dict, Any, Optional
import bcrypt
from app.extensions import db


class User(db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='用户ID（自增）')
    username = db.Column(db.String(100), nullable=False, unique=True, comment='用户名（唯一）')
    email = db.Column(db.String(200), nullable=False, unique=True, comment='邮箱地址（唯一）')
    password_hash = db.Column(db.String(256), nullable=False, comment='密码哈希')
    full_name = db.Column(db.String(200), comment='真实姓名')
    role = db.Column(db.String(50), default='user', comment='用户角色: admin(管理员)/user(普通用户)')
    status = db.Column(db.String(50), default='active', comment='用户状态: active/inactive/suspended')
    last_login = db.Column(db.DateTime, comment='最后登录时间')
    login_attempts = db.Column(db.Integer, default=0, comment='登录失败次数')
    locked_until = db.Column(db.DateTime, comment='账户锁定截止时间')
    email_verified = db.Column(db.Boolean, default=False, comment='邮箱是否验证')
    phone = db.Column(db.String(20), comment='手机号码')
    department = db.Column(db.String(100), comment='部门')
    position = db.Column(db.String(100), comment='职位')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    def set_password(self, password: str) -> None:
        """设置密码"""
        # 使用bcrypt生成密码哈希
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """验证密码"""
        # 使用bcrypt验证密码
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        except ValueError:
            # 如果哈希格式有问题，返回False
            return False

    def update_last_login(self) -> None:
        """更新最后登录时间"""
        self.last_login = datetime.utcnow()

    def increment_login_attempts(self) -> None:
        """增加登录失败次数"""
        self.login_attempts += 1

    def reset_login_attempts(self) -> None:
        """重置登录失败次数"""
        self.login_attempts = 0
        self.locked_until = None

    def lock_account(self, minutes: int = 30) -> None:
        """锁定账户"""
        self.locked_until = datetime.utcnow() + datetime.timedelta(minutes=minutes)

    def is_account_locked(self) -> bool:
        """检查账户是否被锁定"""
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        return False

    def is_admin(self) -> bool:
        """检查是否为管理员"""
        return self.role == 'admin'

    def is_active(self) -> bool:
        """检查用户是否激活"""
        return self.status == 'active'

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'status': self.status,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'login_attempts': self.login_attempts,
            'locked_until': self.locked_until.isoformat() if self.locked_until else None,
            'email_verified': self.email_verified,
            'phone': self.phone,
            'department': self.department,
            'position': self.position,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        # 敏感信息只在特定情况下返回
        if include_sensitive:
            base_dict['password_hash'] = self.password_hash

        return base_dict

    def to_safe_dict(self) -> Dict[str, Any]:
        """转换为安全的字典（不包含敏感信息）"""
        return self.to_dict(include_sensitive=False)

    def update_profile(self, data: Dict[str, Any]) -> None:
        """更新用户信息"""
        allowed_fields = ['full_name', 'phone', 'department', 'position', 'email']

        for field in allowed_fields:
            if field in data:
                setattr(self, field, data[field])

    def __repr__(self):
        return f'<User {self.id}: {self.username} ({self.role})>'
