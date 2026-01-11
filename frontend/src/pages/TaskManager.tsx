import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  message,
  Badge,
  Typography,
  Row,
  Col,
  Statistic,
  Tabs,
  Progress,
  Descriptions,
  Empty,
  Modal,
  Select,
  Input,
  Form
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  StopOutlined,
  EyeOutlined,
  DeleteOutlined,
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  AppstoreOutlined,
  PlayCircleOutlined,
  DatabaseOutlined
} from '@ant-design/icons';
import { apiService as ApiService } from '../services/api';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;
const { confirm } = Modal;

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
  model_name?: string;
  dataset_name?: string;
  queue_name?: string;
  priority?: number;
}

const TaskManager: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<any>({});
  const [queueStatus, setQueueStatus] = useState<any>({});
  const [selectedTask, setSelectedTask] = useState<TaskInfo | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [filters, setFilters] = useState({
    task_type: '',
    status: '',
    model_name: ''
  });
  const [hasRunningTasks, setHasRunningTasks] = useState(false);

  // 初始化数据
  useEffect(() => {
    fetchTasks();
    fetchStats();
    fetchQueueStatus();

    // 设置轮询更新任务状态
    const interval = setInterval(() => {
      fetchTasks();
      fetchStats();
      fetchQueueStatus();
    }, 5000); // 每5秒更新一次

    return () => clearInterval(interval);
  }, []);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const response = await ApiService.getTasks({
        ...filters,
        limit: 100
      });
      if (response.success) {
        const taskList = response.tasks || [];
        
        // 调试：打印任务类型分布
        const taskTypes: { [key: string]: number } = {};
        taskList.forEach((task: TaskInfo) => {
          const type = task.task_type || 'unknown';
          taskTypes[type] = (taskTypes[type] || 0) + 1;
        });
        console.log('📊 任务列表:', {
          total: taskList.length,
          taskTypes,
          filters
        });
        
        setTasks(taskList);

        // 检查是否有运行中的任务
        const runningTasks = taskList.filter((task: TaskInfo) => task.status === 'running');
        setHasRunningTasks(runningTasks.length > 0);

        // 如果有运行中的任务，显示通知
        if (runningTasks.length > 0 && !hasRunningTasks) {
          message.info(`${runningTasks.length} 个任务正在执行中`);
        }
      }
    } catch (error) {
      console.error('❌ 获取任务列表失败:', error);
      message.error('获取任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await ApiService.getTaskStatistics(7); // 7天统计
      if (response.success) {
        setStats(response.stats || {});
      }
    } catch (error) {
      console.error('获取统计信息失败:', error);
    }
  };

  const fetchQueueStatus = async () => {
    try {
      const response = await ApiService.getQueueStatus();
      if (response.success) {
        setQueueStatus(response.queues || {});
      }
    } catch (error) {
      console.error('获取队列状态失败:', error);
    }
  };

  // 获取状态信息
  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'pending':
        return { icon: <ClockCircleOutlined />, color: 'orange', text: '等待中', badge: 'processing' };
      case 'running':
        return { icon: <PlayCircleOutlined />, color: 'blue', text: '执行中', badge: 'processing' };
      case 'completed':
        return { icon: <CheckCircleOutlined />, color: 'green', text: '已完成', badge: 'success' };
      case 'failed':
        return { icon: <CloseCircleOutlined />, color: 'red', text: '失败', badge: 'error' };
      case 'cancelled':
        return { icon: <StopOutlined />, color: 'gray', text: '已取消', badge: 'default' };
      default:
        return { icon: <ClockCircleOutlined />, color: 'default', text: status, badge: 'default' };
    }
  };

  // 获取任务类型标签
  const getTaskTypeTag = (task: TaskInfo) => {
    const typeMap: { [key: string]: { color: string; text: string } } = {
      'single_attack': { color: 'red', text: '单次攻击' },
      'batch_attack': { color: 'orange', text: '批量攻击' },
      'generate_report': { color: 'blue', text: '生成报告' },
      'evaluate_model': { color: 'purple', text: '模型评估' },
      'finetune': { color: 'green', text: '微调训练' }
    };

    const type = typeMap[task.task_type] || { color: 'default', text: task.task_type };
    return <Tag color={type.color}>{type.text}</Tag>;
  };

  // 取消任务
  const handleCancelTask = async (taskId: string) => {
    confirm({
      title: '确认取消任务',
      content: '确定要取消这个任务吗？取消后无法恢复。',
      onOk: async () => {
        try {
          const response = await ApiService.cancelTask(taskId);
          if (response.success) {
            message.success('任务已取消');
            fetchTasks();
            fetchStats();
          } else {
            message.error('取消任务失败');
          }
        } catch (error) {
          message.error('取消任务失败');
        }
      }
    });
  };

  // 查看任务详情/结果
  const handleViewDetail = async (task: TaskInfo) => {
    try {
      // 如果任务已完成且有结果，跳转到相应的结果页面
      if (task.status === 'completed' && task.result) {
        let response: any;
        let statusData: any;
        
        // 根据任务类型使用不同的API获取任务详情
        if (task.task_type === 'batch_attack') {
          // 批量攻击任务使用批量测试状态API
          response = await ApiService.getBatchTestingStatus(task.id);
          if (response.success && response.status && response.status.result) {
            statusData = response.status;
          }
        } else {
          // 其他任务使用通用getTask API
          response = await ApiService.getTask(task.id);
          if (response.success && response.status && response.status.result) {
            statusData = response.status;
          }
        }
        
        if (response && response.success && statusData && statusData.result) {
          // 根据任务类型跳转到相应的结果页面
          if (task.task_type === 'single_attack') {
            navigate('/attack/result', {
              state: {
                taskId: task.id,
                result: statusData.result,
                taskInfo: statusData
              }
            });
          } else if (task.task_type === 'generate_report') {
            navigate('/evaluation/result', {
              state: {
                taskId: task.id,
                result: statusData.result,
                taskInfo: statusData
              }
            });
          } else if (task.task_type === 'finetune') {
            navigate('/finetuning/result', {
              state: {
                taskId: task.id,
                result: statusData.result,
                taskInfo: statusData
              }
            });
          } else if (task.task_type === 'batch_attack') {
            // 批量攻击结果跳转到批量测试页面
            navigate('/batch-testing', {
              state: {
                taskId: task.id,
                result: statusData.result,
                taskInfo: statusData
              }
            });
          } else {
            // 对于其他类型的任务，显示详情模态框
            setSelectedTask(statusData);
            setDetailModalVisible(true);
          }
        } else {
          message.error('获取任务结果失败');
        }
      } else {
        // 对于未完成的任务或没有结果的任务，显示详情模态框
        const response = await ApiService.getTask(task.id);
        if (response.success) {
          setSelectedTask(response.status);
          setDetailModalVisible(true);
        } else {
          message.error('获取任务详情失败');
        }
      }
    } catch (error) {
      console.error('查看任务详情失败:', error);
      message.error('获取任务详情失败');
    }
  };

  // 表格列配置
  const columns = [
    {
      title: '任务ID',
      dataIndex: 'id',
      key: 'id',
      width: 120,
      render: (id: string) => (
        <Text copyable={{ text: id }} style={{ fontFamily: 'monospace' }}>
          {id.slice(0, 8)}...
        </Text>
      )
    },
    {
      title: '类型',
      key: 'type',
      width: 120,
      render: (task: TaskInfo) => getTaskTypeTag(task)
    },
    {
      title: '子类型',
      dataIndex: 'sub_task_type',
      key: 'sub_task_type',
      width: 100,
      render: (subType: string) => (
        <Tag color="cyan">{subType?.toUpperCase()}</Tag>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Badge
          status={getStatusInfo(status).badge as any}
          text={getStatusInfo(status).text}
        />
      )
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress: number, task: TaskInfo) => (
        <div>
          <Progress
            percent={progress}
            size="small"
            status={task.status === 'running' ? 'active' : task.status === 'completed' ? 'success' : 'normal'}
          />
          {task.progress_message && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {task.progress_message}
            </Text>
          )}
        </div>
      )
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 100,
      render: (model: string) => model ? <Tag>{model}</Tag> : '-'
    },
    {
      title: '数据集',
      dataIndex: 'dataset_name',
      key: 'dataset_name',
      width: 100,
      render: (dataset: string) => dataset ? <Tag color="geekblue">{dataset}</Tag> : '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (task: TaskInfo) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(task)}
          >
            详情
          </Button>
          {['pending', 'running'].includes(task.status) && (
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => handleCancelTask(task.id)}
            >
              取消
            </Button>
          )}
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px', textAlign: 'center' }}>
        <Title level={1} style={{ marginBottom: '8px', color: hasRunningTasks ? '#faad14' : '#1890ff' }}>
          {hasRunningTasks ? (
            <PlayCircleOutlined style={{ marginRight: '16px' }} />
          ) : (
            <CheckCircleOutlined style={{ marginRight: '16px' }} />
          )}
          任务管理中心
          {hasRunningTasks && (
            <Badge
              count="运行中"
              style={{ backgroundColor: '#faad14', marginLeft: '16px' }}
            />
          )}
        </Title>
        <Text type="secondary" style={{ fontSize: '16px' }}>
          {hasRunningTasks
            ? `${tasks.filter(t => t.status === 'running').length} 个任务正在执行中`
            : '统一管理所有异步任务的状态和结果'
          }
        </Text>
      </div>

      <Tabs defaultActiveKey="tasks" type="card" style={{ background: 'white', borderRadius: '8px' }}>
        {/* 任务列表标签页 */}
        <TabPane
          tab={
            <span>
              <ClockCircleOutlined />
              任务列表 ({tasks.length})
            </span>
          }
          key="tasks"
        >
          {/* 筛选器 */}
          <Card style={{ marginBottom: '16px' }}>
            <Row gutter={16} align="middle">
              <Col span={4}>
                <Select
                  placeholder="任务类型"
                  allowClear
                  style={{ width: '100%' }}
                  onChange={(value) => setFilters(prev => ({ ...prev, task_type: value }))}
                >
                  <Option value="single_attack">单次攻击</Option>
                  <Option value="batch_attack">批量攻击</Option>
                  <Option value="generate_report">生成报告</Option>
                  <Option value="evaluate_model">模型评估</Option>
                  <Option value="finetune">微调训练</Option>
                </Select>
              </Col>
              <Col span={4}>
                <Select
                  placeholder="任务状态"
                  allowClear
                  style={{ width: '100%' }}
                  onChange={(value) => setFilters(prev => ({ ...prev, status: value }))}
                >
                  <Option value="pending">等待中</Option>
                  <Option value="running">执行中</Option>
                  <Option value="completed">已完成</Option>
                  <Option value="failed">失败</Option>
                  <Option value="cancelled">已取消</Option>
                </Select>
              </Col>
              <Col span={4}>
                <Input
                  placeholder="模型名称"
                  onChange={(e) => setFilters(prev => ({ ...prev, model_name: e.target.value }))}
                />
              </Col>
              <Col span={12}>
                <Space>
                  <Button type="primary" icon={<SearchOutlined />} onClick={fetchTasks}>
                    搜索
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={fetchTasks}>
                    刷新
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>

          {/* 任务表格 */}
          <Card>
            <Table
              columns={columns}
              dataSource={tasks}
              loading={loading}
              rowKey="id"
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
              }}
              scroll={{ x: 1200 }}
            />
          </Card>
        </TabPane>

        {/* 统计信息标签页 */}
        <TabPane
          tab={
            <span>
              <CheckCircleOutlined />
              统计信息
            </span>
          }
          key="stats"
        >
          <Row gutter={24}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="总任务数"
                  value={stats.total || 0}
                  prefix={<ClockCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="运行中"
                  value={stats.by_status?.running || 0}
                  prefix={<PlayCircleOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="已完成"
                  value={stats.by_status?.completed || 0}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="失败任务"
                  value={stats.by_status?.failed || 0}
                  prefix={<CloseCircleOutlined />}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={24} style={{ marginTop: '24px' }}>
            <Col span={12}>
              <Card title="任务类型分布">
                {stats.by_type ? (
                  Object.entries(stats.by_type).map(([type, count]) => (
                    <div key={type} style={{ marginBottom: '8px' }}>
                      <Text strong>{type}: </Text>
                      <Text>{count as number}</Text>
                    </div>
                  ))
                ) : (
                  <Empty description="暂无数据" />
                )}
              </Card>
            </Col>
            <Col span={12}>
              <Card title="性能指标">
                {stats.performance ? (
                  <div>
                    <div style={{ marginBottom: '8px' }}>
                      <Text strong>平均执行时间: </Text>
                      <Text>{stats.performance.avg_execution_time?.toFixed(2)}s</Text>
                    </div>
                    <div style={{ marginBottom: '8px' }}>
                      <Text strong>最短执行时间: </Text>
                      <Text>{stats.performance.min_execution_time}s</Text>
                    </div>
                    <div style={{ marginBottom: '8px' }}>
                      <Text strong>最长执行时间: </Text>
                      <Text>{stats.performance.max_execution_time}s</Text>
                    </div>
                  </div>
                ) : (
                  <Empty description="暂无数据" />
                )}
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 队列状态标签页 */}
        <TabPane
          tab={
            <span>
              <AppstoreOutlined />
              队列状态
            </span>
          }
          key="queues"
        >
          <Row gutter={24}>
            {Object.entries(queueStatus).map(([queueName, status]: [string, any]) => (
              <Col span={8} key={queueName}>
                <Card title={`${queueName} 队列`} style={{ height: '200px' }}>
                  <Statistic
                    title="活跃任务"
                    value={status.active_tasks || 0}
                    prefix={<DatabaseOutlined />}
                    valueStyle={{ color: '#1890ff' }}
                  />
                  <div style={{ marginTop: '16px' }}>
                    <Text>等待任务: {status.pending_tasks || 0}</Text>
                  </div>
                  <div style={{ marginTop: '8px' }}>
                    <Text>总任务数: {status.total_tasks || 0}</Text>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
          {Object.keys(queueStatus).length === 0 && (
            <Empty description="暂无队列信息" />
          )}
        </TabPane>
      </Tabs>

      {/* 任务详情模态框 */}
      <Modal
        title="任务详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        ]}
      >
        {selectedTask && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="任务ID" span={2}>
              <Text copyable>{selectedTask.id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="任务类型">
              {getTaskTypeTag(selectedTask)}
            </Descriptions.Item>
            <Descriptions.Item label="子任务类型">
              <Tag color="cyan">{selectedTask.sub_task_type?.toUpperCase()}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Badge
                status={getStatusInfo(selectedTask.status).badge as any}
                text={getStatusInfo(selectedTask.status).text}
              />
            </Descriptions.Item>
            <Descriptions.Item label="进度">
              <Progress percent={selectedTask.progress} size="small" />
            </Descriptions.Item>
            <Descriptions.Item label="模型">
              {selectedTask.model_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="数据集">
              {selectedTask.dataset_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="队列">
              {selectedTask.queue_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="优先级">
              {selectedTask.priority || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={2}>
              {new Date(selectedTask.created_at).toLocaleString()}
            </Descriptions.Item>
            {selectedTask.started_at && (
              <Descriptions.Item label="开始时间" span={2}>
                {new Date(selectedTask.started_at).toLocaleString()}
              </Descriptions.Item>
            )}
            {selectedTask.completed_at && (
              <Descriptions.Item label="完成时间" span={2}>
                {new Date(selectedTask.completed_at).toLocaleString()}
              </Descriptions.Item>
            )}
            {selectedTask.progress_message && (
              <Descriptions.Item label="进度消息" span={2}>
                {selectedTask.progress_message}
              </Descriptions.Item>
            )}
            {selectedTask.error_message && (
              <Descriptions.Item label="错误信息" span={2}>
                <Text type="danger">{selectedTask.error_message}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default TaskManager;
