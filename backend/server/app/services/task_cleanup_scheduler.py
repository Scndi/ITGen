"""任务清理调度器 - 定时清理旧任务"""
import logging
import threading
import time
from datetime import datetime
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)

class TaskCleanupScheduler:
    """任务清理调度器"""
    
    def __init__(self, cleanup_interval_hours: int = 24, retention_days: int = 30):
        """
        初始化调度器
        
        Args:
            cleanup_interval_hours: 清理间隔（小时），默认24小时
            retention_days: 任务保留天数，默认30天
        """
        self.cleanup_interval_hours = cleanup_interval_hours
        self.retention_days = retention_days
        self.task_service = TaskService()
        self.running = False
        self.thread = None
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("任务清理调度器已在运行")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"✓ 任务清理调度器已启动（间隔: {self.cleanup_interval_hours}小时，保留: {self.retention_days}天）")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("✓ 任务清理调度器已停止")
    
    def _run(self):
        """运行清理循环"""
        while self.running:
            try:
                # 执行清理
                self._cleanup()
                
                # 等待指定时间
                time.sleep(self.cleanup_interval_hours * 3600)
            except Exception as e:
                logger.error(f"✗ 任务清理调度器执行异常: {str(e)}", exc_info=True)
                # 发生异常时等待1小时再重试
                time.sleep(3600)
    
    def _cleanup(self):
        """执行清理操作"""
        try:
            logger.info("开始清理旧任务...")
            
            # 清理已完成的任务
            completed_count = self.task_service.cleanup_old_tasks(
                days=self.retention_days,
                status='completed'
            )
            
            # 清理失败的任务（保留时间稍短，如15天）
            failed_count = self.task_service.cleanup_old_tasks(
                days=max(15, self.retention_days // 2),
                status='failed'
            )
            
            total_count = completed_count + failed_count
            
            if total_count > 0:
                logger.info(f"✓ 清理完成：删除了 {total_count} 个旧任务（已完成: {completed_count}, 失败: {failed_count}）")
            else:
                logger.debug("没有需要清理的旧任务")
                
        except Exception as e:
            logger.error(f"✗ 清理旧任务失败: {str(e)}", exc_info=True)
    
    def cleanup_now(self, days: int = None, task_type: str = None, status: str = None) -> int:
        """
        立即执行清理
        
        Args:
            days: 保留天数（默认使用配置的 retention_days）
            task_type: 任务类型筛选（可选）
            status: 状态筛选（可选）
        
        Returns:
            删除的任务数量
        """
        if days is None:
            days = self.retention_days
        
        return self.task_service.cleanup_old_tasks(
            days=days,
            task_type=task_type,
            status=status
        )

# 全局调度器实例
_scheduler = None

def get_scheduler() -> TaskCleanupScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskCleanupScheduler()
    return _scheduler

def start_scheduler(cleanup_interval_hours: int = 24, retention_days: int = 30):
    """启动全局调度器"""
    scheduler = get_scheduler()
    scheduler.cleanup_interval_hours = cleanup_interval_hours
    scheduler.retention_days = retention_days
    scheduler.start()

def stop_scheduler():
    """停止全局调度器"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()

