import React, { useState, useEffect } from 'react';
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
  Upload,
  Table,
  Tag,
  Modal,
  Statistic,
  Tabs,
  Descriptions
} from 'antd';
import { 
  PlayCircleOutlined, 
  StopOutlined, 
  UploadOutlined,
  DownloadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  CopyOutlined
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import { apiService as ApiService } from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { TabPane } = Tabs;

interface TestCase {
  id: string;
  code: string;
  language: string;
  expected_result: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: any;
  error?: string;
}

interface BatchTestResult {
  total: number;
  completed: number;
  failed: number;
  success_rate: number;
  avg_time: number;
  results: TestCase[];
  // 基线方法对比
  baseline_comparison: {
    alert_performance: {
      accuracy: number;
      bleu_score: number;
      avg_time: number;
    };
    beam_attack_performance: {
      accuracy: number;
      bleu_score: number;
      avg_time: number;
    };
    itgen_performance: {
      accuracy: number;
      bleu_score: number;
      avg_time: number;
    };
  };
  // 任务类型统计
  task_statistics: {
    'vulnerability-detection': { success: number; total: number; };
    'clone-detection': { success: number; total: number; };
    'code-summarization': { success: number; total: number; };
  };
}

const BatchTesting: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [form] = Form.useForm();
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [testRunning, setTestRunning] = useState(false);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [testResults, setTestResults] = useState<BatchTestResult | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [taskProgress, setTaskProgress] = useState(0);
  const [taskStatus, setTaskStatus] = useState<string>('');
  const [uploadedFile, setUploadedFile] = useState<any>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null);
  const [copiedType, setCopiedType] = useState<string>('');

  useEffect(() => {
    fetchModels();
    
    // 检查是否从路由参数中加载结果（从任务管理页面跳转过来）
    const stateData = location.state as any;
    if (stateData && stateData.taskId && stateData.result) {
      console.log('📦 从路由state加载批量攻击结果', stateData);
      console.log('📦 result数据:', stateData.result);
      setCurrentTaskId(stateData.taskId);
      setTaskProgress(100);
      setTaskStatus('completed');
      // 处理结果数据 - 直接传递result对象，processBatchResults会处理
      processBatchResults(stateData.result);
    }
    
    // 组件卸载时清理定时器
    return () => {
      if ((window as any).batchTestingInterval) {
        clearInterval((window as any).batchTestingInterval);
        (window as any).batchTestingInterval = null;
      }
    };
  }, [location]);

  const fetchModels = async () => {
    try {
      const response = await ApiService.getModels();
      if (response.success) {
        setModels(response.data);
      }
    } catch (error) {
      console.error('Error fetching models:', error);
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
    const taskType = form.getFieldValue('test_type');
    if (!taskType) {
      message.warning('请先选择测试类型再上传数据集');
      return;
    }

    console.log('Processing file:', actualFile.name, 'Type:', actualFile.type);
    
    // 设置上传的文件信息
    setUploadedFile(file);

    // 实际上传到后端（可选）
    try {
      await ApiService.uploadFile(actualFile, {
        fileType: 'dataset',
        purpose: 'batch_testing',
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
        let cases: TestCase[] = [];
        
        if (actualFile.name.endsWith('.json')) {
          // JSON格式
          const jsonData = JSON.parse(content);
          cases = Array.isArray(jsonData) ? jsonData.map((item, index) => ({
            id: `test_${index + 1}`,
            code: item.code || item.text || JSON.stringify(item),
            language: item.language || 'python',
            expected_result: item.expected_result || '',
            status: 'pending' as const
          })) : [];
        } else if (actualFile.name.endsWith('.csv')) {
          // CSV格式
          const lines = content.split('\n').filter(line => line.trim());
          // 跳过表头
          const dataLines = lines.slice(1);
          cases = dataLines.map((line, index) => {
            const parts = line.split(',');
            return {
              id: `test_${index + 1}`,
              code: parts[0] ? parts[0].trim() : line.trim(),
              language: parts[1] ? parts[1].trim() : 'python',
              expected_result: parts[2] ? parts[2].trim() : '',
              status: 'pending' as const
            };
          });
        } else {
          // TXT格式 - 每行一个测试用例
          const lines = content.split('\n').filter(line => line.trim());
          cases = lines.map((line, index) => ({
            id: `test_${index + 1}`,
            code: line.trim(),
            language: 'python',
            expected_result: '',
            status: 'pending' as const
          }));
        }
        
        console.log('Parsed test cases:', cases.length);
        
        if (cases.length === 0) {
          message.error({ content: '数据集为空或格式不正确', key: 'parsing' });
          return;
        }
        
        setTestCases(cases);
        message.success({ 
          content: `成功加载 ${cases.length} 个测试用例`, 
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

  const handleStartBatchTest = async (values: any) => {
    if (testCases.length === 0) {
      message.warning('请先上传数据集');
      return;
    }

    if (!uploadedFile) {
      message.warning('请先上传数据集文件');
      return;
    }

    // 清除上一次的轮询定时器
    if ((window as any).batchTestingInterval) {
      clearInterval((window as any).batchTestingInterval);
      (window as any).batchTestingInterval = null;
    }

    // 清除上一次的生成结果
    setTestResults(null);
    setTaskProgress(0);
    setTaskStatus('');
    setCurrentTaskId(null);

    setLoading(true);
    setTestRunning(true);
    
    try {
      // 构造符合新格式的请求数据
      const requestData = {
        model_name: values.model_name || 'codebert',
        task_type: 'batch_testing',
        test_type: values.test_type || 'clone-detection',
        attack_method: values.attack_method || 'itgen',
        parameters: {
          eval_data_file: uploadedFile.name || 'test_dataset.txt',
          block_size: parseInt(values.block_size) || 512,
          eval_batch_size: parseInt(values.eval_batch_size) || 2,
          seed: parseInt(values.seed) || 123456,
          cuda_device: parseInt(values.cuda_device) || 0,
          beam_size: parseInt(values.beam_size) || 2,
          timeout: parseInt(values.timeout) || 3600
        }
      };

      console.log('批量测试请求数据:', JSON.stringify(requestData, null, 2));

      // 调用后端API启动批量测试任务
      console.log('🚀 调用后端API启动批量测试...');
      const response = await ApiService.startBatchTesting(requestData);
      
      if (!response.success) {
        throw new Error(response.error || '启动批量测试失败');
      }

      const taskId = response.task_id;
      if (!taskId) {
        throw new Error('后端未返回任务ID');
      }

      console.log('✅ 批量测试任务已创建，taskId:', taskId);
      
      setCurrentTaskId(taskId);
      setTaskStatus('批量对抗样本生成已启动');
      setTaskProgress(0);

      message.success('批量对抗样本生成已启动');

      // 开始轮询任务状态
      pollTaskStatus(taskId);
    } catch (error: any) {
      message.error('批量对抗样本生成启动失败: ' + (error.message || '未知错误'));
      console.error('Error starting batch test:', error);
      setTestRunning(false);
      setLoading(false);
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    console.log('🔄 开始轮询任务状态，taskId:', taskId);
    
    // 清除之前的轮询
    if ((window as any).batchTestingInterval) {
      clearInterval((window as any).batchTestingInterval);
      (window as any).batchTestingInterval = null;
    }
    
    let isPolling = true; // 标记是否应该继续轮询
    
    const interval = setInterval(async () => {
      if (!isPolling) {
        clearInterval(interval);
        (window as any).batchTestingInterval = null;
        return;
      }

      try {
        const statusResponse = await ApiService.getBatchTestingStatus(taskId);
        console.log('📊 状态轮询响应:', statusResponse);
        
        // 检查任务是否存在
        if (statusResponse.isTaskNotFound || (!statusResponse.success && statusResponse.error === '任务不存在')) {
          console.log('⚠️ 任务不存在，停止轮询');
          isPolling = false;
          clearInterval(interval);
          (window as any).batchTestingInterval = null;
          
          setTestRunning(false);
          setLoading(false);
          setTaskProgress(0);
          setTaskStatus('');
          setCurrentTaskId(null);
          message.warning('任务不存在，已停止轮询');
          return;
        }
        
        if (statusResponse.success) {
          const status = statusResponse.status;
          console.log('  - status:', status.status);
          console.log('  - progress:', status.progress);
          console.log('  - message:', status.message || status.progress_message);
          
          // 更新进度
          if (status.progress !== undefined) {
            setTaskProgress(status.progress);
          }
          
          // 更新状态消息
          if (status.message || status.progress_message) {
            setTaskStatus(status.message || status.progress_message || '');
          } else {
            setTaskStatus(`批量对抗样本生成进行中... ${status.progress || 0}%`);
          }
          
          // 检查是否完成
          if (status.status === 'completed' || status.status === 'success') {
            console.log('🎉 任务已完成，准备处理结果');
            isPolling = false; // 停止轮询
            clearInterval(interval);
            (window as any).batchTestingInterval = null;
            
            setTaskProgress(100);
            setTaskStatus('批量对抗样本生成完成');
            setTestRunning(false);
            setLoading(false);
            
            // 从任务状态中获取结果
            if (status.result) {
              console.log('📞 处理任务结果');
              processBatchResults(status.result);
              message.success('批量对抗样本已生成');
            } else {
              // 如果没有结果，尝试从结果API获取
              await fetchBatchResults(taskId);
            }
            return; // 任务完成，不再继续轮询
          } else if (status.status === 'failed' || status.status === 'error' || status.status === 'cancelled') {
            console.error('❌ 任务失败/取消:', status.error || status.error_message);
            isPolling = false; // 停止轮询
            clearInterval(interval);
            (window as any).batchTestingInterval = null;
            
            setTestRunning(false);
            setLoading(false);
            setTaskStatus(status.status === 'cancelled' ? '批量对抗样本生成已取消' : '批量对抗样本生成失败');
            if (status.status === 'cancelled') {
              message.info('任务已取消');
            } else {
              message.error(status.error || status.error_message || '批量对抗样本生成失败');
            }
            return; // 任务失败/取消，不再继续轮询
          }
        } else {
          console.warn('⚠️ 状态轮询返回失败:', statusResponse);
        }
      } catch (error: any) {
        // 如果是404错误，停止轮询
        if (error.response && error.response.status === 404) {
          console.log('⚠️ 任务不存在（404），停止轮询');
          isPolling = false;
          clearInterval(interval);
          (window as any).batchTestingInterval = null;
          
          setTestRunning(false);
          setLoading(false);
          setTaskProgress(0);
          setTaskStatus('');
          setCurrentTaskId(null);
          message.warning('任务不存在，已停止轮询');
          return;
        }
        console.error('❌ 轮询任务状态时出错:', error);
        // 其他错误继续轮询，不中断
      }
    }, 2000); // 每2秒轮询一次
    
    // 存储interval ID以便停止时清除
    (window as any).batchTestingInterval = interval;
  };

  const processBatchResults = (resultData: any) => {
    try {
      console.log('📥 开始处理批量测试结果');
      console.log('📦 结果数据类型:', typeof resultData);
      console.log('📦 结果数据:', resultData);
      
      // 从后端返回的result中获取results数组
      let parsedResults: any[] = [];
      
      if (resultData.results && Array.isArray(resultData.results)) {
        // 如果result中有results数组
        parsedResults = resultData.results;
        console.log('✅ 从result.results获取数据，共', parsedResults.length, '条记录');
      } else if (Array.isArray(resultData)) {
        // 如果result本身就是数组
        parsedResults = resultData;
        console.log('✅ result本身就是数组，共', parsedResults.length, '条记录');
      } else {
        console.warn('⚠️ 未知的结果格式');
        parsedResults = [];
      }
      
      if (parsedResults.length === 0) {
        message.warning('批量测试结果为空');
        return;
      }
      
      console.log('📊 解析后的结果数量:', parsedResults.length);
      
      // 统计数据
      const successCount = parsedResults.filter(item => 
        item['Adversarial Code'] !== null && item['Adversarial Code'] !== undefined && item['Adversarial Code'] !== ''
      ).length;
      const failedCount = parsedResults.length - successCount;
      const totalQueries = parsedResults.reduce((sum, item) => sum + (item['Query Times'] || 0), 0);
      const totalTime = parsedResults.reduce((sum, item) => sum + (item['Time Cost'] || 0), 0);
      
      console.log('📈 统计信息:');
      console.log('  - 总数:', parsedResults.length);
      console.log('  - 成功:', successCount);
      console.log('  - 失败:', failedCount);
      console.log('  - 平均查询次数:', parsedResults.length > 0 ? totalQueries / parsedResults.length : 0);
      console.log('  - 平均时间:', parsedResults.length > 0 ? totalTime / parsedResults.length : 0);
      
      // 将后端结果映射到前端数据结构
      const results: BatchTestResult = {
        total: parsedResults.length,
        completed: successCount,
        failed: failedCount,
        success_rate: parsedResults.length > 0 ? Math.round((successCount / parsedResults.length) * 100 * 100) / 100 : 0,
        avg_time: parsedResults.length > 0 ? totalTime / parsedResults.length : 0,
        results: parsedResults.map((item, index) => ({
          id: `test_${item['Index'] !== undefined ? item['Index'] : index}`,
          code: item['Original Code'] || `Sample ${index + 1}`,
          language: 'java', // 根据实际情况设置
          expected_result: 'success',
          status: (item['Adversarial Code'] && item['Adversarial Code'] !== null && item['Adversarial Code'] !== '') ? 'completed' as const : 'failed' as const,
          result: (item['Adversarial Code'] && item['Adversarial Code'] !== null && item['Adversarial Code'] !== '') ? {
            success: true,
            time_cost: item['Time Cost'] || 0,
            confidence: 0.9,
            original_code: item['Original Code'],
            adversarial_code: item['Adversarial Code'],
            query_times: item['Query Times'],
            replaced_identifiers: item['Replaced Identifiers'],
            program_length: item['Program Length'],
            identifier_num: item['Identifier Num']
          } : undefined,
          error: (!item['Adversarial Code'] || item['Adversarial Code'] === null || item['Adversarial Code'] === '') ? '攻击失败' : undefined
        })),
        baseline_comparison: {
          alert_performance: { accuracy: 0, bleu_score: 0, avg_time: 0 },
          beam_attack_performance: { accuracy: 0, bleu_score: 0, avg_time: 0 },
          itgen_performance: { 
            accuracy: parsedResults.length > 0 ? (successCount / parsedResults.length) : 0, 
            bleu_score: 0, 
            avg_time: parsedResults.length > 0 ? totalTime / parsedResults.length : 0
          }
        },
        task_statistics: {
          'vulnerability-detection': { success: 0, total: 0 },
          'clone-detection': { success: successCount, total: parsedResults.length },
          'code-summarization': { success: 0, total: 0 }
        }
      };
      
      console.log('🎯 映射后的结果:', results);
      console.log('📊 准备设置testResults状态');
      
      setTestResults(results);
      message.success(`批量对抗样本生成完成！成功 ${successCount}/${parsedResults.length} 个样本`);
      
      console.log('✅ testResults状态已更新');
    } catch (error) {
      console.error('❌ 处理批量测试结果时出错:', error);
      message.error('处理测试结果失败: ' + (error as Error).message);
    }
  };

  const fetchBatchResults = async (taskId: string) => {
    try {
      console.log('📥 开始从API获取批量测试结果，taskId:', taskId);
      const resultsResponse = await ApiService.getBatchTestingResults(taskId);
      
      console.log('📦 API返回的原始结果类型:', typeof resultsResponse);
      console.log('📦 API返回的原始结果:', resultsResponse);
      
      // 处理JSONL格式的返回数据
      let parsedResults: any[] = [];
      
      if (typeof resultsResponse === 'string') {
        // 如果返回的是JSONL字符串，按行解析
        console.log('🔄 检测到JSONL字符串格式，开始解析...');
        const lines = resultsResponse.split('\n').filter(line => line.trim());
        parsedResults = lines.map(line => {
          try {
            return JSON.parse(line);
          } catch (e) {
            console.warn('解析行失败:', line);
            return null;
          }
        }).filter(item => item !== null);
        console.log(`✅ JSONL解析完成，共 ${parsedResults.length} 条记录`);
      } else if (Array.isArray(resultsResponse)) {
        // 如果已经是数组
        console.log('✅ 检测到数组格式');
        parsedResults = resultsResponse;
      } else if (resultsResponse && resultsResponse.success) {
        // 如果是标准格式的响应对象
        console.log('✅ 检测到标准格式');
        parsedResults = resultsResponse.results || [];
      } else {
        console.warn('⚠️ 未知的返回格式');
        parsedResults = [];
      }
      
      // 使用processBatchResults处理结果
      processBatchResults({ results: parsedResults });
    } catch (error) {
      console.error('❌ 获取批量测试结果时出错:', error);
      message.error('获取测试结果失败: ' + (error as Error).message);
    }
  };

  const handleStopTest = async () => {
    if (!currentTaskId) {
      message.warning('没有正在运行的任务');
      return;
    }

    try {
      // 调用后端API取消任务
      const response = await ApiService.cancelTask(currentTaskId, '用户手动取消');
      
      if (response.success) {
        message.success('任务已取消');
      } else {
        message.warning(response.message || '取消任务失败');
      }
    } catch (error) {
      console.error('取消任务失败:', error);
      message.error('取消任务失败: ' + (error as Error).message);
    }
    
    // 清除轮询定时器
    if ((window as any).batchTestingInterval) {
      clearInterval((window as any).batchTestingInterval);
      (window as any).batchTestingInterval = null;
    }
    
    setTestRunning(false);
    setLoading(false);
    setTaskProgress(0);
    setTaskStatus('任务已取消');
    setCurrentTaskId(null);
  };

  const downloadResults = () => {
    if (!testResults) return;
    
    const csvContent = [
      '测试用例ID,代码,语言,状态,结果,错误信息',
      ...testResults.results.map(result => 
        `${result.id},"${result.code}",${result.language},${result.status},"${result.result ? '成功' : '失败'}",${result.error || ''}`
      )
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `batch_test_results_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  // 解析标识符替换字符串
  const parseIdentifierReplacements = (replacedStr: string | null | undefined): Array<{original: string, adversarial: string}> => {
    if (!replacedStr) return [];
    const pairs = replacedStr.split(',').filter(p => p.trim());
    return pairs.map((pair) => {
      const [original, adversarial] = pair.split(':');
      return {
        original: original?.trim() || '',
        adversarial: adversarial?.trim() || ''
      };
    });
  };

  // 复制代码到剪贴板
  const handleCopy = async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedType(type);
      message.success('代码已复制到剪贴板');
      setTimeout(() => setCopiedType(''), 2000);
    } catch (err) {
      message.error('复制失败，请手动复制');
    }
  };

  // 查看详情
  const handleViewDetail = (record: TestCase) => {
    setSelectedTestCase(record);
    setDetailModalVisible(true);
  };

  const columns = [
    {
      title: '测试用例ID',
      dataIndex: 'id',
      key: 'id',
      width: 120,
    },
    {
      title: '原始代码',
      dataIndex: 'code',
      key: 'code',
      ellipsis: true,
      render: (text: string) => (
        <Text code style={{ fontSize: '12px' }}>
          {text.length > 50 ? `${text.substring(0, 50)}...` : text}
        </Text>
      ),
    },
    {
      title: '对抗代码',
      key: 'adversarial_code',
      ellipsis: true,
      render: (_: any, record: TestCase) => {
        const adversarialCode = record.result?.adversarial_code || '';
        return (
          <Text code style={{ fontSize: '12px', color: adversarialCode ? '#52c41a' : '#999' }}>
            {adversarialCode ? (adversarialCode.length > 50 ? `${adversarialCode.substring(0, 50)}...` : adversarialCode) : '无'}
          </Text>
        );
      },
    },
    {
      title: '语言',
      dataIndex: 'language',
      key: 'language',
      width: 80,
      render: (language: string) => <Tag color="blue">{language}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusConfig = {
          pending: { color: 'default', text: '等待中' },
          running: { color: 'processing', text: '运行中' },
          completed: { color: 'success', text: '完成' },
          failed: { color: 'error', text: '失败' },
        };
        const config = statusConfig[status as keyof typeof statusConfig];
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '查询次数',
      key: 'query_times',
      width: 100,
      render: (_: any, record: TestCase) => {
        return record.result?.query_times || '-';
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: TestCase) => (
        <Button 
          type="link" 
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
          disabled={record.status !== 'completed'}
        >
          查看详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Title level={2} style={{ marginBottom: '24px' }}>
        批量对抗样本生成
      </Title>

      <Row gutter={24}>
        <Col span={16}>
          <Card title="测试配置">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleStartBatchTest}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="model_name"
                    label="测试模型"
                    rules={[{ required: true, message: '请选择测试模型' }]}
                  >
                    <Select placeholder="请选择测试模型">
                      {models.map(model => (
                        <Option key={model.model_name} value={model.model_name}>
                          {model.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="test_type"
                    label="测试类型"
                    rules={[{ required: true, message: '请选择测试类型' }]}
                    initialValue="clone-detection"
                  >
                    <Select placeholder="请选择测试类型">
                      <Option value="clone-detection">克隆检测</Option>
                      <Option value="vulnerability-detection">漏洞检测</Option>
                      <Option value="code-summarization">代码摘要</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="language"
                    label="编程语言"
                    rules={[{ required: true, message: '请选择编程语言' }]}
                    initialValue="python"
                  >
                    <Select placeholder="请选择编程语言">
                      <Option value="python">Python</Option>
                      <Option value="java">Java</Option>
                      <Option value="c">C/C++</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="attack_method"
                    label="攻击方法"
                    initialValue="itgen"
                  >
                    <Select placeholder="请选择攻击方法">
                      <Option value="itgen">ITGen</Option>
                      <Option value="alert">ALERT</Option>
                      <Option value="beam_attack">Beam Attack</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">生成参数</Divider>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="block_size"
                    label="Block Size"
                    initialValue={512}
                    tooltip="代码块最大长度"
                  >
                    <Input type="number" placeholder="512" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="eval_batch_size"
                    label="Batch Size"
                    initialValue={2}
                    tooltip="评估批次大小"
                  >
                    <Input type="number" placeholder="2" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="beam_size"
                    label="Beam Size"
                    initialValue={2}
                    tooltip="Beam搜索宽度"
                  >
                    <Input type="number" placeholder="2" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="seed"
                    label="Random Seed"
                    initialValue={123456}
                    tooltip="随机种子，确保结果可复现"
                  >
                    <Input type="number" placeholder="123456" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="cuda_device"
                    label="CUDA Device"
                    initialValue={0}
                    tooltip="GPU设备编号，-1表示使用CPU"
                  >
                    <Input type="number" placeholder="0" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="timeout"
                    label="Timeout (秒)"
                    initialValue={3600}
                    tooltip="任务超时时间"
                  >
                    <Input type="number" placeholder="3600" />
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">数据集</Divider>

              <Form.Item 
                label="上传数据集"
                tooltip="请先选择测试类型，然后上传数据集文件"
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Upload
                    accept=".txt,.csv,.json"
                    beforeUpload={(file) => {
                      console.log('beforeUpload called with file:', file.name);
                      return false; // 阻止自动上传，由onChange手动处理
                    }}
                    onChange={handleFileUpload}
                    showUploadList={false}
                    maxCount={1}
                  >
                    <Button 
                      icon={<UploadOutlined />}
                      size="large"
                      type={testCases.length === 0 ? 'primary' : 'default'}
                    >
                      {testCases.length === 0 ? '选择数据集文件' : '重新选择数据集'}
                    </Button>
                  </Upload>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    点击按钮选择文件，支持 .txt, .csv, .json 格式
                  </Text>
                  {uploadedFile && (
                    <Alert
                      message="数据集已加载"
                      description={
                        <div>
                          <Text strong>
                            <FileTextOutlined /> {uploadedFile.name}
                          </Text>
                          <br />
                          <Text type="secondary">
                            共加载 {testCases.length} 个测试用例
                          </Text>
                        </div>
                      }
                      type="success"
                      showIcon
                    />
                  )}
                </Space>
              </Form.Item>

              <Form.Item style={{ marginBottom: 0, textAlign: 'center' }}>
                <Space size="large" direction="vertical" style={{ width: '100%' }}>
                  {testCases.length === 0 && !testRunning && (
                    <Alert
                      message="请先上传数据集"
                      description="请在上方选择并上传包含测试用例的数据集文件（支持.txt, .csv, .json格式）"
                      type="warning"
                      showIcon
                    />
                  )}
                  <Space size="large">
                    <Button 
                      type="primary" 
                      htmlType="submit"
                      loading={loading}
                      disabled={testRunning || testCases.length === 0}
                      icon={<PlayCircleOutlined />}
                      size="large"
                    >
                      开始批量对抗样本生成
                    </Button>
                    {testRunning && (
                      <Button 
                        danger
                        onClick={handleStopTest}
                        icon={<StopOutlined />}
                        size="large"
                      >
                        停止测试
                      </Button>
                    )}
                  </Space>
                </Space>
              </Form.Item>
            </Form>
          </Card>

          {testResults && (
            <Card title="生成结果" style={{ marginTop: '16px' }}>
              <Row gutter={16} style={{ marginBottom: '16px' }}>
                <Col span={6}>
                  <Statistic title="总生成数" value={testResults.total} />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="成功数" 
                    value={testResults.completed} 
                    valueStyle={{ color: '#3f8600' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="失败数" 
                    value={testResults.failed} 
                    valueStyle={{ color: '#cf1322' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="成功率" 
                    value={testResults.success_rate} 
                    precision={1}
                    suffix="%" 
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Col>
              </Row>

              <div style={{ textAlign: 'right', marginBottom: '16px' }}>
                <Button 
                  icon={<DownloadOutlined />}
                  onClick={downloadResults}
                >
                  下载结果
                </Button>
              </div>

              <Table
                columns={columns}
                dataSource={testResults.results}
                rowKey="id"
                pagination={{ pageSize: 10 }}
                size="small"
              />
            </Card>
          )}

          {/* 详情模态框 */}
          <Modal
            title="测试用例详情"
            open={detailModalVisible}
            onCancel={() => {
              setDetailModalVisible(false);
              setSelectedTestCase(null);
            }}
            footer={null}
            width={1200}
          >
            {selectedTestCase && (
              <div>
                <Descriptions bordered column={2} style={{ marginBottom: '16px' }}>
                  <Descriptions.Item label="测试用例ID">
                    {selectedTestCase.id}
                  </Descriptions.Item>
                  <Descriptions.Item label="状态">
                    <Tag color={selectedTestCase.status === 'completed' ? 'success' : 'error'}>
                      {selectedTestCase.status === 'completed' ? '完成' : '失败'}
                    </Tag>
                  </Descriptions.Item>
                  {selectedTestCase.result && (
                    <>
                      <Descriptions.Item label="查询次数">
                        {selectedTestCase.result.query_times || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="时间成本">
                        {selectedTestCase.result.time_cost ? `${selectedTestCase.result.time_cost.toFixed(2)}秒` : '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="程序长度">
                        {selectedTestCase.result.program_length || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="标识符数量">
                        {selectedTestCase.result.identifier_num || '-'}
                      </Descriptions.Item>
                    </>
                  )}
                </Descriptions>

                <Tabs defaultActiveKey="code">
                  <Tabs.TabPane tab="代码对比" key="code">
                    <Row gutter={16}>
                      <Col span={12}>
                        <Card 
                          title="原始代码"
                          extra={
                            <Button 
                              type="text" 
                              icon={<CopyOutlined />} 
                              size="small"
                              onClick={() => handleCopy(selectedTestCase.result?.original_code || selectedTestCase.code || '', 'original')}
                              style={{ 
                                color: copiedType === 'original' ? '#52c41a' : undefined,
                                fontWeight: copiedType === 'original' ? 'bold' : 'normal'
                              }}
                            >
                              {copiedType === 'original' ? '已复制' : '复制'}
                            </Button>
                          }
                        >
                          <pre style={{ 
                            background: '#f5f5f5', 
                            padding: '12px', 
                            borderRadius: '4px',
                            fontSize: '13px',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-all',
                            margin: 0,
                            maxHeight: '400px',
                            overflow: 'auto'
                          }}>
                            {selectedTestCase.result?.original_code || selectedTestCase.code || '暂无数据'}
                          </pre>
                        </Card>
                      </Col>
                      <Col span={12}>
                        <Card 
                          title="对抗代码"
                          extra={
                            <Button 
                              type="text" 
                              icon={<CopyOutlined />} 
                              size="small"
                              onClick={() => handleCopy(selectedTestCase.result?.adversarial_code || '', 'adversarial')}
                              style={{ 
                                color: copiedType === 'adversarial' ? '#52c41a' : undefined,
                                fontWeight: copiedType === 'adversarial' ? 'bold' : 'normal'
                              }}
                            >
                              {copiedType === 'adversarial' ? '已复制' : '复制'}
                            </Button>
                          }
                        >
                          {selectedTestCase.result?.adversarial_code ? (
                            <pre style={{ 
                              background: '#f5f5f5', 
                              padding: '12px', 
                              borderRadius: '4px',
                              fontSize: '13px',
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-all',
                              margin: 0,
                              maxHeight: '400px',
                              overflow: 'auto',
                              color: '#52c41a'
                            }}>
                              {selectedTestCase.result.adversarial_code}
                            </pre>
                          ) : (
                            <Alert message="攻击失败，无对抗代码生成" type="warning" />
                          )}
                        </Card>
                      </Col>
                    </Row>
                  </Tabs.TabPane>
                  <Tabs.TabPane tab="标识符替换" key="replacements">
                    {selectedTestCase.result?.replaced_identifiers ? (
                      <Table
                        columns={[
                          {
                            title: '原始标识符',
                            dataIndex: 'original',
                            key: 'original',
                            render: (text: string) => <Text code>{text}</Text>
                          },
                          {
                            title: '对抗标识符',
                            dataIndex: 'adversarial',
                            key: 'adversarial',
                            render: (text: string) => <Text code style={{ color: '#52c41a' }}>{text}</Text>
                          }
                        ]}
                        dataSource={parseIdentifierReplacements(selectedTestCase.result.replaced_identifiers)}
                        pagination={false}
                        size="small"
                        rowKey={(record, index) => `${record.original}-${index}`}
                      />
                    ) : (
                      <Alert message="无标识符替换信息" type="info" />
                    )}
                  </Tabs.TabPane>
                </Tabs>
              </div>
            )}
          </Modal>
        </Col>

        <Col span={8}>
          <Card title="生成状态">
            {testRunning ? (
              <div>
                <Progress 
                  percent={taskProgress} 
                  status="active"
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
                <div style={{ marginTop: '16px', textAlign: 'center' }}>
                  <Alert
                    message={taskStatus}
                    type="info"
                    showIcon
                  />
                </div>
                {currentTaskId && (
                  <div style={{ marginTop: '16px', fontSize: '12px', color: '#666' }}>
                    任务ID: {currentTaskId}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', color: '#999' }}>
                <PlayCircleOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                <div>暂无运行中的生成任务</div>
              </div>
            )}
          </Card>

          <Card title="使用说明" style={{ marginTop: '16px' }}>
            <div>
              <h4>支持的文件格式</h4>
              <ul>
                <li><Text code>.txt</Text> - 每行一个测试用例</li>
                <li><Text code>.csv</Text> - CSV格式，包含代码列</li>
                <li><Text code>.json</Text> - JSON格式，包含测试用例数组</li>
              </ul>
              
              <h4>生成流程</h4>
              <ol>
                <li>选择测试模型和测试类型</li>
                <li>上传包含测试用例的数据集</li>
                <li>配置并发数量和其他参数</li>
                <li>开始批量对抗样本生成</li>
                <li>查看生成结果和下载报告</li>
              </ol>
            </div>
      </Card>
        </Col>
      </Row>
    </div>
  );
};

export default BatchTesting;
