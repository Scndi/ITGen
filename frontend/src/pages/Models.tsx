import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Table, 
  Button, 
  Modal, 
  Form, 
  Input, 
  Select, 
  message, 
  Space, 
  Tag, 
  Popconfirm,
  Typography,
  Row,
  Col,
  Statistic
} from 'antd';
import { 
  PlusOutlined, 
  DeleteOutlined, 
  PlayCircleOutlined, 
  InfoCircleOutlined 
} from '@ant-design/icons';
import { adminAPI } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

interface Model {
  id: string;
  model_name: string;
  model_type?: string;
  description: string;
  model_path: string;
  tokenizer_path: string;
  max_length: number;
  supported_tasks: string[];
  status: string;
  is_predefined: boolean;
}

const Models: React.FC = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    setLoading(true);
    try {
      const response = await adminAPI.getAllModels();
      if (response.success) {
        setModels(response.models || []);
      } else {
        message.error(response.message || '获取模型列表失败');
      }
    } catch (error) {
      message.error('获取模型列表失败');
      console.error('Error fetching models:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddModel = async (values: any) => {
    try {
      const response = await adminAPI.createModel(values);
      if (response.success) {
        message.success('模型添加成功');
        setModalVisible(false);
        form.resetFields();
        fetchModels();
      } else {
        message.error(response.message || '模型添加失败');
      }
    } catch (error) {
      message.error('模型添加失败');
      console.error('Error adding model:', error);
    }
  };

  const handleDeleteModel = async (modelId: string) => {
    try {
      const response = await adminAPI.deleteModel(parseInt(modelId));
      if (response.success) {
        message.success('模型删除成功');
        fetchModels();
      } else {
        message.error(response.message || '模型删除失败');
      }
    } catch (error) {
      message.error('模型删除失败');
      console.error('Error deleting model:', error);
    }
  };

  const handleTestModel = async (model: Model) => {
    try {
      const testData = {
        task_type: 'clone_detection',
        test_code: 'def test_function():\n    return "test"'
      };
      
      const response = await adminAPI.testModel(parseInt(model.id), testData);
      if (response.success) {
        message.success(`模型测试成功: ${JSON.stringify(response.result)}`);
      } else {
        message.error(response.error || '模型测试失败');
      }
    } catch (error) {
      message.error('模型测试失败');
      console.error('Error testing model:', error);
    }
  };

  const columns = [
    {
      title: '模型名称',
      dataIndex: 'model_name',
      key: 'model_name',
      render: (text: string, record: Model) => (
        <Space>
          <span>{text}</span>
          {record.is_predefined && <Tag color="blue">预定义</Tag>}
        </Space>
      ),
    },
    {
      title: '模型类型',
      dataIndex: 'model_type',
      key: 'model_type',
      render: (value: string | undefined) => value || '-'
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '支持任务',
      dataIndex: 'supported_tasks',
      key: 'supported_tasks',
      render: (tasks: string[]) => (
        <Space wrap>
          {tasks.map(task => (
            <Tag key={task} color="green">{task}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '最大长度',
      dataIndex: 'max_length',
      key: 'max_length',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'available' ? 'green' : 'red'}>
          {status === 'available' ? '可用' : '不可用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Model) => (
        <Space>
          <Button 
            type="primary" 
            size="small" 
            icon={<PlayCircleOutlined />}
            onClick={() => handleTestModel(record)}
          >
            测试
          </Button>
          {!record.is_predefined && (
            <Popconfirm
              title="确定要删除这个模型吗？"
              onConfirm={() => handleDeleteModel(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button 
                danger 
                size="small" 
                icon={<DeleteOutlined />}
              >
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2} style={{ margin: 0 }}>
          模型管理
        </Title>
        <Button 
          type="primary" 
          icon={<PlusOutlined />}
          onClick={() => setModalVisible(true)}
        >
          添加模型
        </Button>
      </div>

      {/* 统计信息 */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总模型数"
              value={models.length}
              prefix={<InfoCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="可用模型"
              value={models.filter(m => m.status === 'available').length}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="预定义模型"
              value={models.filter(m => m.is_predefined).length}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="自定义模型"
              value={models.filter(m => !m.is_predefined).length}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 模型列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={models}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个模型`,
          }}
        />
      </Card>

      {/* 添加模型模态框 */}
      <Modal
        title="添加新模型"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleAddModel}
        >
          <Form.Item
            name="model_name"
            label="模型名称"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="请输入模型名称" />
          </Form.Item>

          <Form.Item
            name="model_type"
            label="模型类型"
            rules={[{ required: true, message: '请输入模型类型' }]}
          >
            <Input placeholder="例如: encoder / decoder / encoder-decoder 或自定义" />
          </Form.Item>

          <Form.Item
            name="description"
            label="模型描述"
            rules={[{ required: true, message: '请输入模型描述' }]}
          >
            <Input.TextArea rows={3} placeholder="请输入模型描述" />
          </Form.Item>

          <Form.Item
            name="model_path"
            label="模型路径"
            rules={[{ required: true, message: '请输入模型路径' }]}
          >
            <Input placeholder="例如: microsoft/codebert-base" />
          </Form.Item>

          <Form.Item
            name="tokenizer_path"
            label="分词器路径"
            rules={[{ required: true, message: '请输入分词器路径' }]}
          >
            <Input placeholder="例如: microsoft/codebert-base" />
          </Form.Item>

          <Form.Item
            name="max_length"
            label="最大长度"
            rules={[{ required: true, message: '请输入最大长度' }]}
          >
            <Input type="number" placeholder="512" />
          </Form.Item>

          <Form.Item
            name="supported_tasks"
            label="支持的任务"
            rules={[{ required: true, message: '请选择支持的任务' }]}
          >
            <Select
              mode="multiple"
              placeholder="请选择支持的任务"
              options={[
                { label: '克隆检测', value: 'clone_detection' },
                { label: '漏洞检测', value: 'vulnerability_detection' },
                { label: '代码摘要', value: 'code_summarization' },
                { label: '代码生成', value: 'code_generation' },
              ]}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                添加
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Models;
