"""任务执行调度器 - 管理和执行异步任务"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from flask import current_app
from app.services.task_service import TaskService
from app.services.attack_service import AttackService
from app.extensions import db

logger = logging.getLogger(__name__)


class TaskExecutionScheduler:
    """任务执行调度器 - 选择最高优先级的任务并执行"""

    def __init__(self, app, check_interval: int = 5, task_timeout: int = 1800):
        """
        初始化调度器

        Args:
            app: Flask应用实例
            check_interval: 检查间隔（秒），默认5秒
            task_timeout: 任务超时时间（秒），默认30分钟
        """
        self.app = app
        self.check_interval = check_interval
        self.task_timeout = task_timeout  # 任务超时时间
        self.task_service = TaskService()
        self.attack_service = AttackService()
        self.running = False
        self.thread = None
        self.active_tasks: Dict[str, Dict[str, Any]] = {}  # 正在执行的任务信息: {task_id: {'thread': thread, 'start_time': datetime}}
        self.task_start_times: Dict[str, datetime] = {}  # 任务开始时间

    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("⚠️ 调度器已在运行")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True, name="TaskExecutionScheduler")
        self.thread.start()
        logger.info(f"✅ 任务执行调度器已启动（检查间隔: {self.check_interval}秒, 线程名: {self.thread.name})")
        
        # 等待一小段时间确保线程启动
        time.sleep(0.1)
        
        if self.thread.is_alive():
            logger.info(f"✅ 调度器线程运行正常 (线程ID: {self.thread.ident})")
        else:
            logger.error(f"❌ 调度器线程启动失败！")

    def stop(self):
        """停止调度器"""
        logger.info("🛑 正在停止任务执行调度器...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

        # 取消所有活动任务
        active_task_ids = list(self.active_tasks.keys())
        for task_id in active_task_ids:
            self.cancel_task(task_id, "调度器关闭")

        logger.info(f"✓ 任务执行调度器已停止，已取消 {len(active_task_ids)} 个活动任务")

    def _run(self):
        """运行调度循环"""
        logger.info("🔄 调度器主循环开始运行...")
        with self.app.app_context():
            iteration = 0
            while self.running:
                try:
                    iteration += 1
                    if iteration % 10 == 0:  # 每10次循环记录一次日志
                        logger.debug(f"📊 调度器运行中... (第 {iteration} 次循环, 活跃任务数: {len(self.active_tasks)})")

                    # 检查并清理超时的任务
                    self._check_timeout_tasks()
                    
                    # 查找并执行下一个任务
                    self._check_and_execute_next_task()

                    # 清理已完成的任务线程
                    self._cleanup_completed_threads()

                except Exception as e:
                    logger.error(f"❌ 调度器运行出错: {e}", exc_info=True)
                    import traceback
                    logger.error(f"完整错误堆栈:\n{traceback.format_exc()}")

                # 等待下次检查
                time.sleep(self.check_interval)
        
        logger.info("🛑 调度器主循环已停止")

    def _check_and_execute_next_task(self):
        """检查并执行下一个优先级最高的任务"""
        try:
            # 在应用上下文中执行所有数据库操作
            with self.app.app_context():
                next_task = self.task_service.get_next_pending_task()

                if not next_task:
                    # 没有待执行任务，这是正常的，不需要记录日志（避免日志过多）
                    return

                task_id = next_task.id
                task_type = next_task.task_type

                # 再次检查任务状态，确保任务仍然是pending或queued状态
                current_task = self.task_service.get_task(task_id)
                if not current_task:
                    logger.warning(f"任务 {task_id} 不存在，跳过")
                    return

                # 严格检查：只接受pending或queued状态的任务
                if current_task.status not in ['pending', 'queued']:
                    logger.warning(f"⚠️ 任务 {task_id} 状态为 {current_task.status}（已完成/失败/取消），跳过执行")
                    # 如果任务状态是queued但实际状态不是pending或queued，更新数据库状态
                    if next_task.status == 'queued' and current_task.status != 'queued':
                        logger.info(f"🔄 更新任务 {task_id} 状态从 queued 到 {current_task.status}")
                        try:
                            from app.models.db_tasks import Task
                            Task.query.filter_by(id=task_id).update({'status': current_task.status})
                            db.session.commit()
                            logger.info(f"✅ 已更新任务 {task_id} 的数据库状态为 {current_task.status}")
                        except Exception as e:
                            logger.error(f"❌ 更新任务 {task_id} 状态失败: {e}")
                            db.session.rollback()
                    return

                # 额外检查：确保任务不是已完成、失败或取消状态
                if current_task.status in ['completed', 'failed', 'cancelled']:
                    logger.warning(f"⚠️ 任务 {task_id} 状态为 {current_task.status}，不应该被调度，跳过执行")
                    # 如果任务状态是queued但实际状态是completed/failed/cancelled，更新数据库状态
                    if next_task.status == 'queued':
                        logger.info(f"🔄 更新任务 {task_id} 状态从 queued 到 {current_task.status}")
                        try:
                            from app.models.db_tasks import Task
                            Task.query.filter_by(id=task_id).update({'status': current_task.status})
                            db.session.commit()
                            logger.info(f"✅ 已更新任务 {task_id} 的数据库状态为 {current_task.status}")
                        except Exception as e:
                            logger.error(f"❌ 更新任务 {task_id} 状态失败: {e}")
                            db.session.rollback()
                    return

                logger.info(f"🎯 找到待执行任务: {task_id} (类型: {task_type}, 状态: {next_task.status})")

                # 检查是否已经在执行
                if task_id in self.active_tasks:
                    task_info = self.active_tasks[task_id]
                    thread = task_info['thread']
                    if thread.is_alive():
                        logger.warning(f"任务 {task_id} 已在执行中，跳过")
                        return
                    else:
                        # 线程已结束但未清理，先清理
                        logger.info(f"清理已完成的任务线程: {task_id}")
                        del self.active_tasks[task_id]

            # 启动任务执行线程（在应用上下文之外）
                execution_thread = threading.Thread(
                    target=self._execute_task,
                    args=(next_task,),
                daemon=True,
                name=f"Task-{task_id}"
                )
                execution_thread.start()

            # 记录活动任务和开始时间
            self.active_tasks[task_id] = {
                'thread': execution_thread,
                'start_time': datetime.now(),
                'task_type': task_type
            }

            logger.info(f"🚀 已启动任务 {task_id} 的执行线程 (线程名: {execution_thread.name})")

        except Exception as e:
            logger.error(f"检查下一个任务时出错: {e}", exc_info=True)

    def _execute_task(self, task):
        """执行单个任务"""
        task_id = task.id
        task_type = task.task_type

        # 记录任务开始时间
        task_start_time = datetime.now()
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['start_time'] = task_start_time

        logger.info(f"⚙️ 开始执行任务 {task_id} (开始时间: {task_start_time})")

        with self.app.app_context():
            try:
                # 再次检查任务状态，确保任务没有被取消
                current_task = self.task_service.get_task(task_id)
                if not current_task:
                    logger.warning(f"任务 {task_id} 不存在，停止执行")
                    return
                
                if current_task.status == 'cancelled':
                    logger.info(f"任务 {task_id} 已被取消，停止执行")
                    return
                
                # 严格检查：只接受pending或queued状态的任务
                if current_task.status not in ['pending', 'queued']:
                    logger.warning(f"⚠️ 任务 {task_id} 状态为 {current_task.status}，无法执行（已完成/失败/取消）")
                    return
                
                # 额外检查：确保任务不是已完成、失败或取消状态
                if current_task.status in ['completed', 'failed', 'cancelled']:
                    logger.warning(f"⚠️ 任务 {task_id} 状态为 {current_task.status}，不应该被执行，停止执行")
                    return

                logger.info(f"⚡ 开始执行任务 {task_id} (类型: {task_type})")

                # 更新任务状态为运行中
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='running',
                    progress=0,
                    progress_message='任务开始执行'
                )

                # 根据任务类型执行相应的逻辑
                if task_type in ['single_attack', 'attack']:
                    self._execute_attack_task(task)
                elif task_type == 'batch_attack':
                    self._execute_batch_testing_task(task)
                elif task_type == 'generate_report':
                    self._execute_evaluation_task(task)
                elif task_type == 'finetune':
                    self._execute_finetuning_task(task)
                else:
                    logger.warning(f"未知任务类型: {task_type}")
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='failed',
                        progress=0,
                        progress_message=f'未知任务类型: {task_type}'
                    )

            except Exception as e:
                logger.error(f"执行任务 {task_id} 时出错: {e}")
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='failed',
                    progress=0,
                    progress_message=f'执行失败: {str(e)}'
                )
            finally:
                # 从活动任务中移除
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                    logger.debug(f"已从活动任务列表中移除任务 {task_id}")

    def _execute_attack_task(self, task):
        """执行攻击任务"""
        task_id = task.id
        parameters = task.parameters or {}

        logger.info(f"🎯 执行攻击任务 {task_id}")

        try:
            # 模拟攻击执行过程
            progress_steps = [
                (10, '正在初始化攻击环境...'),
                (25, '正在加载模型和数据集...'),
                (45, '正在分析原始代码...'),
                (65, '正在生成对抗样本...'),
                (85, '正在验证攻击效果...'),
                (100, '攻击任务完成')
            ]

            for progress, message in progress_steps:
                # 检查任务是否已被取消
                with self.app.app_context():
                    current_task = self.task_service.get_task(task_id)
                    if current_task and current_task.status == 'cancelled':
                        logger.info(f"🛑 任务 {task_id} 已被取消，停止执行")
                        return
                
                logger.info(f"📊 任务 {task_id} 进度更新: {progress}% - {message}")

                # 更新进度
                with self.app.app_context():
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='running',
                        progress=progress,
                        progress_message=message
                    )

                # 模拟执行时间 - 缩短到0.5秒，让进度更新更快
                time.sleep(0.5)

            # 再次检查任务是否已被取消
            with self.app.app_context():
                current_task = self.task_service.get_task(task_id)
                if current_task and current_task.status == 'cancelled':
                    logger.info(f"🛑 任务 {task_id} 已被取消，停止执行")
                    return
            
            # 使用固定的演示数据（来自JSONL文件的Index 3）
            # 这是一条成功的攻击结果，包含完整的Original Code和Adversarial Code
            demo_original_code = """    public static boolean encodeFileToFile(String infile, String outfile) {
        boolean success = false;
        java.io.InputStream in = null;
        java.io.OutputStream out = null;
        try {
            in = new Base64.InputStream(new java.io.BufferedInputStream(new java.io.FileInputStream(infile)), Base64.ENCODE);
            out = new java.io.BufferedOutputStream(new java.io.FileOutputStream(outfile));
            byte[] buffer = new byte[65536];
            int read = -1;
            while ((read = in.read(buffer)) >= 0) {
                out.write(buffer, 0, read);
            }
            success = true;
        } catch (java.io.IOException exc) {
            exc.printStackTrace();
        } finally {
            try {
                in.close();
            } catch (Exception exc) {
            }
            try {
                out.close();
            } catch (Exception exc) {
            }
        }
        return success;
    }
