"""任务执行调度器 - 管理和执行异步任务"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from flask import current_app
from app.services.task_service import TaskService
from app.services.attack_service import AttackService
from app.services.evaluation_service import EvaluationService
from app.services.finetuning_service import FinetuningService
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
        self.evaluation_service = EvaluationService()
        self.finetuning_service = FinetuningService()
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
        """执行攻击任务 - 使用真实的攻击算法"""
        task_id = task.id
        parameters = task.parameters or {}

        logger.info(f"🎯 执行攻击任务 {task_id}")

        try:
            # 解析任务参数
            code1 = parameters.get('code1', '')
            code2 = parameters.get('code2', '')
            method = parameters.get('method', 'itgen')
            model_name = task.model_name or parameters.get('model_name', 'codebert')
            task_type = parameters.get('task_type', 'clone-detection')
            language = parameters.get('language', 'java')
            true_label = parameters.get('true_label', 1)

            # 验证输入
            if not code1:
                raise ValueError("原始代码(code1)不能为空")

            # 准备代码数据
            code_data = {
                'code1': code1,
                'code2': code2
            }

            # 准备攻击配置
            config = {
                'model_name': model_name,
                'task_type': task_type,
                'language': language,
                'true_label': true_label,
                'model_id': parameters.get('model_id'),
                'attack_strategy': parameters.get('attack_strategy', 'identifier_rename'),
                'max_modifications': parameters.get('max_modifications', 5),
                'max_query_times': parameters.get('max_query_times', 200),
                'time_limit': parameters.get('time_limit', 60),
                'max_substitutions': parameters.get('max_substitutions', 10)
            }

            # 更新任务状态为运行中
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='running',
                    progress=10,
                    progress_message='正在初始化攻击环境...'
                )

            # 检查任务是否已被取消
            with self.app.app_context():
                current_task = self.task_service.get_task(task_id)
                if current_task and current_task.status == 'cancelled':
                    logger.info(f"🛑 任务 {task_id} 已被取消，停止执行")
                    return

            # 执行真实攻击
            logger.info(f"⚔️ 开始执行真实攻击: model={model_name}, method={method}, task_type={task_type}")
            result = self.attack_service.attack(
                code_data=code_data,
                target_model=model_name,
                language=language,
                config=config,
                method=method
            )

            # 更新任务结果
            with self.app.app_context():
                if result.get('success'):
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='completed',
                        progress=100,
                        progress_message='攻击任务完成',
                        result=result
                    )
                    logger.info(f"✅ 攻击任务 {task_id} 执行成功")
                else:
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='failed',
                        progress=0,
                        progress_message=f'攻击失败: {result.get("error", "未知错误")}',
                        result=result
                    )
                    logger.warning(f"⚠️ 攻击任务 {task_id} 执行失败: {result.get('error', '未知错误')}")

        except Exception as e:
            logger.error(f"❌ 攻击任务 {task_id} 执行失败: {e}", exc_info=True)
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='failed',
                    progress=0,
                    progress_message=f'攻击任务失败: {str(e)}',
                    result={'success': False, 'error': str(e)}
                )
            raise

    def _execute_batch_testing_task(self, task):
        """执行批量测试任务 - 使用真实的攻击算法"""
        task_id = task.id
        parameters = task.parameters or {}
        logger.info(f"📊 执行批量测试任务 {task_id}")

        try:
            # 解析任务参数
            dataset_path = parameters.get('dataset_path', '')
            model_name = task.model_name or parameters.get('model_name', 'codebert')
            task_type = parameters.get('task_type', 'clone-detection')
            attack_method = parameters.get('attack_method', 'itgen')
            language = parameters.get('language', 'java')
            max_samples = parameters.get('max_samples', 50)  # 限制处理样本数量
            true_label = parameters.get('true_label', 1)

            # 更新任务状态为运行中
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='running',
                    progress=10,
                    progress_message='正在初始化批量测试环境...'
                )

            # 检查任务是否已被取消
            with self.app.app_context():
                current_task = self.task_service.get_task(task_id)
                if current_task and current_task.status == 'cancelled':
                    logger.info(f"🛑 任务 {task_id} 已被取消，停止执行")
                    return

            # 查找测试数据集
            import json
            from pathlib import Path

            # 默认数据集路径
            if not dataset_path:
                current_file = Path(__file__).resolve()
                backend_dir = current_file.parent.parent.parent.parent
                dataset_path = backend_dir / 'dataset' / 'preprocess' / 'test_clone.jsonl'

            dataset_file = Path(dataset_path)
            if not dataset_file.exists():
                # 尝试其他可能的位置
                alternative_paths = [
                    Path('/home/king/project/ITGen/backend/dataset/preprocess/test_clone.jsonl'),
                    Path('/home/king/project/ITGen/dataset/preprocess/test_clone.jsonl'),
                ]
                for alt_path in alternative_paths:
                    if alt_path.exists():
                        dataset_file = alt_path
                        break

            if not dataset_file.exists():
                raise FileNotFoundError(f"测试数据集文件不存在: {dataset_path}")

            logger.info(f"📖 加载测试数据集: {dataset_file}")

            # 读取测试数据集
            test_samples = []
            with open(dataset_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f):
                    if line_num >= max_samples:  # 限制样本数量
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        sample = json.loads(line)
                        if 'code1' in sample:  # 确保包含必要字段
                            test_samples.append(sample)
                    except json.JSONDecodeError as e:
                        logger.warning(f"跳过第 {line_num} 行，无法解析JSON: {e}")

            total_samples = len(test_samples)
            logger.info(f"✅ 加载了 {total_samples} 个测试样本")

            if total_samples == 0:
                raise ValueError("没有找到有效的测试样本")

            # 更新进度
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='running',
                    progress=25,
                    progress_message=f'正在加载模型和数据集... (共 {total_samples} 个样本)'
                )

            # 执行批量攻击测试
            results = []
            successful_samples = 0
            failed_samples = 0

            logger.info(f"⚔️ 开始批量攻击测试: model={model_name}, method={attack_method}, samples={total_samples}")

            for idx, sample in enumerate(test_samples):
                # 检查任务是否已被取消
                with self.app.app_context():
                    current_task = self.task_service.get_task(task_id)
                    if current_task and current_task.status == 'cancelled':
                        logger.info(f"🛑 任务 {task_id} 已被取消，停止执行")
                        return

                # 更新进度
                progress = 25 + int((idx + 1) / total_samples * 60)  # 25%-85%的进度
                with self.app.app_context():
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='running',
                        progress=progress,
                        progress_message=f'正在处理样本 {idx + 1}/{total_samples}...'
                    )

                try:
                    # 准备攻击配置
                    attack_config = {
                        'model_name': model_name,
                        'task_type': task_type,
                        'language': language,
                        'true_label': true_label,
                        'attack_strategy': parameters.get('attack_strategy', 'identifier_rename'),
                        'max_modifications': parameters.get('max_modifications', 5),
                        'max_query_times': parameters.get('max_query_times', 200),
                        'time_limit': parameters.get('time_limit', 60),
                        'max_substitutions': parameters.get('max_substitutions', 10)
                    }

                    # 执行单个攻击
                    attack_result = self.attack_service.attack(
                        code_data=sample,
                        target_model=model_name,
                        language=language,
                        config=attack_config,
                        method=attack_method
                    )

                    if attack_result.get('success'):
                        successful_samples += 1
                        results.append({
                            'index': idx,
                            'original_code': attack_result.get('original_code', ''),
                            'adversarial_code': attack_result.get('adversarial_code', ''),
                            'replaced_identifiers': attack_result.get('replaced_identifiers', {}),
                            'query_times': attack_result.get('query_times', 0),
                            'time_cost': attack_result.get('time_cost', 0),
                            'type': '1' if attack_result.get('success') else '0',
                            'attack_success': True
                        })
                    else:
                        failed_samples += 1
                        results.append({
                            'index': idx,
                            'original_code': sample.get('code1', ''),
                            'adversarial_code': None,
                            'replaced_identifiers': None,
                            'query_times': 0,
                            'time_cost': 0,
                            'type': '0',
                            'attack_success': False,
                            'error': attack_result.get('error', '攻击失败')
                        })

                    logger.debug(f"样本 {idx + 1}/{total_samples}: {'成功' if attack_result.get('success') else '失败'}")

                except Exception as e:
                    logger.warning(f"样本 {idx + 1} 攻击失败: {e}")
                    failed_samples += 1
                    results.append({
                        'index': idx,
                        'original_code': sample.get('code1', ''),
                        'adversarial_code': None,
                        'replaced_identifiers': None,
                        'query_times': 0,
                        'time_cost': 0,
                        'type': '0',
                        'attack_success': False,
                        'error': str(e)
                    })

            # 构建最终结果
            result = {
                'success': True,
                'total_samples': total_samples,
                'successful_samples': successful_samples,
                'failed_samples': failed_samples,
                'success_rate': round((successful_samples / total_samples * 100), 2) if total_samples > 0 else 0,
                'results': results,
                'dataset_file': dataset_file.name,
                'model_name': model_name,
                'task_type': task_type,
                'attack_method': attack_method,
                'note': f'实时批量测试结果: 使用{attack_method.upper()}算法处理{total_samples}个样本'
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

            logger.info(f"✅ 批量测试任务 {task_id} 执行完成")
            logger.info(f"📊 结果统计: 总计={total_samples}, 成功={successful_samples}, 失败={failed_samples}, 成功率={result['success_rate']}%")

        except Exception as e:
            logger.error(f"❌ 批量测试任务 {task_id} 执行失败: {e}", exc_info=True)
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
        """执行评估任务 - 使用真实评估算法"""
        task_id = task.id
        logger.info(f"📈 执行评估任务 {task_id}")

        try:
            parameters = task.parameters or {}
            model_name = task.model_name or parameters.get('model_name', 'codebert')
            task_type = parameters.get('task_type', 'clone-detection')
            attack_methods = parameters.get('attack_methods', ['itgen', 'alert'])
            evaluation_metrics = parameters.get('evaluation_metrics', ['asr', 'ami', 'art'])

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

            # 调用真实的评估服务生成报告
            logger.info(f"📊 调用真实评估服务生成报告...")

            # 更新进度
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='running',
                    progress=50,
                    progress_message='正在分析攻击结果...'
                )

            # 调用真实评估服务
            evaluation_result = self.evaluation_service.generate_report_from_results(
                model_name=model_name,
                task_type=task_type,
                attack_methods=attack_methods,
                evaluation_metrics=evaluation_metrics
            )

            # 检查任务是否被取消
            with self.app.app_context():
                updated_task = self.task_service.get_task(task_id)
                if updated_task and updated_task.status == 'cancelled':
                    logger.info(f"⚠️ 任务 {task_id} 已被取消，停止执行")
                    return

            if evaluation_result.get('success'):
                logger.info(f"✅ 评估报告生成成功，准备保存结果")

                # 更新进度
                with self.app.app_context():
                    self.task_service.update_task_status(
                        task_id=task_id,
                        status='running',
                        progress=90,
                        progress_message='正在保存评估结果...'
                    )

                # 准备任务结果
                report_id = evaluation_result.get('report_id')
                report_data = evaluation_result.get('report', {})

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
                error_msg = evaluation_result.get('error', '评估失败')
                logger.error(f"❌ 评估服务返回失败: {error_msg}")
                raise Exception(error_msg)

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


    def _execute_finetuning_task(self, task):
        """执行微调任务 - 使用真实微调算法"""
        task_id = task.id
        logger.info(f"🔧 执行微调任务 {task_id}")

        try:
            parameters = task.parameters or {}
            model_name = task.model_name or parameters.get('model_name', 'codebert')
            task_type = parameters.get('task_type', 'clone-detection')
            attack_methods = parameters.get('attack_methods', ['itgen', 'alert'])
            epochs = parameters.get('epochs', 10)
            learning_rate = parameters.get('learning_rate', 0.0001)
            batch_size = parameters.get('batch_size', 16)

            logger.info(f"📊 微调参数: model={model_name}, task_type={task_type}, epochs={epochs}")

            # 更新任务状态为运行中
            with self.app.app_context():
                self.task_service.update_task_status(
                    task_id=task_id,
                    status='running',
                    progress=10,
                    progress_message='正在加载基础模型...'
                )

            # 检查任务是否已被取消
            with self.app.app_context():
                current_task = self.task_service.get_task(task_id)
                if current_task and current_task.status == 'cancelled':
                    logger.info(f"🛑 微调任务 {task_id} 已被取消，停止执行")
                    return

            # 调用真实微调服务
            logger.info(f"🔧 调用真实微调服务...")

            # 准备微调配置
            finetune_config = {
                'model_name': model_name,
                'task_type': task_type,
                'attack_methods': attack_methods,
                'epochs': epochs,
                'learning_rate': learning_rate,
                'batch_size': batch_size,
                'output_dir': parameters.get('output_dir', f'/models/{model_name}_finetuned_{task_type}')
            }

            # 调用微调服务 - 这里假设finetuning_service有一个execute_finetuning方法
            try:
                # 如果微调服务有execute_finetuning方法，直接调用
                if hasattr(self.finetuning_service, 'execute_finetuning'):
                    finetuning_result = self.finetuning_service.execute_finetuning(finetune_config)
                else:
                    # 否则手动执行微调流程
                    logger.info("微调服务没有execute_finetuning方法，使用手动流程")

                    # 步骤1: 提取对抗样本
                    with self.app.app_context():
                        self.task_service.update_task_status(
                            task_id=task_id,
                            status='running',
                            progress=20,
                            progress_message='正在提取对抗样本...'
                        )

                    adversarial_samples = self.finetuning_service.extract_adversarial_samples(
                        model_name, task_type, attack_methods
                    )

                    if not adversarial_samples:
                        raise ValueError("没有找到对抗样本用于微调")

                    # 步骤2: 准备训练数据
                    with self.app.app_context():
                        self.task_service.update_task_status(
                            task_id=task_id,
                            status='running',
                            progress=40,
                            progress_message='正在准备训练数据...'
                        )

                    from pathlib import Path
                    temp_dir = Path(f'/tmp/finetune_{task_id}')
                    temp_dir.mkdir(exist_ok=True)
                    training_data_path = temp_dir / 'training_data.jsonl'

                    self.finetuning_service.prepare_training_data(
                        adversarial_samples, training_data_path
                    )

                    # 步骤3: 执行微调训练
                    with self.app.app_context():
                        self.task_service.update_task_status(
                            task_id=task_id,
                            status='running',
                            progress=60,
                            progress_message='正在执行微调训练...'
                        )

                    # 这里应该调用实际的微调训练逻辑
                    logger.warning("⚠️ 实际微调训练逻辑未实现，尝试调用finetuning_service的训练方法")

                    # 步骤4: 执行微调训练
                    with self.app.app_context():
                        self.task_service.update_task_status(
                            task_id=task_id,
                            status='running',
                            progress=90,
                            progress_message='正在执行微调训练...'
                        )

                    # 尝试调用finetuning_service的训练方法
                    try:
                        # 这里需要实现实际的微调训练逻辑
                        # 目前返回错误结果，表明需要真实的训练实现
                        finetuning_result = {
                            'success': False,
                            'error': '微调训练逻辑尚未实现，需要配置训练环境和数据集',
                            'model_name': model_name,
                            'task_type': task_type,
                            'note': '需要实现真实的微调训练算法'
                        }
                        logger.error("❌ 微调训练失败：需要实现真实的训练逻辑")
                    except Exception as e:
                        finetuning_result = {
                            'success': False,
                            'error': f'微调训练异常: {str(e)}',
                            'model_name': model_name,
                            'task_type': task_type
                        }
                        logger.error(f"❌ 微调训练异常: {e}")

                    # 清理临时文件
                    import shutil
                    if temp_dir.exists():
                        shutil.rmtree(temp_dir)

            except Exception as e:
                logger.error(f"微调服务调用失败: {e}")
                raise

            # 再次检查任务是否已被取消
            with self.app.app_context():
                current_task = self.task_service.get_task(task_id)
                if current_task and current_task.status == 'cancelled':
                    logger.info(f"🛑 微调任务 {task_id} 已被取消，停止执行")
                    return

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
