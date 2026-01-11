import React, { useState, useEffect } from 'react';
import {
  Card,
  Typography,
  Row,
  Col,
  Tag,
  Descriptions,
  Button,
  Divider,
  Alert,
  message
} from 'antd';
import { ArrowLeftOutlined, CopyOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Title, Text } = Typography;
const { Paragraph } = Typography;

const AttackResult: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [resultData, setResultData] = useState<any>(null);
  const [copiedType, setCopiedType] = useState<string>('');

  useEffect(() => {
    // 优先从路由state获取数据
    const stateData = location.state as any;
    if (stateData && stateData.result) {
      console.log('📦 从路由state加载攻击结果', stateData);
      console.log('🔍 stateData.result:', stateData.result);
      console.log('🔍 stateData.taskInfo:', stateData.taskInfo);
      console.log('🔍 stateData.taskInfo.parameters:', stateData.taskInfo?.parameters);

      // 构建config对象，从taskInfo中提取相关信息
      const taskInfo = stateData.taskInfo;
      const parameters = taskInfo?.parameters || {};
      const codeData = parameters.code_data || {};

      // 确保result中有原始代码和对抗代码，如果没有则从parameters中获取
      const result = { ...stateData.result };
      if (!result.original_code || result.original_code === '') {
        result.original_code = codeData.code1 || '';
        console.log('🔄 从parameters.code_data.code1获取原始代码:', result.original_code);
      }
      if (!result.adversarial_code || result.adversarial_code === '') {
        // 如果对抗代码为空，尝试从原始代码生成或使用code2
        result.adversarial_code = codeData.code2 || result.original_code || '';
        console.log('🔄 从parameters.code_data.code2获取对抗代码:', result.adversarial_code);
      }

      const config = {
        method: parameters.method || taskInfo?.sub_task_type,
        model_name: taskInfo?.model_name || parameters.model_name,
        model_id: taskInfo?.model_name || parameters.model_name,
        task_type: parameters.task_type || 'clone-detection',
        language: 'Python',  // 默认Python
        attack_strategy: 'identifier_rename',  // 默认标识符重命名
        ...parameters  // 保留其他参数
      };

      console.log('✅ 最终result数据:', result);
      console.log('✅ original_code:', result.original_code);
      console.log('✅ adversarial_code:', result.adversarial_code);

      setResultData({
        taskId: stateData.taskId,
        result: result,
        taskInfo: taskInfo,
        config: config
      });
      return;
    }

    // 备用：从sessionStorage获取攻击结果
    const storedData = sessionStorage.getItem('attackResult');
    if (storedData) {
      console.log('📦 从sessionStorage加载攻击结果');
      setResultData(JSON.parse(storedData));
    } else {
      console.warn('⚠️ 未找到攻击结果数据，重定向到攻击页面');
      message.warning('未找到攻击结果，请重新开始攻击');
      navigate('/attack');
    }
  }, [navigate, location.state]);

  const handleBack = () => {
    navigate('/attack');
  };

  const handleCopy = async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedType(type);
      message.success('代码已复制到剪贴板');
      
      // 2秒后清除复制状态
      setTimeout(() => {
        setCopiedType('');
      }, 2000);
    } catch (err) {
      console.error('复制失败:', err);
      message.error('复制失败，请手动复制');
      
      // 备用方案：使用传统方法
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      try {
        document.execCommand('copy');
        message.success('代码已复制到剪贴板');
        setCopiedType(type);
        setTimeout(() => {
          setCopiedType('');
        }, 2000);
      } catch (fallbackErr) {
        message.error('复制失败，请手动复制');
      } finally {
        document.body.removeChild(textArea);
      }
    }
  };

  if (!resultData) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Alert
          message="未找到攻击结果"
          description="请返回攻击页面重新开始攻击"
          type="warning"
          showIcon
        />
        <Button onClick={handleBack} style={{ marginTop: '16px' }}>
          返回攻击页面
        </Button>
      </div>
    );
  }

  const { taskId, result, config } = resultData;
  
  // 判断攻击是否成功
  // 方式1: 检查 success 字段
  // 方式2: 检查是否有 adversarial_code 且与 original_code 不同
  // 方式3: 检查 original_label 和 adversarial_label 是否不同
  const isAttackSuccessful = 
    result?.success === true || 
    (result?.adversarial_code && result?.original_code && result.adversarial_code !== result.original_code) ||
    (result?.original_label !== undefined && result?.adversarial_label !== undefined && result.original_label !== result.adversarial_label);

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={handleBack}
          style={{ marginBottom: '16px' }}
        >
          返回攻击页面
        </Button>
        <Title level={2}>对抗攻击结果</Title>
      </div>

      {/* 攻击成功/失败提示 */}
      <Alert
        message={isAttackSuccessful ? "✅ 攻击成功！" : "❌ 攻击失败"}
        description={
          isAttackSuccessful ? 
            (result?.query_times ? 
              `成功生成对抗样本！查询次数: ${result.query_times}, 耗时: ${result.time_cost ? result.time_cost.toFixed(3) + 's' : 'N/A'}` :
              '成功生成对抗代码样本！'
            ) : 
            '未能成功生成对抗样本。建议调整攻击参数或尝试其他攻击方法。'
        }
        type={isAttackSuccessful ? "success" : "error"}
        showIcon
        style={{ marginBottom: '16px' }}
      />

      <Row gutter={16}>
        <Col span={24}>
          <Card title="攻击配置信息" style={{ marginBottom: '16px' }}>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="任务ID" span={2}>{taskId}</Descriptions.Item>
              <Descriptions.Item label="攻击方法">
                <Tag color="blue">
                  {config?.method === 'itgen' ? 'ITGen' :
                   config?.method === 'alert' ? 'ALERT' :
                   config?.method === 'beam_attack' ? 'Beam Attack' : 
                   config?.method || 'ITGen'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="测试模型">
                <Tag color="purple">{config?.model_name || config?.model_id || 'CodeBERT'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="任务类型">
                <Tag color="orange">
                  {config?.task_type === 'clone-detection' ? '克隆检测' : 
                   config?.task_type === 'vulnerability-detection' ? '漏洞检测' : 
                   config?.task_type === 'code-summarization' ? '代码摘要' : '未知'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="编程语言">
                <Tag color="cyan">{config?.language || 'Python'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="攻击手段">
                <Tag color="green">
                  {config?.attack_strategy === 'identifier_rename' ? '标识符重命名' : 
                   config?.attack_strategy === 'equivalent_transform' ? '等价变换' : 
                   config?.attack_strategy === 'both' ? '两种手段结合' : '未知'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="最大修改次数">
                {config?.max_modifications || 5}
              </Descriptions.Item>
              <Descriptions.Item label="最大查询次数">
                {config?.max_query_times || 200}
              </Descriptions.Item>
              <Descriptions.Item label="时间限制">
                {config?.time_limit || 60} 秒
              </Descriptions.Item>
              <Descriptions.Item label="最大替换数">
                {config?.max_substitutions || 10}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      {result && (
        <>
          {/* 攻击前的代码 */}
          <Card title="原始代码 (Original Code)" style={{ marginBottom: '16px' }}>
            <Card 
              size="small"
              extra={
                <Button 
                  type="text" 
                  icon={<CopyOutlined />} 
                  size="small"
                  onClick={() => handleCopy(result.original_code || result.original_code1 || '', 'original_code')}
                  style={{ 
                    color: copiedType === 'original_code' ? '#52c41a' : undefined,
                    fontWeight: copiedType === 'original_code' ? 'bold' : 'normal'
                  }}
                >
                  {copiedType === 'original_code' ? '已复制' : '复制'}
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
                {result.original_code || result.original_code1 || resultData.taskInfo?.parameters?.code_data?.code1 || '暂无数据'}
              </pre>
            </Card>
          </Card>

          {/* 攻击后的代码 - 只在攻击成功时显示代码变体 */}
          <Card title={isAttackSuccessful ? "对抗代码 - 攻击成功 (Adversarial Code - Attack Successful)" : "攻击结果 (Attack Result)"} style={{ marginBottom: '16px' }}>
            {isAttackSuccessful ? (
              <Card 
                size="small"
                extra={
                  <Button 
                    type="text" 
                    icon={<CopyOutlined />} 
                    size="small"
                    onClick={() => handleCopy(result.adversarial_code || result.adversarial_code1 || '', 'adversarial_code')}
                    style={{ 
                      color: copiedType === 'adversarial_code' ? '#52c41a' : undefined,
                      fontWeight: copiedType === 'adversarial_code' ? 'bold' : 'normal'
                    }}
                  >
                    {copiedType === 'adversarial_code' ? '已复制' : '复制'}
                  </Button>
                }
              >
                <pre style={{ 
                  background: '#e6fffb', 
                  padding: '12px', 
                  borderRadius: '4px',
                  fontSize: '13px',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  margin: 0,
                  maxHeight: '400px',
                  overflow: 'auto',
                  border: '2px solid #52c41a'
                }}>
                  {result.adversarial_code || result.adversarial_code1 || resultData.taskInfo?.parameters?.code_data?.code2 || '暂无数据'}
                </pre>
              </Card>
            ) : (
              <Alert
                message="攻击未成功"
                description="未能成功生成对抗代码。可能需要调整攻击参数或更换攻击方法。"
                type="warning"
                showIcon
              />
            )}
          </Card>

          {result.replaced_words && Object.keys(result.replaced_words).length > 0 && (
            <Row gutter={16} style={{ marginBottom: '16px' }}>
              <Col span={24}>
                <Card title="标识符替换映射">
                  <Descriptions bordered column={3}>
                    {Object.entries(result.replaced_words).map(([key, value]) => (
                      <Descriptions.Item key={key} label={<Text style={{ color: '#1890ff' }}>{key}</Text>}>
                        <Text style={{ color: '#52c41a' }}>{value as string}</Text>
                      </Descriptions.Item>
                    ))}
                  </Descriptions>
                </Card>
              </Col>
            </Row>
          )}

          <Row gutter={16}>
            <Col span={8}>
              <Card title="查询次数">
                <Text style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff' }}>
                  {result.query_times || 'N/A'}
                </Text>
              </Card>
            </Col>
            <Col span={8}>
              <Card title="时间成本">
                <Text style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                  {result.time_cost ? `${result.time_cost}s` : 'N/A'}
                </Text>
              </Card>
            </Col>
            <Col span={8}>
              <Card title="攻击方法">
                <Text style={{ fontSize: '24px', fontWeight: 'bold', color: '#ff4d4f' }}>
                  {result.method || 'ITGen'}
                </Text>
              </Card>
            </Col>
          </Row>
        </>
      )}

      <Divider />

      <Row justify="center" style={{ marginTop: '24px' }}>
        <Col>
          <Button 
            type="primary" 
            onClick={handleBack}
            size="large"
            style={{ minWidth: '200px' }}
          >
            返回攻击页面
          </Button>
        </Col>
      </Row>
    </div>
  );
};

export default AttackResult;
