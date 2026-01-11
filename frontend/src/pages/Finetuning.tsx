import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  message,
  Space,
  Typography,
  Row,
  Col,
  Progress,
  Alert,
  Divider,
  Tag,
  Statistic,
  Descriptions,
  Tabs,
  Timeline,
  Badge,
  Empty,
  Spin
} from 'antd';
import {
  PlayCircleOutlined,
  StopOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  TrophyOutlined,
  BugOutlined,
  EyeOutlined,
  FileTextOutlined,
  UploadOutlined,
  CodeOutlined,
  SettingOutlined,
  AppstoreOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { apiService as ApiService } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

interface TaskInfo {
  id: string;
  task_type: string;
  sub_task_type: string;
  status: string;
  progress: number;
  progress_message?: string;
  result?: any;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  metrics?: any;
}

interface TrainingData {
  id: string;
  original_code: string;
  adversarial_code: string;
  label: string;
  difficulty: 'easy' | 'medium' | 'hard';
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

interface TrainingConfig {
  model_id: string;
  base_model: string;
  learning_rate: number;
  batch_size: number;
  epochs: number;
  warmup_steps: number;
  max_length: number;
  adversarial_ratio: number;
  augmentation_strategies: string[];
}

interface TrainingProgress {
  current_epoch: number;
  total_epochs: number;
  current_step: number;
  total_steps: number;
  loss: number;
  accuracy: number;
  learning_rate: number;
  eta: string;
}

interface FinetuningResult {
  model_id: string;
  model_name: string;
  training_time: number;
  final_loss: number;
  // 微调前性能
  original_accuracy: number;
  original_bleu_score: number;
  original_asr: number;
  original_ami: number;
  original_art: number;
  // 微调后性能
  final_accuracy: number;
  final_bleu_score: number;
  final_asr: number;
  final_ami: number;
  final_art: number;
  adversarial_accuracy: number;
  adversarial_bleu_score: number;
  // 性能提升
  accuracy_improvement: number;
  bleu_improvement: number;
  asr_improvement: number;
  ami_improvement: number;
  art_improvement: number;
  overall_improvement: number;
  model_path: string;
  training_logs: any[];
  training_samples: number;
  evaluation_samples: number;
}

const Finetuning: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  // 状态管理
  const [models, setModels] = useState<any[]>([]);
  const [supportedMethods, setSupportedMethods] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskInfo, setTaskInfo] = useState<TaskInfo | null>(null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
  const [finetuningHistory, setFinetuningHistory] = useState<TaskInfo[]>([]);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<string>('');
  const [uploadedFile, setUploadedFile] = useState<any>(null);
  const [trainingData, setTrainingData] = useState<any[]>([]);
  const [trainingProgress, setTrainingProgress] = useState<any>(null);
  const [trainingRunning, setTrainingRunning] = useState(false);
  const [trainingComplete, setTrainingComplete] = useState(false);
  const [trainingConfig, setTrainingConfig] = useState<any>(null);
  const [finetuningResult, setFinetuningResult] = useState<any>(null);
  const [currentStep, setCurrentStep] = useState(0);

  // 初始化数据
  useEffect(() => {
    fetchInitialData();
    fetchFinetuningHistory();
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, []);

  const fetchInitialData = async () => {
    try {
      // 并行获取数据
      const [modelsResponse, methodsResponse] = await Promise.all([
        ApiService.getModels(),
        ApiService.getSupportedAttackMethods()
      ]);

      if (modelsResponse.success) {
        setModels(modelsResponse.data);
      }

      if (methodsResponse.success) {
        setSupportedMethods(methodsResponse.methods || []);
      }
    } catch (error) {
      console.error('Error fetching initial data:', error);
      message.error('加载数据失败');
    }
  };

  const fetchFinetuningHistory = async () => {
    try {
      const response = await ApiService.getTasks({
        task_type: 'finetune',
        limit: 10
      });
      if (response.success) {
        setFinetuningHistory(response.tasks || []);
      }
    } catch (error) {
      console.error('Error fetching finetuning history:', error);
    }
  };

  // 开始微调
  const handleStartFinetuning = async (values: any) => {
    setLoading(true);

    try {
      // 构造请求数据
      const finetuningData = {
        model_name: values.model_name,
        task_type: values.task_type || 'clone-detection',
        dataset: values.dataset,
        attack_methods: values.attack_methods || ['itgen'],
        sub_task_type: values.sub_task_type || 'attack_resistance',
        parameters: {
          learning_rate: parseFloat(values.learning_rate) || 2e-5,
          epochs: parseInt(values.epochs) || 3,
          batch_size: parseInt(values.batch_size) || 16,
          max_queries: parseInt(values.max_queries) || 100
        }
      };

      console.log('🚀 启动微调任务:', finetuningData);

      // 调用后端API启动微调任务
      const response = await ApiService.startFinetuning(finetuningData);
      if (response.success) {
        message.success('微调任务已成功启动！');
        const taskId = response.task_id;
        setTaskInfo({
          id: taskId,
          task_type: 'finetune',
          sub_task_type: values.sub_task_type,
          status: 'running',
          progress: 0,
          progress_message: '任务已创建，等待执行...',
          created_at: new Date().toISOString()
        });
        startTaskPolling(taskId);
      } else {
        message.error(`启动微调任务失败: ${response.error || '未知错误'}`);
      }
    } catch (error: any) {
      console.error('微调启动失败:', error);
      message.error(`微调启动失败: ${error.message || '未知错误'}`);
    } finally {
      setLoading(false);
    }
  };

  // 开始轮询任务状态
  const startTaskPolling = useCallback((taskId: string) => {
    // 清除之前的轮询
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }

    let currentInterval: NodeJS.Timeout | null = null;
    let isPolling = true; // 标记是否应该继续轮询

    const poll = async () => {
      if (!isPolling) {
        return; // 如果已经停止轮询，直接返回
      }

      try {
        const response = await ApiService.getFinetuningStatus(taskId);
        
        // 检查任务是否存在
        if (response.isTaskNotFound || (!response.success && response.error === '任务不存在')) {
          console.log('⚠️ 任务不存在，停止轮询');
          isPolling = false;
          if (currentInterval) {
            clearInterval(currentInterval);
            currentInterval = null;
          }
          setPollingInterval(null);
          setTaskInfo(null);
          message.warning('任务不存在，已停止轮询');
          return;
        }
        
        if (response.success && response.status) {
          const updatedTask = response.status;
          setTaskInfo(updatedTask);

          // 检查任务是否完成
          if (['completed', 'failed', 'cancelled'].includes(updatedTask.status)) {
            isPolling = false; // 停止轮询
            if (currentInterval) {
              clearInterval(currentInterval);
              currentInterval = null;
            }
            setPollingInterval(null);

            if (updatedTask.status === 'completed') {
              message.success('微调任务已完成！');
            } else if (updatedTask.status === 'failed') {
              message.error(`微调任务失败: ${updatedTask.error_message || '未知错误'}`);
            }

            // 刷新历史记录
            fetchFinetuningHistory();
            return; // 任务完成，不再继续轮询
          }
        }
      } catch (error: any) {
        // 如果是404错误（任务不存在），停止轮询
        if (error.response && error.response.status === 404) {
          console.log('⚠️ 任务不存在（404），停止轮询');
          isPolling = false;
          if (currentInterval) {
            clearInterval(currentInterval);
            currentInterval = null;
          }
          setPollingInterval(null);
          setTaskInfo(null);
          message.warning('任务不存在，已停止轮询');
          return;
        }
        console.error('轮询任务状态失败:', error);
      }
    };

    // 立即执行一次，然后每2秒轮询一次
    poll();
    currentInterval = setInterval(() => {
      if (isPolling) {
        poll();
      } else {
        if (currentInterval) {
          clearInterval(currentInterval);
          currentInterval = null;
        }
      }
    }, 2000);
    setPollingInterval(currentInterval);
  }, [pollingInterval]);

  // 取消任务
  const handleCancelTask = async () => {
    if (!taskInfo) return;

    try {
      const response = await ApiService.cancelTask(taskInfo.id, '用户主动取消');
      if (response.success) {
        message.success('任务已取消');
        setTaskInfo(prev => prev ? { ...prev, status: 'cancelled' } : null);
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
      } else {
        message.error('取消任务失败');
      }
    } catch (error) {
      message.error('取消任务失败');
    }
  };

  // 获取状态图标和颜色
  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'pending':
        return { icon: <ClockCircleOutlined />, color: 'orange', text: '等待中' };
      case 'running':
        return { icon: <PlayCircleOutlined />, color: 'blue', text: '训练中' };
      case 'completed':
        return { icon: <CheckCircleOutlined />, color: 'green', text: '已完成' };
      case 'failed':
        return { icon: <CloseCircleOutlined />, color: 'red', text: '失败' };
      case 'cancelled':
        return { icon: <StopOutlined />, color: 'gray', text: '已取消' };
      default:
        return { icon: <ClockCircleOutlined />, color: 'default', text: status };
    }
  };

  // 查看结果
  const handleViewResult = () => {
    if (taskInfo && taskInfo.result) {
      navigate('/finetuning/result', {
        state: {
          taskId: taskInfo.id,
          result: taskInfo.result,
          taskInfo: taskInfo
        }
      });
    }
  };

  // 获取微调结果
  const fetchFinetuningResults = async (taskId: string) => {
    try {
      console.log('📥 获取微调结果，taskId:', taskId);
      const resultsResponse = await ApiService.getFinetuningResults(taskId);

      console.log('📦 后端返回的结果:', resultsResponse);

      if (resultsResponse.success && resultsResponse.result) {
        const backendResult = resultsResponse.result;

        // 转换为前端使用的格式
        const result: any = {
          model_id: backendResult.task_id || taskId,
          model_name: backendResult.model_name || '微调模型',
          training_time: backendResult.training_time || 0,
          final_loss: backendResult.final_loss || 0,

          // 微调前性能（从old_metrics获取）
          original_accuracy: 0, // 后端未提供
          original_bleu_score: 0, // 后端未提供
          original_asr: backendResult.old_metrics?.asr || 0,
          original_ami: backendResult.old_metrics?.ami || 0,
          original_art: backendResult.old_metrics?.art || 0,

          // 微调后性能
          final_accuracy: 0, // 后端未提供
          final_bleu_score: 0, // 后端未提供
          final_asr: 0,
          final_ami: 0,
          final_art: 0,

          // 性能提升
          accuracy_improvement: 0,
          bleu_improvement: 0,
          asr_improvement: backendResult.comparison?.asr || 0,
          ami_improvement: backendResult.comparison?.ami || 0,
          art_improvement: backendResult.comparison?.art || 0,

          // 训练日志
          training_logs: backendResult.training_logs || [],

          // 其他信息
          attack_methods: backendResult.attack_methods || [],
          task_type: backendResult.task_type || ''
        };

        // 计算微调后的平均性能
        if (backendResult.new_metrics && Array.isArray(backendResult.new_metrics)) {
          const totalMethods = backendResult.new_metrics.length;
          result.final_asr = backendResult.new_metrics.reduce((sum: number, method: any) => sum + (method.asr || 0), 0) / totalMethods;
          result.final_ami = backendResult.new_metrics.reduce((sum: number, method: any) => sum + (method.ami || 0), 0) / totalMethods;
          result.final_art = backendResult.new_metrics.reduce((sum: number, method: any) => sum + (method.art || 0), 0) / totalMethods;
        } else if (backendResult.new_metrics) {
          result.final_asr = backendResult.new_metrics.asr || 0;
          result.final_ami = backendResult.new_metrics.ami || 0;
          result.final_art = backendResult.new_metrics.art || 0;
        }

        setFinetuningResult(result);
        message.success('微调结果已获取');

        // 存储到sessionStorage供结果页面使用
        sessionStorage.setItem('finetuningResult', JSON.stringify(result));
        console.log('✅ 微调结果已存储到sessionStorage');
      } else {
        console.error('⚠️ 后端返回失败:', resultsResponse);
        message.error('获取微调结果失败');
      }
    } catch (error) {
      console.error('❌ 获取微调结果时出错:', error);
      message.error('获取微调结果失败: ' + (error as Error).message);
    }
  };

  const handleFileUpload = async (info: any) => {
    console.log('Upload onChange triggered:', info);
    const { file } = info;
    
    // 获取实际的文件对象
    const actualFile = file.originFileObj || file;
    
    if (!actualFile) {
      console.error('No file object found');
      return;
    }

    // 需先选择任务类型
    const taskType = form.getFieldValue('task_type');
    if (!taskType) {
      message.warning('请先选择任务类型再上传数据集');
      return;
    }

    console.log('Processing file:', actualFile.name, 'Type:', actualFile.type);
    
    // 设置上传的文件信息
    setUploadedFile(file);

    // 实际上传到后端（可选）
    try {
      await ApiService.uploadFile(actualFile, {
        fileType: 'dataset',
        purpose: 'finetuning',
        taskType: taskType,
        datasetName: actualFile.name,
      });
      console.log('File uploaded to backend successfully');
    } catch (e) {
      // 即使上传失败，也允许继续在前端解析以演示
      console.warn('数据集上传失败，继续本地解析:', e);
    }

    // 本地解析文件内容
    message.loading({ content: '正在解析数据集...', key: 'parsing' });
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        console.log('File content loaded, length:', content.length);
        
        // 根据文件类型解析
        let data: TrainingData[] = [];
        
        if (actualFile.name.endsWith('.json')) {
          // JSON格式
          const jsonData = JSON.parse(content);
          data = Array.isArray(jsonData) ? jsonData.map((item, index) => ({
            id: `train_${index + 1}`,
            original_code: item.original_code || item.code || JSON.stringify(item),
            adversarial_code: item.adversarial_code || '',
            label: item.label || 'unknown',
            difficulty: (item.difficulty || 'medium') as 'easy' | 'medium' | 'hard',
            status: 'pending' as const
          })) : [];
        } else if (actualFile.name.endsWith('.csv')) {
          // CSV格式
          const lines = content.split('\n').filter(line => line.trim());
          // 跳过表头
          const dataLines = lines.slice(1);
          data = dataLines.map((line, index) => {
            const parts = line.split(',');
            return {
              id: `train_${index + 1}`,
              original_code: parts[0] ? parts[0].trim() : '',
              adversarial_code: parts[1] ? parts[1].trim() : '',
              label: parts[2] ? parts[2].trim() : 'unknown',
              difficulty: 'medium' as const,
              status: 'pending' as const
            };
          });
        } else {
          // TXT格式 - 每行格式：原始代码|对抗代码|标签
          const lines = content.split('\n').filter(line => line.trim());
          data = lines.map((line, index) => {
            const parts = line.split('|');
            return {
              id: `train_${index + 1}`,
              original_code: parts[0] || '',
              adversarial_code: parts[1] || '',
              label: parts[2] || 'unknown',
              difficulty: 'medium' as const,
              status: 'pending' as const
            };
          });
        }
        
        console.log('Parsed training data:', data.length);
        
        if (data.length === 0) {
          message.error({ content: '数据集为空或格式不正确', key: 'parsing' });
          return;
        }
        
        setTrainingData(data);
        message.success({ 
          content: `成功加载 ${data.length} 个训练样本`, 
          key: 'parsing',
          duration: 2
        });
      } catch (error) {
        console.error('Parse error:', error);
        message.error({ content: '数据集解析失败: ' + (error as Error).message, key: 'parsing' });
      }
    };
    
    reader.onerror = (error) => {
      console.error('FileReader error:', error);
      message.error({ content: '文件读取失败', key: 'parsing' });
    };
    
    reader.readAsText(actualFile);
  };

  // 轮询微调状态
  const pollFinetuningStatus = async (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const statusResponse = await ApiService.getFinetuningStatus(taskId);
        
        if (statusResponse.success) {
          const status = statusResponse.status;
          console.log('📊 微调状态:', status);
          
          // 更新进度信息
          if (status.progress) {
            setTrainingProgress({
              current_epoch: status.progress.current_epoch || 0,
              total_epochs: status.progress.total_epochs || 3,
              current_step: status.progress.current_step || 0,
              total_steps: status.progress.total_steps || 100,
              loss: status.progress.loss || 0,
              accuracy: status.progress.accuracy || 0,
              learning_rate: status.progress.learning_rate || 2e-5,
              eta: status.progress.eta || '计算中...'
            });
            setCurrentStep(Math.min(status.progress.current_epoch || 0, 3));
          }
          
          setTaskStatus(status.message || '训练中...');
          
          // 检查是否完成
          if (status.status === 'completed' || status.status === 'success') {
            clearInterval(interval);
            (window as any).finetuningInterval = null;
            setTrainingRunning(false);
            setTrainingComplete(true);
            setTaskStatus('鲁棒性增强完成');
            setCurrentStep(3);
            
            // 获取微调结果
            fetchFinetuningResults(taskId);
            message.success('鲁棒性增强完成');
          } else if (status.status === 'failed' || status.status === 'error') {
            clearInterval(interval);
            (window as any).finetuningInterval = null;
            setTrainingRunning(false);
            setTaskStatus('鲁棒性增强失败');
            message.error(status.error || '鲁棒性增强失败');
          }
        }
      } catch (error) {
        console.error('❌ 获取微调状态失败:', error);
      }
    }, 3000); // 每3秒轮询一次
    
    (window as any).finetuningInterval = interval;
  };

  const simulateTraining = (taskId: string) => {
    let epoch = 0;
    let step = 0;
    const totalEpochs = trainingConfig?.epochs || 5;
    const stepsPerEpoch = Math.ceil(trainingData.length / (trainingConfig?.batch_size || 8));
    const totalSteps = totalEpochs * stepsPerEpoch;
    
    const interval = setInterval(() => {
      step += 1;
      if (step > stepsPerEpoch) {
        epoch += 1;
        step = 1;
        setCurrentStep(Math.min(epoch, 3)); // 最多显示3个步骤
      }
      
      const progress: TrainingProgress = {
        current_epoch: epoch,
        total_epochs: totalEpochs,
        current_step: step,
        total_steps: stepsPerEpoch,
        loss: Math.max(0.1, 2.0 - (epoch * 0.3) - (step / stepsPerEpoch) * 0.1),
        accuracy: Math.min(0.95, 0.6 + (epoch * 0.05) + (step / stepsPerEpoch) * 0.02),
        learning_rate: (trainingConfig?.learning_rate || 0.001) * Math.pow(0.9, epoch),
        eta: `${Math.max(0, totalSteps - (epoch * stepsPerEpoch + step)) * 2}分钟`
      };
      
      setTrainingProgress(progress);
      setTaskStatus(`训练中 - Epoch ${epoch + 1}/${totalEpochs}, Step ${step}/${stepsPerEpoch}`);
      
      if (epoch >= totalEpochs) {
        clearInterval(interval);
        setTaskStatus('鲁棒性增强完成');
        setTrainingRunning(false);
        setTrainingComplete(true);
        setCurrentStep(3);
        
        // 生成训练结果
        setTimeout(() => {
          generateTrainingResult();
        }, 1000);
      }
    }, 2000);
  };


  const generateTrainingResult = () => {
    // 微调前性能
    const originalAccuracy = 0.75 + Math.random() * 0.1;
    const originalBleuScore = 0.65 + Math.random() * 0.1;
    const originalASR = 0.35 + Math.random() * 0.15; // 攻击成功率应该降低（模型更鲁棒）
    const originalAMI = 0.65 + Math.random() * 0.1;
    const originalART = 0.45 + Math.random() * 0.15;
    
    // 微调后性能
    const finalAccuracy = originalAccuracy + 0.05 + Math.random() * 0.1;
    const finalBleuScore = originalBleuScore + 0.03 + Math.random() * 0.08;
    const finalASR = originalASR - 0.1 - Math.random() * 0.1; // 攻击成功率降低
    const finalAMI = originalAMI + 0.05 + Math.random() * 0.08;
    const finalART = originalART - 0.1 - Math.random() * 0.1; // 攻击响应时间降低（模型更鲁棒）
    const adversarialAccuracy = finalAccuracy - 0.05 - Math.random() * 0.05;
    const adversarialBleuScore = finalBleuScore - 0.02 - Math.random() * 0.03;
    
    // 计算性能提升
    const accuracyImprovement = ((finalAccuracy - originalAccuracy) / originalAccuracy) * 100;
    const bleuImprovement = ((finalBleuScore - originalBleuScore) / originalBleuScore) * 100;
    const asrImprovement = ((originalASR - finalASR) / originalASR) * 100; // ASR降低是好事
    const amiImprovement = ((finalAMI - originalAMI) / originalAMI) * 100;
    const artImprovement = ((originalART - finalART) / originalART) * 100; // ART降低是好事
    const overallImprovement = (accuracyImprovement + bleuImprovement + asrImprovement + amiImprovement + artImprovement) / 5;
    
    const result: FinetuningResult = {
      model_id: `finetuned_${Date.now()}`,
      model_name: `鲁棒性增强模型_${new Date().toLocaleDateString()}`,
      training_time: Math.floor(Math.random() * 1800) + 600, // 10-40分钟
      final_loss: 0.1 + Math.random() * 0.2,
      // 微调前性能
      original_accuracy: originalAccuracy,
      original_bleu_score: originalBleuScore,
      original_asr: originalASR,
      original_ami: originalAMI,
      original_art: originalART,
      // 微调后性能
      final_accuracy: finalAccuracy,
      final_bleu_score: finalBleuScore,
      final_asr: finalASR,
      final_ami: finalAMI,
      final_art: finalART,
      adversarial_accuracy: adversarialAccuracy,
      adversarial_bleu_score: adversarialBleuScore,
      // 性能提升
      accuracy_improvement: accuracyImprovement,
      bleu_improvement: bleuImprovement,
      asr_improvement: asrImprovement,
      ami_improvement: amiImprovement,
      art_improvement: artImprovement,
      overall_improvement: overallImprovement,
      model_path: `/models/finetuned_${Date.now()}`,
      training_logs: [],
      training_samples: trainingData.length,
      evaluation_samples: 0
    };
    
    setFinetuningResult(result);
    message.success('鲁棒性增强完成');
  };

  const handleStopTraining = () => {
    setTrainingRunning(false);
    setTaskStatus('');
    setCurrentTaskId(null);
    setCurrentStep(0);
    message.info('鲁棒性增强已停止');
  };

  const downloadModel = () => {
    if (!finetuningResult) return;
    message.info('模型下载功能开发中...');
  };

  const getDifficultyColor = (difficulty: string) => {
    const colors = {
      easy: 'green',
      medium: 'orange',
      hard: 'red'
    };
    return colors[difficulty as keyof typeof colors];
  };

  const getStatusColor = (status: string) => {
    const colors = {
      pending: 'default',
      processing: 'processing',
      completed: 'success',
      failed: 'error'
    };
    return colors[status as keyof typeof colors];
  };

  const columns = [
    {
      title: '原始代码',
      dataIndex: 'original_code',
      key: 'original_code',
      width: 200,
      render: (text: string) => (
        <Text code style={{ fontSize: '12px' }}>
          {text.length > 30 ? `${text.substring(0, 30)}...` : text}
        </Text>
      ),
    },
    {
      title: '对抗代码',
      dataIndex: 'adversarial_code',
      key: 'adversarial_code',
      width: 200,
      render: (text: string) => (
        <Text code style={{ fontSize: '12px' }}>
          {text.length > 30 ? `${text.substring(0, 30)}...` : text}
        </Text>
      ),
    },
    {
      title: '标签',
      dataIndex: 'label',
      key: 'label',
      width: 120,
      render: (label: string) => <Tag color="blue">{label}</Tag>,
    },
    {
      title: '难度',
      dataIndex: 'difficulty',
      key: 'difficulty',
      width: 80,
      render: (difficulty: string) => (
        <Tag color={getDifficultyColor(difficulty)}>
          {difficulty.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusConfig = {
          pending: { color: 'default', text: '等待中' },
          processing: { color: 'processing', text: '处理中' },
          completed: { color: 'success', text: '完成' },
          failed: { color: 'error', text: '失败' },
        };
        const config = statusConfig[status as keyof typeof statusConfig];
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
  ];

  const trainingSteps = [
    {
      title: '数据准备',
      description: '加载和预处理训练数据',
      icon: <UploadOutlined />
    },
    {
      title: '模型初始化',
      description: '加载预训练模型和配置参数',
      icon: <CodeOutlined />
    },
    {
      title: '鲁棒性增强',
      description: '执行鲁棒性增强',
      icon: <ExperimentOutlined />
    },
    {
      title: '模型保存',
      description: '保存鲁棒性增强后的模型',
      icon: <CheckCircleOutlined />
    }
  ];

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px', textAlign: 'center' }}>
        <Title level={1} style={{ marginBottom: '8px', color: '#1890ff' }}>
          <RocketOutlined style={{ marginRight: '16px' }} />
          模型鲁棒性增强
        </Title>
        <Text type="secondary" style={{ fontSize: '16px' }}>
          通过对抗性训练提升模型对攻击的防御能力
        </Text>
      </div>

      <Tabs defaultActiveKey="finetuning" type="card" style={{ background: 'white', borderRadius: '8px' }}>
        {/* 微调配置标签页 */}
        <TabPane
          tab={
            <span>
              <ExperimentOutlined />
              微调配置
            </span>
          }
          key="finetuning"
        >
          <Row gutter={24}>
            {/* 配置表单 */}
            <Col span={24}>
              <Card
                title={
                  <span>
                    <SettingOutlined style={{ marginRight: '8px' }} />
                    微调参数配置
                  </span>
                }
              >
                <Form
                  form={form}
                  layout="vertical"
                  onFinish={handleStartFinetuning}
                  initialValues={{
                    task_type: 'clone-detection',
                    attack_methods: ['itgen'],
                    sub_task_type: 'attack_resistance',
                    learning_rate: 2e-5,
                    epochs: 3,
                    batch_size: 16,
                    max_queries: 100
                  }}
                >
                  <Row gutter={16}>
                    <Col span={6}>
                      <Form.Item
                        name="model_name"
                        label="基础模型"
                        rules={[{ required: true, message: '请选择基础模型' }]}
                      >
                        <Select
                          placeholder="选择模型"
                          suffixIcon={<ExperimentOutlined />}
                          size="large"
                        >
                          {models.map(model => (
                            <Option key={model.model_name} value={model.model_name}>
                              {model.model_name}
                            </Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item
                        name="task_type"
                        label="任务类型"
                        rules={[{ required: true, message: '请选择任务类型' }]}
                      >
                        <Select placeholder="选择任务类型" size="large">
                          <Option value="clone-detection">代码克隆检测</Option>
                          <Option value="vulnerability-detection">漏洞检测</Option>
                          <Option value="code-summarization">代码摘要生成</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item
                        name="dataset"
                        label="训练数据集"
                        rules={[{ required: true, message: '请选择训练数据集' }]}
                      >
                        <Select placeholder="选择数据集" size="large">
                          <Option value="finetuning-dataset">微调数据集</Option>
                          <Option value="adversarial-dataset">对抗数据集</Option>
                          <Option value="mixed-dataset">混合数据集</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item
                        name="sub_task_type"
                        label="微调策略"
                        rules={[{ required: true, message: '请选择微调策略' }]}
                      >
                        <Select placeholder="选择策略" size="large">
                          <Option value="attack_resistance">攻击抵抗</Option>
                          <Option value="performance_optimization">性能优化</Option>
                          <Option value="balanced_training">均衡训练</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="attack_methods"
                        label="对抗算法"
                        rules={[{ required: true, message: '请选择对抗算法' }]}
                      >
                        <Select
                          mode="multiple"
                          placeholder="选择对抗算法"
                          size="large"
                          suffixIcon={<BugOutlined />}
                        >
                          {supportedMethods.map(method => (
                            <Option key={method} value={method}>
                              <Tag color="blue">{method.toUpperCase()}</Tag>
                            </Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="max_queries" label="最大查询次数">
                        <Input type="number" placeholder="100" size="large" suffix="次" />
                      </Form.Item>
                    </Col>
                  </Row>

                  {/* 训练参数折叠 */}
                  <Divider orientation="left">训练参数</Divider>
                  <Row gutter={16}>
                    <Col span={6}>
                      <Form.Item name="learning_rate" label="学习率">
                        <Input placeholder="2e-5" size="large" />
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="epochs" label="训练轮数">
                        <Input type="number" placeholder="3" size="large" suffix="轮" />
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="batch_size" label="批次大小">
                        <Input type="number" placeholder="16" size="large" suffix="个" />
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item label="操作">
                        <Space>
                          <Button
                            type="primary"
                            htmlType="submit"
                            loading={loading}
                            size="large"
                            icon={<PlayCircleOutlined />}
                            disabled={!!taskInfo && ['pending', 'running'].includes(taskInfo.status)}
                          >
                            {loading ? '启动中...' : '开始微调'}
                          </Button>
                          <Button
                            onClick={() => form.resetFields()}
                            size="large"
                            icon={<StopOutlined />}
                          >
                            重置
                          </Button>
                        </Space>
                      </Form.Item>
                    </Col>
                  </Row>
                </Form>
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 任务状态标签页 */}
        <TabPane
          tab={
            <span>
              <AppstoreOutlined />
              任务状态
              {taskInfo && (
                <Badge
                  count={getStatusInfo(taskInfo.status).text}
                  style={{ backgroundColor: getStatusInfo(taskInfo.status).color }}
                />
              )}
            </span>
          }
          key="status"
        >
          {taskInfo ? (
            <Card>
              <Row gutter={24}>
                <Col span={8}>
                  <Statistic
                    title="任务状态"
                    value={getStatusInfo(taskInfo.status).text}
                    prefix={getStatusInfo(taskInfo.status).icon}
                    valueStyle={{ color: getStatusInfo(taskInfo.status).color }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="任务ID"
                    value={taskInfo.id}
                    valueStyle={{ fontSize: '14px' }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="创建时间"
                    value={new Date(taskInfo.created_at).toLocaleString()}
                    valueStyle={{ fontSize: '12px' }}
                  />
                </Col>
              </Row>

              <Divider />

              <Row gutter={24}>
                <Col span={12}>
                  <div style={{ marginBottom: '16px' }}>
                    <Text strong>训练进度</Text>
                    <Progress
                      percent={taskInfo.progress}
                      status={taskInfo.status === 'running' ? 'active' : taskInfo.status === 'completed' ? 'success' : 'normal'}
                      strokeColor={{
                        '0%': '#108ee9',
                        '100%': '#87d068',
                      }}
                    />
                  </div>

                  {taskInfo.progress_message && (
                    <Alert
                      message={taskInfo.progress_message}
                      type={taskInfo.status === 'running' ? 'info' : taskInfo.status === 'completed' ? 'success' : 'warning'}
                      showIcon
                    />
                  )}
                </Col>
                <Col span={12}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Button
                      type="primary"
                      onClick={handleViewResult}
                      disabled={!taskInfo.result}
                      icon={<EyeOutlined />}
                      block
                    >
                      查看结果
                    </Button>
                    <Button
                      danger
                      onClick={handleCancelTask}
                      disabled={!['pending', 'running'].includes(taskInfo.status)}
                      icon={<StopOutlined />}
                      block
                    >
                      取消任务
                    </Button>
                  </Space>
                </Col>
              </Row>

              {taskInfo.result && (
                <>
                  <Divider />
                  <Descriptions title="微调结果概览" bordered column={2}>
                    <Descriptions.Item label="最终损失">
                      <Text strong style={{ color: '#1890ff' }}>
                        {taskInfo.result.final_loss ? taskInfo.result.final_loss.toFixed(4) : 'N/A'}
                      </Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="训练轮数">
                      <Text strong>{taskInfo.result.epochs_completed || 'N/A'}</Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="模型大小">
                      <Text strong style={{ color: '#52c41a' }}>
                        {taskInfo.result.model_size ? `${(taskInfo.result.model_size / 1024 / 1024).toFixed(2)}MB` : 'N/A'}
                      </Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="输出文件">
                      <Text strong>{taskInfo.result.output_files?.length || 0} 个</Text>
                    </Descriptions.Item>
                  </Descriptions>
                </>
              )}
            </Card>
          ) : (
            <Empty
              description="暂无运行中的任务"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </TabPane>

        {/* 历史记录标签页 */}
        <TabPane
          tab={
            <span>
              <ClockCircleOutlined />
              历史记录
            </span>
          }
          key="history"
        >
          <Card>
            <Timeline>
              {finetuningHistory.map(task => (
                <Timeline.Item
                  key={task.id}
                  color={getStatusInfo(task.status).color}
                  dot={getStatusInfo(task.status).icon}
                >
                  <div style={{ padding: '8px 0' }}>
                    <Space>
                      <Tag color="blue">{task.sub_task_type}</Tag>
                      <Text strong>{task.id.slice(0, 8)}...</Text>
                      <Text type="secondary">
                        {new Date(task.created_at).toLocaleString()}
                      </Text>
                      {task.status === 'completed' && task.result?.final_loss && (
                        <TrophyOutlined style={{ color: '#52c41a' }} />
                      )}
                    </Space>
                    <div style={{ marginTop: '8px' }}>
                      <Text>
                        状态: {getStatusInfo(task.status).text}
                        {task.result && ` | 损失: ${task.result.final_loss?.toFixed(4) || 'N/A'}`}
                      </Text>
                    </div>
                  </div>
                </Timeline.Item>
              ))}
            </Timeline>
            {finetuningHistory.length === 0 && (
              <Empty description="暂无历史记录" />
            )}
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Finetuning;
