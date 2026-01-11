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
  Badge,
  Tag,
  Spin,
  Timeline,
  Statistic,
  Descriptions,
  Tabs,
  Empty
} from 'antd';
import {
  PlayCircleOutlined,
  StopOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  CodeOutlined,
  ExperimentOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  TrophyOutlined,
  BugOutlined,
  AppstoreOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { apiService as ApiService } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;
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
}

const Attack: React.FC = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();

  // 状态管理
  const [models, setModels] = useState<any[]>([]);
  const [supportedMethods, setSupportedMethods] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskInfo, setTaskInfo] = useState<TaskInfo | null>(null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
  const [attackHistory, setAttackHistory] = useState<TaskInfo[]>([]);

  // 初始化数据
  useEffect(() => {
    fetchInitialData();
    fetchAttackHistory();
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, []);

  const fetchInitialData = async () => {
    console.log('🔄 开始加载初始数据...');
    try {
      // 并行获取数据
      const [modelsResponse, methodsResponse] = await Promise.all([
        ApiService.getModels(),
        ApiService.getSupportedAttackMethods()
      ]);

      console.log('📊 模型响应:', modelsResponse);
      console.log('⚔️ 方法响应:', methodsResponse);
      console.log('🔍 响应状态:', {
        modelsSuccess: modelsResponse.success,
        methodsSuccess: methodsResponse.success,
        modelsCount: modelsResponse.data?.length || 0,
        methodsCount: methodsResponse.methods?.length || 0
      });

      if (modelsResponse.success) {
        setModels(modelsResponse.data);
        console.log('✅ 成功加载模型列表:', modelsResponse.data.length, '个模型');
      } else {
        console.error('❌ 加载模型失败:', modelsResponse);
      }

      if (methodsResponse.success) {
        setSupportedMethods(methodsResponse.methods || []);
        console.log('✅ 成功加载攻击方法列表:', methodsResponse.methods?.length, '个方法');
      } else {
        console.error('❌ 加载攻击方法失败:', methodsResponse);
      }
    } catch (error) {
      console.error('Error fetching initial data:', error);
      message.error('加载数据失败');
    }
  };

  const fetchAttackHistory = async () => {
    try {
      const response = await ApiService.getTasks({
        task_type: 'single_attack',
        limit: 10
      });
      if (response.success) {
        setAttackHistory(response.tasks || []);
      }
    } catch (error) {
      console.error('Error fetching attack history:', error);
    }
  };

  // 开始攻击
  const handleStartAttack = async (values: any) => {
    console.log('🔥 handleStartAttack 函数被调用，表单值:', values);
    console.log('📋 表单验证通过，开始处理攻击请求');
    setLoading(true);

    try {
      console.log('🚀 发送攻击请求到后端...');

      // 构建请求数据
      console.log('🔍 原始表单数据 values:', JSON.stringify(values, null, 2));
      console.log('🔍 values.code1:', values.code1);
      console.log('🔍 values.code1 类型:', typeof values.code1);
      console.log('🔍 values.code2:', values.code2);
      console.log('🔍 values.code2 类型:', typeof values.code2);
      console.log('🔍 values.method:', values.method);
      console.log('🔍 values keys:', Object.keys(values));

      const attackData = {
        code_data: {
          code1: values.code1 || '',
          code2: values.code2 || ''
        },
        method: values.method || 'itgen',
        model_name: values.model_name || 'codebert',
        task_type: 'clone-detection'
      };

      console.log('📤 构建的请求数据:', JSON.stringify(attackData, null, 2));
      console.log('📤 code_data.code1 长度:', attackData.code_data.code1?.length || 0);
      console.log('📤 code_data.code2 长度:', attackData.code_data.code2?.length || 0);

      // 发送攻击请求到后端
      const response = await ApiService.startAttack(attackData);

      if (!response.success) {
        throw new Error(response.error || '攻击请求失败');
      }

      const taskId = response.task_id;
      console.log('✅ 后端已接收攻击请求，任务ID:', taskId);

      // 创建前端任务状态
      const newTask: TaskInfo = {
        id: taskId,
        task_type: 'single_attack',
        sub_task_type: values.method,
        status: 'pending',
        progress: 0,
        progress_message: '任务已提交，等待执行...',
        created_at: new Date().toISOString()
      };

      setTaskInfo(newTask);
      message.success(`攻击任务已提交！任务ID: ${taskId}`);

      // 开始轮询任务状态
      startTaskPolling(taskId);
    } catch (error: any) {
      console.error('攻击启动失败:', error);
      message.error(`攻击启动失败: ${error.message || '未知错误'}`);
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
        const response = await ApiService.getTask(taskId);
        
        // 检查任务是否存在
        if (!response.success && (response.task_not_found || response.error === '任务不存在')) {
          // 任务不存在，停止轮询
          isPolling = false;
          if (currentInterval) {
            clearInterval(currentInterval);
            currentInterval = null;
          }
          setPollingInterval(null);
          message.warning('任务不存在，已停止轮询');
          setTaskInfo(null);
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
              message.success('攻击任务已完成！');
            } else if (updatedTask.status === 'failed') {
              message.error(`攻击任务失败: ${updatedTask.error_message || '未知错误'}`);
            } else if (updatedTask.status === 'cancelled') {
              message.info('任务已取消');
            }

            // 刷新历史记录
            fetchAttackHistory();
            return; // 任务完成，不再继续轮询
          }
        }
      } catch (error: any) {
        console.error('轮询任务状态失败:', error);
        
        // 如果是404错误（任务不存在），停止轮询
        if (error.response?.status === 404 || error.response?.data?.task_not_found) {
          isPolling = false;
          if (currentInterval) {
            clearInterval(currentInterval);
            currentInterval = null;
          }
          setPollingInterval(null);
          message.warning('任务不存在，已停止轮询');
          setTaskInfo(null);
        }
      }
    };

    // 立即执行一次，然后每1秒轮询一次，让进度更新更流畅
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
    }, 1000);
    setPollingInterval(currentInterval);
  }, [pollingInterval]);

  // 取消任务
  const handleCancelTask = async () => {
    if (!taskInfo) {
      console.log('⚠️ 没有任务信息，无法取消');
      return;
    }

    console.log('🛑 尝试取消任务:', taskInfo.id, '当前状态:', taskInfo.status);

    try {
      const response = await ApiService.cancelTask(taskInfo.id, '用户主动取消');
      console.log('📡 取消任务响应:', response);

      if (response.success) {
        message.success('任务已取消');
        setTaskInfo(prev => prev ? { ...prev, status: 'cancelled' } : null);
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        console.log('✅ 任务取消成功');
      } else {
        console.error('❌ 服务器返回取消失败:', response);
        message.error('取消任务失败');
      }
    } catch (error: any) {
      console.error('❌ 取消任务请求失败:', error);
      console.error('🔍 错误详情:', {
        message: error.message,
        status: error.response?.status,
        responseData: error.response?.data
      });
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
      navigate('/attack/result', {
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
          <ThunderboltOutlined style={{ marginRight: '16px' }} />
          模型鲁棒性攻击测试
        </Title>
        <Text type="secondary" style={{ fontSize: '16px' }}>
          评估代码语言模型对对抗性攻击的防御能力
        </Text>
      </div>

      <Tabs defaultActiveKey="attack" type="card" style={{ background: 'white', borderRadius: '8px' }}>
        {/* 攻击配置标签页 */}
        <TabPane
          tab={
            <span>
              <ExperimentOutlined />
              攻击配置
            </span>
          }
          key="attack"
        >
          <Row gutter={24}>
            {/* 配置表单 */}
            <Col span={12}>
              <Card
                title={
                  <span>
                    <CodeOutlined style={{ marginRight: '8px' }} />
                    攻击参数配置
                  </span>
                }
                style={{ height: '100%' }}
              >
                <Form
                  form={form}
                  layout="vertical"
                  onFinish={handleStartAttack}
                  onFinishFailed={(errorInfo) => {
                    console.error('❌ 表单验证失败:', errorInfo);
                    message.error('请填写所有必需字段');
                  }}
                  initialValues={{
                    method: 'itgen',
                    task_type: 'clone-detection',
                    language: 'python',
                    attack_strategy: 'identifier_substitution',
                    max_modifications: 5,
                    max_substitutions: 10,
                    max_query_times: 100,
                    time_limit: 60,
                    label: '1'
                  }}
                >
                  <Row gutter={16}>
                    <Col span={12}>
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
                    <Col span={12}>
                      <Form.Item
                        name="method"
                        label="攻击算法"
                        rules={[{ required: true, message: '请选择攻击算法' }]}
                      >
                        <Select
                          placeholder="选择算法"
                          suffixIcon={<BugOutlined />}
                          size="large"
                        >
                          {supportedMethods.map(method => (
                            <Option key={method} value={method}>
                              <Tag color="blue">{method.toUpperCase()}</Tag>
                            </Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
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
                    <Col span={12}>
                      <Form.Item
                        name="language"
                        label="编程语言"
                        rules={[{ required: true, message: '请选择编程语言' }]}
                      >
                        <Select placeholder="选择语言" size="large">
                          <Option value="python">🐍 Python</Option>
                          <Option value="java">☕ Java</Option>
                          <Option value="c">⚡ C/C++</Option>
                          <Option value="javascript">🟨 JavaScript</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="attack_strategy"
                        label="攻击策略"
                        rules={[{ required: true, message: '请选择攻击策略' }]}
                      >
                        <Select placeholder="选择策略" size="large">
                          <Option value="identifier_substitution">标识符替换</Option>
                          <Option value="equivalent_transform">等价变换</Option>
                          <Option value="hybrid">混合策略</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="label"
                        label="真实标签"
                        rules={[{ required: true, message: '请选择真实标签' }]}
                      >
                        <Select placeholder="选择标签" size="large">
                          <Option value="1">正例 (相似)</Option>
                          <Option value="0">负例 (不相似)</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>

                  {/* 高级参数折叠 */}
                  <Divider orientation="left">高级参数</Divider>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item name="max_modifications" label="最大修改次数">
                        <Input type="number" placeholder="5" size="large" suffix="次" />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="max_substitutions" label="最大替换数">
                        <Input type="number" placeholder="10" size="large" suffix="个" />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="max_query_times" label="最大查询次数">
                        <Input type="number" placeholder="100" size="large" suffix="次" />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="time_limit" label="超时时间">
                        <Input type="number" placeholder="60" size="large" suffix="秒" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="操作">
                        <Space>
                          <Button
                            type="primary"
                            htmlType="submit"
                            loading={loading}
                            size="large"
                            icon={<PlayCircleOutlined />}
                            disabled={!!taskInfo && ['pending', 'running'].includes(taskInfo.status)}
                            onClick={() => {
                              console.log('🖱️ 开始攻击按钮被点击');
                              console.log('📊 当前表单状态:', {
                                modelsCount: models.length,
                                supportedMethodsCount: supportedMethods.length,
                                hasTaskInfo: !!taskInfo,
                                taskStatus: taskInfo?.status
                              });
                            }}
                          >
                            {loading ? '启动中...' : '开始攻击'}
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

            {/* 代码输入 */}
            <Col span={12}>
              <Card
                title={
                  <span>
                    <CodeOutlined style={{ marginRight: '8px' }} />
                    测试代码输入
                  </span>
                }
                style={{ height: '100%' }}
              >
                <Tabs defaultActiveKey="code1" type="card" size="small">
                  <TabPane tab="代码片段 1" key="code1">
                    <Form.Item
                      name="code1"
                      rules={[{ required: true, message: '请输入代码片段1' }]}
                    >
                      <TextArea
                        placeholder="请输入第一个代码片段..."
                        rows={12}
                        style={{ fontFamily: 'Monaco, Consolas, monospace', fontSize: '14px' }}
                      />
                    </Form.Item>
                  </TabPane>
                  <TabPane tab="代码片段 2" key="code2">
                    <Form.Item
                      name="code2"
                      rules={[{ required: true, message: '请输入代码片段2' }]}
                    >
                      <TextArea
                        placeholder="请输入第二个代码片段..."
                        rows={12}
                        style={{ fontFamily: 'Monaco, Consolas, monospace', fontSize: '14px' }}
                      />
                    </Form.Item>
                  </TabPane>
                </Tabs>
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
                  <Descriptions title="攻击结果概览" bordered column={2}>
                    <Descriptions.Item label="攻击成功">
                      <Tag color={taskInfo.result.success ? 'success' : 'error'}>
                        {taskInfo.result.success ? '是' : '否'}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="查询次数">
                      {taskInfo.result.query_count || 'N/A'}
                    </Descriptions.Item>
                    <Descriptions.Item label="执行时间">
                      {taskInfo.result.execution_time ? `${taskInfo.result.execution_time.toFixed(2)}s` : 'N/A'}
                    </Descriptions.Item>
                    <Descriptions.Item label="置信度变化">
                      {taskInfo.result.confidence_change ? `${taskInfo.result.confidence_change.toFixed(4)}` : 'N/A'}
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
              {attackHistory.map(task => (
                <Timeline.Item
                  key={task.id}
                  color={getStatusInfo(task.status).color}
                  dot={getStatusInfo(task.status).icon}
                >
                  <div style={{ padding: '8px 0' }}>
                    <Space>
                      <Tag color="blue">{task.sub_task_type?.toUpperCase()}</Tag>
                      <Text strong>{task.id.slice(0, 8)}...</Text>
                      <Text type="secondary">
                        {new Date(task.created_at).toLocaleString()}
                      </Text>
                      {task.status === 'completed' && task.result?.success && (
                        <TrophyOutlined style={{ color: '#52c41a' }} />
                      )}
                    </Space>
                    <div style={{ marginTop: '8px' }}>
                      <Text>
                        状态: {getStatusInfo(task.status).text}
                        {task.result && ` | 查询次数: ${task.result.query_count || 'N/A'}`}
                      </Text>
                    </div>
                  </div>
                </Timeline.Item>
              ))}
            </Timeline>
            {attackHistory.length === 0 && (
              <Empty description="暂无历史记录" />
            )}
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Attack;
