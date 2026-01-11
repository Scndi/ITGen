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
  BarChartOutlined,
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

interface TestConfig {
  model_id: string;
  base_model: string;
  max_queries: number;
  timeout: number;
  attack_method: string;
  attack_strategy: string;
}

interface TestProgress {
  current_sample: number;
  total_samples: number;
  current_iteration: number;
  max_iterations: number;
  asr: number;
  ami: number;
  art: number;
  eta: string;
}

interface EvaluationResult {
  model_id: string;
  model_name: string;
  test_time: number;
  // 关键指标
  asr: number; // 攻击成功率
  ami: number; // 平均模型调用次数
  art: number; // 平均运行时间
  total_samples: number;
  successful_attacks: number;
  failed_attacks: number;
  identifier_replacements: number;
  test_logs: any[];
}

const Evaluation: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  // 状态管理
  const [models, setModels] = useState<any[]>([]);
  const [supportedMethods, setSupportedMethods] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskInfo, setTaskInfo] = useState<TaskInfo | null>(null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
  const [evaluationHistory, setEvaluationHistory] = useState<TaskInfo[]>([]);

  // 初始化数据
  useEffect(() => {
    fetchInitialData();
    fetchEvaluationHistory();
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

  const fetchEvaluationHistory = async () => {
    try {
      const response = await ApiService.getTasks({
        task_type: 'evaluation',
        limit: 10
      });
      if (response.success) {
        setEvaluationHistory(response.tasks || []);
      }
    } catch (error) {
      console.error('Error fetching evaluation history:', error);
    }
  };

  // 开始评估
  const handleStartEvaluation = async (values: any) => {
    setLoading(true);

    try {
      // 构造请求数据
      const evaluationData = {
        model_name: values.model_name,
        task_type: values.task_type || 'clone-detection',
        attack_methods: values.attack_methods || ['itgen', 'alert'],
        evaluation_metrics: values.evaluation_metrics || ['asr', 'ami', 'art'],
        dataset_name: values.dataset_name
      };

      console.log('🚀 开始评估任务:', evaluationData);

      // 调用后端API创建任务
      const response = await ApiService.startEvaluation(evaluationData);
      
      if (!response.success) {
        throw new Error(response.error || '创建评估任务失败');
      }

      const taskId = response.task_id;
      console.log('✅ 评估任务已创建:', taskId);

      // 设置任务信息并开始轮询
      const newTask: TaskInfo = {
        id: taskId,
        task_type: 'generate_report',
        sub_task_type: 'robustness_evaluation',
        status: 'pending',
        progress: 0,
        progress_message: '任务已创建，等待执行...',
        created_at: new Date().toISOString()
      };

      setTaskInfo(newTask);
      startTaskPolling(taskId);
      
      message.success('评估任务已创建，正在执行中...');
    } catch (error: any) {
      console.error('评估启动失败:', error);
      message.error(`评估启动失败: ${error.message || '未知错误'}`);
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
        const response = await ApiService.getEvaluationStatus(taskId);
        
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
              message.success('评估任务已完成！');
            } else if (updatedTask.status === 'failed') {
              message.error(`评估任务失败: ${updatedTask.error_message || '未知错误'}`);
            }

            // 刷新历史记录
            fetchEvaluationHistory();
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
        return { icon: <PlayCircleOutlined />, color: 'blue', text: '执行中' };
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
      navigate('/evaluation/result', {
        state: {
          taskId: taskInfo.id,
          result: taskInfo.result,
          taskInfo: taskInfo
        }
      });
    }
  };

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px', textAlign: 'center' }}>
        <Title level={1} style={{ marginBottom: '8px', color: '#1890ff' }}>
          <BarChartOutlined style={{ marginRight: '16px' }} />
          模型鲁棒性评估
        </Title>
        <Text type="secondary" style={{ fontSize: '16px' }}>
          全面评估代码语言模型对各种攻击算法的防御能力
        </Text>
      </div>

      <Tabs defaultActiveKey="evaluation" type="card" style={{ background: 'white', borderRadius: '8px' }}>
        {/* 评估配置标签页 */}
        <TabPane
          tab={
            <span>
              <ExperimentOutlined />
              评估配置
            </span>
          }
          key="evaluation"
        >
          <Row gutter={24}>
            {/* 配置表单 */}
            <Col span={24}>
              <Card
                title={
                  <span>
                    <ThunderboltOutlined style={{ marginRight: '8px' }} />
                    评估参数配置
                  </span>
                }
              >
                <Form
                  form={form}
                  layout="vertical"
                  onFinish={handleStartEvaluation}
                  initialValues={{
                    task_type: 'clone-detection',
                    attack_methods: ['itgen', 'alert'],
                    evaluation_metrics: ['asr', 'ami', 'art']
                  }}
                >
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item
                        name="model_name"
                        label="测试模型"
                        rules={[{ required: true, message: '请选择测试模型' }]}
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
                    <Col span={8}>
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
                    <Col span={8}>
                      <Form.Item
                        name="dataset_name"
                        label="数据集"
                        rules={[{ required: true, message: '请选择数据集' }]}
                      >
                        <Select placeholder="选择数据集" size="large">
                          <Option value="test-dataset">测试数据集</Option>
                          <Option value="validation-dataset">验证数据集</Option>
                          <Option value="benchmark-dataset">基准数据集</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="attack_methods"
                        label="攻击算法"
                        rules={[{ required: true, message: '请选择攻击算法' }]}
                      >
                        <Select
                          mode="multiple"
                          placeholder="选择攻击算法"
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
                      <Form.Item
                        name="evaluation_metrics"
                        label="评估指标"
                        rules={[{ required: true, message: '请选择评估指标' }]}
                      >
                        <Select
                          mode="multiple"
                          placeholder="选择评估指标"
                          size="large"
                          suffixIcon={<BarChartOutlined />}
                        >
                          <Option value="asr">
                            <Tag color="red">ASR</Tag> 攻击成功率
                          </Option>
                          <Option value="ami">
                            <Tag color="orange">AMI</Tag> 平均模型调用次数
                          </Option>
                          <Option value="art">
                            <Tag color="green">ART</Tag> 平均运行时间
                          </Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={24}>
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
                            {loading ? '启动中...' : '开始评估'}
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
                    <Text strong>执行进度</Text>
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
                  <Descriptions title="评估结果概览" bordered column={2}>
                    <Descriptions.Item label="攻击成功率 (ASR)">
                      <Text strong style={{ color: '#ff4d4f' }}>
                        {(taskInfo.result.asr * 100).toFixed(2)}%
                      </Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="平均模型调用次数 (AMI)">
                      <Text strong style={{ color: '#faad14' }}>
                        {taskInfo.result.ami?.toFixed(2) || 'N/A'}
                      </Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="平均运行时间 (ART)">
                      <Text strong style={{ color: '#52c41a' }}>
                        {taskInfo.result.art ? `${taskInfo.result.art.toFixed(2)}s` : 'N/A'}
                      </Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="测试样本数">
                      {taskInfo.result.total_samples || 'N/A'}
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
              {evaluationHistory.map(task => (
                <Timeline.Item
                  key={task.id}
                  color={getStatusInfo(task.status).color}
                  dot={getStatusInfo(task.status).icon}
                >
                  <div style={{ padding: '8px 0' }}>
                    <Space>
                      <Tag color="blue">{(task as any).model_name || task.task_type}</Tag>
                      <Text strong>{task.id.slice(0, 8)}...</Text>
                      <Text type="secondary">
                        {new Date(task.created_at).toLocaleString()}
                      </Text>
                      {task.status === 'completed' && task.result?.asr && (
                        <TrophyOutlined style={{ color: '#52c41a' }} />
                      )}
                    </Space>
                    <div style={{ marginTop: '8px' }}>
                      <Text>
                        状态: {getStatusInfo(task.status).text}
                        {task.result && ` | ASR: ${(task.result.asr * 100).toFixed(2)}%`}
                      </Text>
                    </div>
                  </div>
                </Timeline.Item>
              ))}
            </Timeline>
            {evaluationHistory.length === 0 && (
              <Empty description="暂无历史记录" />
            )}
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Evaluation;

