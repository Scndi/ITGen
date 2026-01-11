from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from app.config import Config
from app.utils.logger import setup_logger
from app.extensions import db
import logging

logger = logging.getLogger(__name__)

# 初始化扩展
cors = CORS()

def create_app(config_class=Config):
    """Flask应用工厂"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化CORS - 允许所有路径和方法
    cors.init_app(app, resources={
        r"/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://172.28.241.93:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    # 初始化数据库
    db.init_app(app)
    
    # 创建数据库表
    with app.app_context():
        try:
            from app.models.db_models import Model
            from app.models.db_datasets import Dataset
            from app.models.db_tasks import Task
            from app.models.db_evaluation import EvaluationReport
            from app.models.db_users import User
            db.create_all()
        except Exception as e:
            # 忽略数据库连接警告（如果数据库尚未设置）
            if 'HY000' not in str(e):
                pass
    
    # 配置日志
    setup_logger(app)
    
    # 注册蓝图
    from app.api.health import bp as health_bp
    app.register_blueprint(health_bp, url_prefix='/api')
    
    from app.api.models import bp as models_bp
    app.register_blueprint(models_bp, url_prefix='/api')
    
    from app.api.attack import bp as attack_bp
    app.register_blueprint(attack_bp, url_prefix='/api')

    # 注册新的攻击API（重新设计的任务管理系统）
    from app.api.new_attack import bp as new_attack_bp
    app.register_blueprint(new_attack_bp, url_prefix='/api')
    
    from app.api.evaluation import bp as evaluation_bp
    app.register_blueprint(evaluation_bp, url_prefix='/api')
    
    from app.api.finetuning import bp as finetuning_bp
    app.register_blueprint(finetuning_bp, url_prefix='/api')
    
    
    from app.api.tasks import bp as tasks_bp
    app.register_blueprint(tasks_bp, url_prefix='/api')
    
    from app.api.datasets import bp as datasets_bp
    app.register_blueprint(datasets_bp, url_prefix='/api')

    # 注册认证和管理员蓝图
    from app.controllers.auth_controller import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.controllers.admin_controller import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # 初始化SocketIO（在蓝图注册后）
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # 将socketio附加到app上以便访问
    app.socketio = socketio
    
    # 启动任务执行调度器（默认启用）
    import os
    if os.environ.get('ENABLE_TASK_EXECUTION_SCHEDULER', 'true').lower() == 'true':
        from app.services.task_execution_scheduler import TaskExecutionScheduler
        execution_scheduler = TaskExecutionScheduler(app, check_interval=2)  # 每2秒检查一次，更快响应
        execution_scheduler.start()

        # 将调度器保存到app对象中，以便后续停止
        app.task_execution_scheduler = execution_scheduler
        logger.info("✓ 任务执行调度器已启用（检查间隔: 5秒）")

    # 启动任务清理调度器（可选，通过环境变量控制）
    if os.environ.get('ENABLE_TASK_CLEANUP', 'false').lower() == 'true':
        from app.services.task_cleanup_scheduler import start_scheduler
        cleanup_interval = int(os.environ.get('TASK_CLEANUP_INTERVAL_HOURS', '24'))
        retention_days = int(os.environ.get('TASK_RETENTION_DAYS', '30'))
        start_scheduler(cleanup_interval_hours=cleanup_interval, retention_days=retention_days)
        logger.info(f"任务清理调度器已启用（间隔: {cleanup_interval}小时，保留: {retention_days}天）")
    
    return app

# 导出
__all__ = ['create_app']