"""
            
            demo_adversarial_code = """    public static boolean encodeFileToFile(String infile, String outfile) {
        boolean success = false;
        java.io.InputStream FTPClient = null;
        java.io.OutputStream out = null;
        try {
            FTPClient = new Base64.InputStream(new java.io.BufferedInputStream(new java.io.FileInputStream(infile)), Base64.ENCODE);
            out = new java.io.BufferedOutputStream(new java.io.FileOutputStream(outfile));
            byte[] buffer = new byte[65536];
            int read = -1;
            while ((read = FTPClient.read(buffer)) >= 0) {
                out.write(buffer, 0, read);
            }
            success = true;
        } catch (java.io.IOException exc) {
            exc.printStackTrace();
        } finally {
            try {
                FTPClient.close();
            } catch (Exception exc) {
            }
            try {
                out.close();
            } catch (Exception exc) {
            }
        }
        return success;
    }
"""
            
            # 解析Replaced Identifiers字符串 "in:FTPClient," 为字典格式
            replaced_identifiers_str = "in:FTPClient,"
            replaced_words = {}
            if replaced_identifiers_str:
                # 解析格式 "old:new," 或 "old:new"
                parts = replaced_identifiers_str.rstrip(',').split(',')
                for part in parts:
                    if ':' in part:
                        old, new = part.split(':', 1)
                        replaced_words[old.strip()] = new.strip()
            
            # 生成完整的静态结果，包含所有前端需要展示的数据
            result = {
                'success': True,
                'original_code': demo_original_code,
                'adversarial_code': demo_adversarial_code,
                'replaced_words': replaced_words,
                'query_times': 21,
                'time_cost': 0.023266069094340005,
                'method': parameters.get('method', 'itgen'),
                'model_name': task.model_name or parameters.get('model_name', 'CodeBERT'),
                'task_type': parameters.get('task_type', 'clone-detection'),
                'language': parameters.get('language', 'Java'),  # 演示数据是Java代码
                'attack_strategy': parameters.get('attack_strategy', 'identifier_rename'),
                'max_modifications': parameters.get('max_modifications', 5),
                'max_query_times': parameters.get('max_query_times', 200),
                'time_limit': parameters.get('time_limit', 60),
                'max_substitutions': parameters.get('max_substitutions', 10),
                'note': '演示攻击结果 - 使用JSONL文件Index 3的数据'
            }
            
            logger.info(f"📝 任务 {task_id} 使用演示数据（JSONL Index 3）: original_code长度={len(demo_original_code)}, adversarial_code长度={len(demo_adversarial_code)}")

            # 更新任务为完成状态
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='completed',
                    progress=100,
                    progress_message='攻击任务完成',
                    result=result
                )

            logger.info(f"✅ 攻击任务 {task_id} 执行完成")

        except Exception as e:
            logger.error(f"攻击任务 {task_id} 执行失败: {e}")
            raise

    def _execute_batch_testing_task(self, task):
        """执行批量测试任务"""
        task_id = task.id
        parameters = task.parameters or {}
        logger.info(f"📊 执行批量测试任务 {task_id}")

        try:
            # 模拟批量测试执行过程
            progress_steps = [
                (10, '正在初始化批量测试环境...'),
                (25, '正在加载模型和数据集...'),
                (45, '正在处理测试样本...'),
                (65, '正在生成对抗样本...'),
                (85, '正在统计测试结果...'),
                (100, '批量测试完成')
            ]

            for progress, message in progress_steps:
                # 检查任务是否已被取消
                with self.app.app_context():
                    current_task = self.task_service.get_task(task_id)
                    if current_task and current_task.status == 'cancelled':
                        logger.info(f"🛑 任务 {task_id} 已被取消，停止执行")
                        return
                
                logger.info(f"📊 任务 {task_id} 进度更新: {progress}% - {message}")

                # 更新进度
                with self.app.app_context():
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='running',
                        progress=progress,
                        progress_message=message
                    )

                # 模拟执行时间
                time.sleep(0.5)

            # 再次检查任务是否已被取消
            with self.app.app_context():
                current_task = self.task_service.get_task(task_id)
                if current_task and current_task.status == 'cancelled':
                    logger.info(f"🛑 任务 {task_id} 已被取消，停止执行")
                    return
            
            # 读取 JSONL 文件作为结果
            import json
            from pathlib import Path
            
            # JSONL 文件路径 - 从当前文件位置向上查找backend目录
            current_file = Path(__file__).resolve()
            # task_execution_scheduler.py 位于: backend/server/app/services/
            # 向上4级到达 backend 目录
            backend_dir = current_file.parent.parent.parent.parent
            jsonl_file_path = backend_dir / 'result' / 'codebert_clone-detection_itgen_test_sampled_50.txt.jsonl'
            
            # 如果文件不存在，尝试使用绝对路径
            if not jsonl_file_path.exists():
                jsonl_file_path = Path('/home/king/project/ITGen/backend/result/codebert_clone-detection_itgen_test_sampled_50.txt.jsonl')
            
            if not jsonl_file_path.exists():
                logger.error(f"❌ JSONL文件不存在: {jsonl_file_path}")
                raise FileNotFoundError(f"JSONL文件不存在: {jsonl_file_path}")
            
            logger.info(f"📖 读取JSONL文件: {jsonl_file_path}")
            
            # 读取并解析 JSONL 文件
            results = []
            total_samples = 0
            successful_samples = 0
            failed_samples = 0
            
            with open(jsonl_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        result_item = json.loads(line)
                        results.append(result_item)
                        total_samples += 1
                        
                        # 统计成功和失败的样本
                        result_type = result_item.get('Type', '0')
                        if result_type == '0':
                            failed_samples += 1
                        else:
                            successful_samples += 1
                    except json.JSONDecodeError as e:
                        logger.warning(f"文件第 {line_num} 行解析JSON失败: {e}")
            
            logger.info(f"✅ 成功读取 {len(results)} 条结果记录")
            logger.info(f"📊 统计: 总计={total_samples}, 成功={successful_samples}, 失败={failed_samples}")
            
            # 构建结果数据
            result = {
                'success': True,
                'total_samples': total_samples,
                'successful_samples': successful_samples,
                'failed_samples': failed_samples,
                'success_rate': round((successful_samples / total_samples * 100), 2) if total_samples > 0 else 0,
                'results': results,  # 包含所有 JSONL 文件中的结果
                'result_file': jsonl_file_path.name,
                'model_name': task.model_name or parameters.get('model_name', 'codebert'),
                'task_type': parameters.get('test_type', 'clone-detection'),
                'attack_method': parameters.get('attack_method', 'itgen'),
                'note': f'批量测试结果来自文件: {jsonl_file_path.name}'
            }
            
            # 更新任务为完成状态
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='completed',
                    progress=100,
                    progress_message='批量测试完成',
                    result=result
                )
            
            logger.info(f"✅ 批量测试任务 {task_id} 执行完成，共处理 {total_samples} 个样本")

        except Exception as e:
            logger.error(f"批量测试任务 {task_id} 执行失败: {e}", exc_info=True)
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='failed',
                    progress=0,
                    progress_message=f'批量测试失败: {str(e)}',
                    result={'success': False, 'error': str(e)}
                )
            raise

    def _execute_evaluation_task(self, task):
        """执行评估任务"""
        task_id = task.id
        logger.info(f"📈 执行评估任务 {task_id}")

        try:
            parameters = task.parameters or {}
            model_name = task.model_name or parameters.get('model_name', 'codebert')
            task_type = parameters.get('task_type', 'clone-detection')
            attack_methods = parameters.get('attack_methods', ['itgen', 'alert'])
            
            logger.info(f"📊 评估参数: model={model_name}, task_type={task_type}, methods={attack_methods}")
            
            # 更新进度
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='running',
                    progress=20,
                    progress_message='正在读取结果文件...'
                )
            
            # 检查任务是否被取消
            with self.app.app_context():
                updated_task = self.task_service.get_task(task_id)
                if updated_task and updated_task.status == 'cancelled':
                    logger.info(f"⚠️ 任务 {task_id} 已被取消，停止执行")
                    return
            
            # 生成静态评估报告数据（不执行真实算法）
            logger.info(f"📊 生成静态评估报告数据...")
            
            # 更新进度
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='running',
                    progress=50,
                    progress_message='正在生成评估报告...'
                )
            
            # 直接生成静态评估数据
            static_report = self._generate_static_evaluation_report(
                model_name=model_name,
                task_type=task_type,
                attack_methods=attack_methods
            )
            result = {
                'success': True,
                'report_id': static_report['report_id'],
                'report': static_report
            }
            
            logger.info(f"📊 evaluation_service返回结果: success={result.get('success')}, error={result.get('error', 'None')}")
            
            # 检查任务是否被取消
            with self.app.app_context():
                updated_task = self.task_service.get_task(task_id)
                if updated_task and updated_task.status == 'cancelled':
                    logger.info(f"⚠️ 任务 {task_id} 已被取消，停止执行")
                    return
            
            if result.get('success'):
                logger.info(f"✅ 评估报告生成成功，准备保存结果")
                # 更新进度
                with self.app.app_context():
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='running',
                        progress=90,
                        progress_message='正在保存评估结果...'
                    )
                
                # 准备任务结果：直接保存报告数据，包含报告ID
                report_id = result.get('report_id')
                report_data = result.get('report', {})

                # 将报告ID添加到报告数据中，方便前端获取
                report_data['report_id'] = report_id

                # 保存报告数据到任务result字段
                with self.app.app_context():
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='completed',
                        progress=100,
                        progress_message='评估任务完成',
                        result=report_data
                    )
                
                logger.info(f"✅ 评估任务 {task_id} 执行完成，报告ID: {report_id}")
            else:
                raise Exception(result.get('error', '评估失败'))
                
        except Exception as e:
            logger.error(f"❌ 评估任务 {task_id} 执行失败: {e}", exc_info=True)
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='failed',
                    progress=0,
                    progress_message=f'评估失败: {str(e)}',
                    result={'success': False, 'error': str(e)}
                )

    def _generate_static_evaluation_report(self, model_name: str, task_type: str, attack_methods: List[str]) -> Dict[str, Any]:
        """生成静态评估报告数据"""
        from datetime import datetime
        import uuid

        # 生成报告ID
        report_id = f"{model_name}_{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 静态数据：模拟两种攻击方法的评估结果
        static_data = {
            'itgen': {
                'total_samples': 100,
                'successful_attacks': 45,
                'failed_attacks': 55,
                'asr': 45.0,  # 攻击成功率
                'ami': 8.5,   # 平均模型调用次数
                'art': 12.3,  # 平均响应时间(分钟)
                'avg_program_length': 145.6,
                'avg_identifiers': 7.2
            },
            'alert': {
                'total_samples': 50,
                'successful_attacks': 8,
                'failed_attacks': 42,
                'asr': 16.0,
                'ami': 15.2,
                'art': 18.7,
                'avg_program_length': 152.3,
                'avg_identifiers': 6.8
            }
        }

        # 计算总体统计
        total_samples = sum(static_data[method]['total_samples'] for method in attack_methods if method in static_data)
        successful_attacks = sum(static_data[method]['successful_attacks'] for method in attack_methods if method in static_data)
        failed_attacks = sum(static_data[method]['failed_attacks'] for method in attack_methods if method in static_data)

        # 加权平均计算总体指标
        overall_asr = successful_attacks / total_samples * 100 if total_samples > 0 else 0
        overall_ami = sum(static_data[method]['ami'] * static_data[method]['total_samples'] for method in attack_methods if method in static_data) / total_samples if total_samples > 0 else 0
        overall_art = sum(static_data[method]['art'] * static_data[method]['total_samples'] for method in attack_methods if method in static_data) / total_samples if total_samples > 0 else 0
        overall_avg_program_length = sum(static_data[method]['avg_program_length'] * static_data[method]['total_samples'] for method in attack_methods if method in static_data) / total_samples if total_samples > 0 else 0
        overall_avg_identifiers = sum(static_data[method]['avg_identifiers'] * static_data[method]['total_samples'] for method in attack_methods if method in static_data) / total_samples if total_samples > 0 else 0

        # 构建method_metrics
        method_metrics = {}
        for method in attack_methods:
            if method in static_data:
                method_metrics[method] = static_data[method].copy()

        # 构建summary_stats
        summary_stats = {
            'total_samples': total_samples,
            'successful_attacks': successful_attacks,
            'failed_attacks': failed_attacks,
            'asr': round(overall_asr, 2),
            'ami': round(overall_ami, 2),
            'art': round(overall_art, 2),
            'avg_program_length': round(overall_avg_program_length, 2),
            'avg_identifiers': round(overall_avg_identifiers, 2)
        }

        # 生成模拟的sample_results（成功的攻击样本）
        sample_results = []
        sample_data = [
            {
                'Index': 3,
                'Original Code': 'public static boolean encodeFileToFile(String infile, String outfile) {\n    boolean success = false;\n    java.io.InputStream in = null;\n    java.io.OutputStream out = null;\n    try {\n        in = new Base64.InputStream(new java.io.BufferedInputStream(new java.io.FileInputStream(infile)), Base64.ENCODE);\n        out = new java.io.BufferedOutputStream(new java.io.FileOutputStream(outfile));\n        byte[] buffer = new byte[65536];\n        int read = -1;\n        while ((read = in.read(buffer)) >= 0) {\n            out.write(buffer, 0, read);\n        }\n        success = true;\n    } catch (java.io.IOException exc) {\n        exc.printStackTrace();\n    } finally {\n        try {\n            in.close();\n        } catch (Exception e) {\n        }\n        try {\n            out.close();\n        } catch (Exception e) {\n        }\n    }\n    return success;\n}',
                'Adversarial Code': 'public static boolean encodeFileToFile(String url, String class) {\n    boolean success = false;\n    java.io.InputStream in = null;\n    java.io.OutputStream out = null;\n    try {\n        in = new Base64.InputStream(new java.io.BufferedInputStream(new java.io.FileInputStream(url)), Base64.ENCODE);\n        out = new java.io.BufferedOutputStream(new java.io.FileOutputStream(class));\n        byte[] buffer = new byte[65536];\n        int read = -1;\n        while ((read = in.read(buffer)) >= 0) {\n            out.write(buffer, 0, read);\n        }\n        success = true;\n    } catch (java.io.IOException exc) {\n        exc.printStackTrace();\n    } finally {\n        try {\n            in.close();\n        } catch (Exception e) {\n        }\n        try {\n            out.close();\n        } catch (Exception e) {\n        }\n    }\n    return success;\n}',
                'Program Length': 756,
                'Identifier Num': 10,
                'Replaced Identifiers': 'dest:class,out:out,format:url,p:wp,ds:icks,src:url,',
                'Query Times': 269,
                'Time Cost': 0.2611870328585307,
                'Type': 'Greedy'
            }
        ]

        # 根据选择的攻击方法添加对应的样本
        for method in attack_methods:
            if method == 'alert' and 'alert' in attack_methods:
                sample_results.extend(sample_data)
            elif method == 'itgen' and 'itgen' in attack_methods:
                # 为itgen方法生成类似的样本
                itgen_sample = sample_data[0].copy()
                itgen_sample['Type'] = 'itgen'
                itgen_sample['Query Times'] = 150
                itgen_sample['Time Cost'] = 0.15
                itgen_sample['Replaced Identifiers'] = 'infile:input_file,outfile:output_file,success:result,'
                sample_results.append(itgen_sample)

        # 限制样本数量
        sample_results = sample_results[:5]

        # 构建完整报告
        report = {
            'report_id': report_id,
            'model_name': model_name,
            'task_type': task_type,
            'attack_methods': attack_methods,
            'evaluation_metrics': ['asr', 'ami', 'art'],
            'method_metrics': method_metrics,
            'summary_stats': summary_stats,
            'sample_results': sample_results,
            'generated_at': datetime.now().isoformat()
        }

        # 保存到评估报告数据库
        try:
            with self.app.app_context():
                from app.models.db_evaluation import EvaluationReport

                # 检查是否已存在相同报告
                existing_report = EvaluationReport.query.filter_by(report_id=report_id).first()
                if existing_report:
                    # 更新现有报告
                    existing_report.asr = summary_stats['asr']
                    existing_report.ami = summary_stats['ami']
                    existing_report.art = summary_stats['art']
                    existing_report.total_samples = total_samples
                    existing_report.successful_attacks = successful_attacks
                    existing_report.failed_attacks = failed_attacks
                    existing_report.avg_program_length = summary_stats['avg_program_length']
                    existing_report.avg_identifiers = summary_stats['avg_identifiers']
                    existing_report.method_metrics = method_metrics
                    existing_report.summary_stats = summary_stats
                    existing_report.sample_results = report['sample_results']
                    db.session.commit()
                    logger.info(f"✅ 更新静态评估报告: {report_id}")
                else:
                    # 创建新报告
                    evaluation_report = EvaluationReport(
                        report_id=report_id,
                        model_name=model_name,
                        task_type=task_type,
                        attack_methods=attack_methods,
                        evaluation_metrics=['asr', 'ami', 'art'],
                        total_samples=total_samples,
                        successful_attacks=successful_attacks,
                        failed_attacks=failed_attacks,
                        asr=summary_stats['asr'],
                        ami=summary_stats['ami'],
                        art=summary_stats['art'],
                        avg_program_length=summary_stats['avg_program_length'],
                        avg_identifiers=summary_stats['avg_identifiers'],
                        method_metrics=method_metrics,
                        summary_stats=summary_stats,
                        sample_results=report['sample_results']
                    )
                    db.session.add(evaluation_report)
                    db.session.commit()
                    logger.info(f"✅ 保存静态评估报告到数据库: {report_id}")

        except Exception as e:
            logger.warning(f"⚠️ 保存静态评估报告到数据库失败（不影响返回结果）: {e}")

        logger.info(f"📊 生成静态评估报告完成: ASR={summary_stats['asr']}%, 总样本={total_samples}, 成功攻击={successful_attacks}")
        return report

    def _execute_finetuning_task(self, task):
        """执行微调任务 - 生成静态数据"""
        task_id = task.id
        logger.info(f"🔧 执行微调任务 {task_id}")

        try:
            parameters = task.parameters or {}
            model_name = task.model_name or parameters.get('model_name', 'codebert')
            task_type = parameters.get('task_type', 'clone-detection')
            
            logger.info(f"📊 微调参数: model={model_name}, task_type={task_type}")
            
            # 模拟进度更新
            progress_steps = [
                (10, '正在加载基础模型...'),
                (30, '正在准备微调数据...'),
                (50, '正在执行微调训练...'),
                (80, '正在评估微调效果...'),
                (95, '正在生成微调报告...'),
                (100, '微调完成')
            ]

            for progress, message_text in progress_steps:
                with self.app.app_context():
                    current_task = self.task_service.get_task(task_id)
                    if current_task and current_task.status == 'cancelled':
                        logger.info(f"🛑 微调任务 {task_id} 已被取消，停止执行")
                        return

                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='running',
                        progress=progress,
                        progress_message=message_text
                    )
                time.sleep(0.3)  # 模拟耗时

            # 再次检查任务是否已被取消
            with self.app.app_context():
                current_task = self.task_service.get_task(task_id)
                if current_task and current_task.status == 'cancelled':
                    logger.info(f"🛑 微调任务 {task_id} 已被取消，停止执行")
                    return

            # 生成静态微调结果
            finetuning_result = self._generate_static_finetuning_report(model_name, task_type)

            # 保存微调结果
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='completed',
                    progress=100,
                    progress_message='微调任务完成',
                    result=finetuning_result
                )
                
            logger.info(f"✅ 微调任务 {task_id} 执行完成")

        except Exception as e:
            logger.error(f"❌ 微调任务 {task_id} 执行失败: {e}", exc_info=True)
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='failed',
                    progress=0,
                    progress_message=f'微调失败: {str(e)}',
                    result={'success': False, 'error': str(e)}
                )

    def _generate_static_finetuning_report(self, model_name: str, task_type: str) -> Dict[str, Any]:
        """生成静态微调报告数据"""
        from datetime import datetime
        import uuid

        # 生成报告ID
        report_id = f"finetune_{model_name}_{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 静态微调结果数据
        finetuning_result = {
            'success': True,
            'model_name': model_name,
            'task_type': task_type,
            'sub_task_type': 'attack_resistance',
            'dataset': 'finetuning-dataset',
            'finetuning_type': 'adversarial_training',
            'training_metrics': {
                'epochs': 10,
                'learning_rate': 0.0001,
                'batch_size': 16,
                'total_samples': 1000,
                'training_time': 45.5,  # 分钟
                'final_loss': 0.023,
                'best_accuracy': 0.965
            },
            'robustness_improvement': {
                'baseline_asr': 35.33,  # 基于评估报告的基线值
                'improved_asr': 18.50,  # 降低约47%
                'improvement': 16.83,   # 百分比点改进
                'resistance_score': 81.5  # 鲁棒性评分
            },
            'attack_method_performance': {
                'itgen': {
                    'before_finetuning': 45.0,
                    'after_finetuning': 22.5,
                    'improvement': 22.5
                },
                'alert': {
                    'before_finetuning': 16.0,
                    'after_finetuning': 6.4,
                    'improvement': 9.6
                }
            },
            'metrics_comparison': {
                'asr': {
                    'before': 35.33,
                    'after': 18.50,
                    'improvement': 16.83
                },
                'ami': {
                    'before': 10.73,
                    'after': 9.85,
                    'change': -0.88
                },
                'art': {
                    'before': 14.43,
                    'after': 13.92,
                    'change': -0.51
                }
            },
            'model_artifacts': {
                'model_path': f'/models/{model_name}_finetuned_{task_type}.pth',
                'checkpoint_path': f'/checkpoints/{model_name}_finetuned_{task_type}_best.pt',
                'config_path': f'/configs/{model_name}_finetuned_{task_type}.json'
            },
            'recommendations': [
                '模型鲁棒性显著提升，建议用于生产环境',
                '建议定期重新微调以应对新的攻击方法',
                '可以考虑进一步优化训练参数以获得更好的性能'
            ],
            'baseline_report_id': f"{model_name}_{task_type}_20250112_000000",  # 模拟基线报告ID
            'generated_at': datetime.now().isoformat(),
            'report_id': report_id
        }
                
        logger.info(f"📊 生成静态微调报告完成: ASR从{finetuning_result['robustness_improvement']['baseline_asr']}%降低到{finetuning_result['robustness_improvement']['improved_asr']}%")
        return finetuning_result

    def _check_timeout_tasks(self):
        """检查并处理超时的任务"""
        current_time = datetime.now()
        timeout_tasks = []

        for task_id, task_info in self.active_tasks.items():
            start_time = task_info['start_time']
            elapsed_time = (current_time - start_time).total_seconds()

            if elapsed_time > self.task_timeout:
                timeout_tasks.append(task_id)
                logger.warning(f"⚠️ 任务 {task_id} 已执行 {elapsed_time:.1f} 秒，超过超时时间 {self.task_timeout} 秒")

        # 处理超时的任务
        for task_id in timeout_tasks:
            try:
                task_info = self.active_tasks[task_id]
                thread = task_info['thread']

                # 强制终止线程（注意：这可能不安全）
                logger.warning(f"🛑 强制终止超时任务 {task_id} 的线程")
                # 注意：Python线程不能被安全地强制终止，这里只是记录状态

                # 更新任务状态为失败
                with self.app.app_context():
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='failed',
                        progress=0,
                        progress_message=f'任务执行超时 ({self.task_timeout}秒)',
                        result={'success': False, 'error': f'任务执行超时 ({self.task_timeout}秒)'}
                    )

                # 从活动任务中移除
                del self.active_tasks[task_id]
                logger.info(f"✅ 已清理超时任务 {task_id}")

            except Exception as e:
                logger.error(f"处理超时任务 {task_id} 时出错: {e}")

    def _cleanup_completed_threads(self):
        """清理已完成的线程"""
        completed_task_ids = []
        stuck_task_ids = []

        for task_id, task_info in self.active_tasks.items():
            thread = task_info['thread']

            if not thread.is_alive():
                # 线程已死亡，检查任务状态
                try:
                    with self.app.app_context():
                        task = self.task_service.get_task(task_id)
                        if task:
                            # 如果任务状态仍然是running，说明执行过程中出现了异常
                            if task.status == 'running':
                                logger.warning(f"⚠️ 任务 {task_id} 线程已死亡但状态仍为running，标记为失败")
                                stuck_task_ids.append(task_id)
                                continue

                except Exception as e:
                    logger.error(f"检查任务 {task_id} 状态时出错: {e}")

                completed_task_ids.append(task_id)
                logger.debug(f"清理已完成的任务线程: {task_id}")
            else:
                # 线程仍然存活，检查是否卡住
                start_time = task_info['start_time']
                elapsed_time = (datetime.now() - start_time).total_seconds()

                if elapsed_time > 300:  # 5分钟没有进度更新
                    logger.warning(f"⚠️ 任务 {task_id} 已执行 {elapsed_time:.1f} 秒，可能卡住")

        # 处理卡住的任务
        for task_id in stuck_task_ids:
            try:
                with self.app.app_context():
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='failed',
                        progress=0,
                        progress_message='任务执行异常中断',
                        result={'success': False, 'error': '任务执行异常中断'}
                    )
                logger.info(f"✅ 已标记卡住任务 {task_id} 为失败")
            except Exception as e:
                logger.error(f"处理卡住任务 {task_id} 时出错: {e}")

        # 移除已完成的线程
        for task_id in completed_task_ids:
            del self.active_tasks[task_id]

    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        active_task_details = []
        for task_id, task_info in self.active_tasks.items():
            elapsed_time = (datetime.now() - task_info['start_time']).total_seconds()
            active_task_details.append({
                'task_id': task_id,
                'task_type': task_info['task_type'],
                'start_time': task_info['start_time'].isoformat(),
                'elapsed_seconds': round(elapsed_time, 1),
                'thread_alive': task_info['thread'].is_alive(),
                'thread_name': task_info['thread'].name
            })

        return {
            'running': self.running,
            'active_tasks_count': len(self.active_tasks),
            'active_task_ids': list(self.active_tasks.keys()),
            'active_task_details': active_task_details,
            'check_interval': self.check_interval,
            'task_timeout': self.task_timeout
        }

    def cancel_task(self, task_id: str, reason: str = "用户取消") -> bool:
        """
        取消任务执行

        Args:
            task_id: 任务ID
            reason: 取消原因

        Returns:
            是否成功取消
        """
        try:
            # 如果任务在活跃列表中，移除它
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id]
                thread = task_info['thread']

                # 注意：Python线程不能被安全地强制终止
                logger.info(f"标记任务 {task_id} 为取消状态 (线程: {thread.name})")
                del self.active_tasks[task_id]

            # 更新任务状态
            with self.app.app_context():
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='cancelled',
                        progress=0,
                    progress_message=reason,
                    result={'success': False, 'error': reason}
                    )

            logger.info(f"✅ 任务 {task_id} 已取消: {reason}")
            return True

        except Exception as e:
            logger.error(f"取消任务 {task_id} 时出错: {e}")
            return False
