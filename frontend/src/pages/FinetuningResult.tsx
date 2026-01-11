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
  Statistic,
  Progress,
  Space,
  message
} from 'antd';
import { ArrowLeftOutlined, DownloadOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts';

const { Title, Text } = Typography;

// 后端返回的结果格式（支持新旧两种格式）
interface BackendFinetuningResult {
  // 基础字段
  task_id?: string;
  status?: string;
  success?: boolean;
  model_name: string;
  task_type: string;
  sub_task_type?: string;
  dataset?: string;
  attack_method?: string;
  
  // 训练参数（旧格式）
  parameters?: {
    learning_rate: number;
    epochs: number;
    batch_size: number;
  };
  
  // 训练指标（新格式）
  training_metrics?: {
    epochs: number;
    learning_rate: number;
    batch_size: number;
    total_samples: number;
    training_time: number;
    final_loss: number;
    best_accuracy: number;
  };
  
  // 训练样本数（旧格式）
  training_samples?: number;
  
  // 旧格式的指标
  old_metrics?: {
    asr: number;
    ami: number;
    art: number;
  };
  
  new_metrics?: {
    [method: string]: {
      asr: number;
      ami: number;
      art: number;
    };
  };
  
  // 新格式的鲁棒性改进
  robustness_improvement?: {
    baseline_asr: number;
    improved_asr: number;
    improvement: number;
    resistance_score: number;
  };
  
  // 新格式的攻击方法性能
  attack_method_performance?: {
    [method: string]: {
      before_finetuning: number;
      after_finetuning: number;
      improvement: number;
    };
  };
  
  // 新格式的指标对比
  metrics_comparison?: {
    asr: {
      before: number;
      after: number;
      improvement: number;
    };
    ami: {
      before: number;
      after: number;
      change: number;
    };
    art: {
      before: number;
      after: number;
      change: number;
    };
  };
  
  // 旧格式的对比数据
  comparison?: {
    [method: string]: {
      old_asr: number;
      old_ami: number;
      old_art: number;
      new_asr: number;
      new_ami: number;
      new_art: number;
      asr_change: number;
      ami_change: number;
      art_change: number;
    };
  };
  
  // 模型文件路径（新格式）
  model_artifacts?: {
    model_path: string;
    checkpoint_path: string;
    config_path: string;
  };
  
  // 建议列表（新格式）
  recommendations?: string[];
  
  // 基线报告ID（新格式）
  baseline_report_id?: string;
  
  // 时间字段
  created_at?: string;
  started_at?: string;
  completed_at?: string;
}

interface FinetuningResultData {
  result: BackendFinetuningResult;
  config: any;
  taskId: string | null;
}

const FinetuningResult: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [resultData, setResultData] = useState<FinetuningResultData | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        // 优先从路由state获取数据（从任务管理页面或微调页面跳转过来）
        const stateData = location.state as any;
        if (stateData && stateData.result) {
          console.log('📦 从路由state加载微调结果', stateData);
          // 构造resultData格式
          const data: FinetuningResultData = {
            result: stateData.result,
            config: stateData.taskInfo || {},
            taskId: stateData.taskId || null
          };
          setResultData(data);
        } else {
          // 如果没有路由参数，尝试从sessionStorage获取（兼容旧版本）
          const storedData = sessionStorage.getItem('finetuningResult');
          if (storedData) {
            const parsed = JSON.parse(storedData);
            console.log('📊 从sessionStorage加载鲁棒性增强结果:', parsed);
            setResultData(parsed);
          } else {
            console.warn('⚠️ 未找到鲁棒性增强结果');
            message.warning('未找到微调结果，请重新执行微调');
            navigate('/finetuning');
          }
        }
      } catch (error) {
        console.error('❌ 加载鲁棒性增强结果失败:', error);
        message.error('加载微调结果失败');
        navigate('/finetuning');
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [navigate, location]);

  const handleBack = () => {
    navigate('/finetuning');
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      // 模拟下载
      await new Promise(resolve => setTimeout(resolve, 2000));
      const link = document.createElement('a');
      link.href = '#';
      link.download = `${resultData?.result.model_name || 'model'}_enhanced.pth`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      alert('模型下载成功！');
    } catch (error) {
      console.error('下载失败:', error);
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '24px' }}>
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Alert
            message="正在加载鲁棒性增强结果..."
            description="请稍候"
            type="info"
            showIcon
          />
        </div>
      </div>
    );
  }

  if (!resultData) {
    return (
      <div style={{ padding: '24px' }}>
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Alert
            message="未找到鲁棒性增强结果"
            description="请返回鲁棒性增强页面重新开始训练"
            type="warning"
            showIcon
          />
          <Button onClick={handleBack} style={{ marginTop: '16px' }}>
            返回鲁棒性增强页面
          </Button>
        </div>
      </div>
    );
  }

  const { result } = resultData;
  const taskId = resultData.taskId || result.task_id || 'N/A';
  
  // 适配后端返回的数据格式
  // 后端返回的新格式包含：training_metrics, robustness_improvement, attack_method_performance, metrics_comparison
  const trainingMetrics: any = result.training_metrics || {};
  const robustnessImprovement: any = result.robustness_improvement || {};
  const attackMethodPerformance: any = result.attack_method_performance || {};
  const metricsComparison: any = result.metrics_comparison || {};
  
  // 兼容旧格式
  const oldMetrics = result.old_metrics || {
    asr: (metricsComparison as any).asr?.before || (robustnessImprovement as any).baseline_asr || 0,
    ami: (metricsComparison as any).ami?.before || 0,
    art: (metricsComparison as any).art?.before || 0
  };
  
  const newMetrics = result.new_metrics || {};
  const comparison = result.comparison || {};

  // 计算平均comparison数据（如果有多个攻击方法）
  const getAverageComparison = () => {
    // 优先使用新格式的 metrics_comparison
    const mc = metricsComparison as any;
    if (mc && mc.asr) {
      return {
        old_asr: mc.asr.before || 0,
        old_ami: mc.ami?.before || 0,
        old_art: mc.art?.before || 0,
        new_asr: mc.asr.after || 0,
        new_ami: mc.ami?.after || 0,
        new_art: mc.art?.after || 0,
        asr_change: mc.asr.improvement || 0,
        ami_change: mc.ami?.change || 0,
        art_change: mc.art?.change || 0
      };
    }
    
    // 使用旧格式的 comparison
    if (comparison && Object.keys(comparison).length > 0) {
      const methods = Object.keys(comparison);
      const avgComparison = {
        old_asr: 0,
        old_ami: 0,
        old_art: 0,
        new_asr: 0,
        new_ami: 0,
        new_art: 0,
        asr_change: 0,
        ami_change: 0,
        art_change: 0
      };
      
      methods.forEach(method => {
        const comp = comparison[method];
        avgComparison.old_asr += comp.old_asr || 0;
        avgComparison.old_ami += comp.old_ami || 0;
        avgComparison.old_art += comp.old_art || 0;
        avgComparison.new_asr += comp.new_asr || 0;
        avgComparison.new_ami += comp.new_ami || 0;
        avgComparison.new_art += comp.new_art || 0;
        avgComparison.asr_change += comp.asr_change || 0;
        avgComparison.ami_change += comp.ami_change || 0;
        avgComparison.art_change += comp.art_change || 0;
      });
      
      const count = methods.length;
      Object.keys(avgComparison).forEach(key => {
        avgComparison[key as keyof typeof avgComparison] /= count;
      });
      
      return avgComparison;
    }
    
    return null;
  };

  const avgComp = getAverageComparison();

  return (
    <div style={{ padding: '24px' }}>
      <Button 
        icon={<ArrowLeftOutlined />} 
        onClick={handleBack}
        style={{ marginBottom: '16px' }}
      >
        返回鲁棒性增强页面
      </Button>
      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <Title level={2}>鲁棒性增强结果</Title>
      </div>

      <Row gutter={16}>
        <Col span={24}>
          <Card title="模型信息" style={{ marginBottom: '16px' }}>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="任务ID" span={2}>{taskId}</Descriptions.Item>
              <Descriptions.Item label="模型名称">
                <Tag color="blue">{result.model_name || 'N/A'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="任务类型">
                <Tag color="purple">
                  {result.task_type === 'clone-detection' ? '克隆检测' :
                   result.task_type === 'vulnerability-detection' ? '漏洞检测' :
                   result.task_type === 'code-summarization' ? '代码摘要' : result.task_type || 'N/A'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="数据集">{result.dataset || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="训练样本数">{(trainingMetrics as any).total_samples || result.training_samples || 0}</Descriptions.Item>
              <Descriptions.Item label="攻击方法">
                {Object.keys(attackMethodPerformance).length > 0 ? (
                  Object.keys(attackMethodPerformance).map((method: string) => (
                    <Tag key={method.trim()} color="green" style={{ marginRight: '4px' }}>
                      {method.trim().toUpperCase()}
                    </Tag>
                  ))
                ) : result.attack_method ? (
                  result.attack_method.split(',').map((method: string) => (
                    <Tag key={method.trim()} color="green" style={{ marginRight: '4px' }}>
                      {method.trim().toUpperCase()}
                    </Tag>
                  ))
                ) : (
                  <Tag color="default">未指定</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="学习率">
                {(trainingMetrics as any).learning_rate || result.parameters?.learning_rate || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="训练周期">{(trainingMetrics as any).epochs || result.parameters?.epochs || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="批次大小">{(trainingMetrics as any).batch_size || result.parameters?.batch_size || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="训练时间">
                {(trainingMetrics as any).training_time ? `${(trainingMetrics as any).training_time} 分钟` : 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="最终损失">
                {(trainingMetrics as any).final_loss || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="最佳准确率">
                {(trainingMetrics as any).best_accuracy ? `${((trainingMetrics as any).best_accuracy * 100).toFixed(2)}%` : 'N/A'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="鲁棒性增强前模型性能" bordered={false}>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="ASR (攻击成功率)"
                  value={oldMetrics.asr || (robustnessImprovement as any).baseline_asr || 0}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: '#cf1322' }}
                />
              </Col>
              <Col span={8}>
                <Statistic 
                  title="AMI (平均调用次数)" 
                  value={oldMetrics.ami || 0} 
                  precision={1}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col span={8}>
                <Statistic 
                  title="ART (平均响应时间)" 
                  value={oldMetrics.art || 0} 
                  precision={2}
                  suffix="分"
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col span={12}>
          <Card title="鲁棒性增强后模型性能" bordered={false}>
            {Object.keys(attackMethodPerformance).length > 0 ? (
              <div>
                {Object.entries(attackMethodPerformance).map(([method, perf]: [string, any]) => (
                  <div key={method} style={{ marginBottom: '16px' }}>
                    <Text strong style={{ display: 'block', marginBottom: '8px' }}>
                      {method.toUpperCase()} 方法
                    </Text>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic 
                          title="ASR" 
                          value={perf.after_finetuning || 0} 
                          precision={2}
                          suffix="%"
                          valueStyle={{ color: '#3f8600' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic 
                          title="改进幅度" 
                          value={perf.improvement || 0} 
                          precision={2}
                          suffix="%"
                          valueStyle={{ color: '#52c41a' }}
                          prefix={<CheckCircleOutlined />}
                        />
                      </Col>
                    </Row>
                  </div>
                ))}
                {metricsComparison?.asr && (
                  <>
                    <Divider />
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic
                          title="总体ASR"
                          value={(metricsComparison as any).asr.after || (robustnessImprovement as any).improved_asr || 0}
                          precision={2}
                          suffix="%"
                          valueStyle={{ color: '#3f8600' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="总体AMI"
                          value={(metricsComparison as any).ami?.after || 0}
                          precision={1}
                          valueStyle={{ color: '#1890ff' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="总体ART"
                          value={(metricsComparison as any).art?.after || 0}
                          precision={2}
                          suffix="分"
                          valueStyle={{ color: '#fa8c16' }}
                        />
                      </Col>
                    </Row>
                  </>
                )}
              </div>
            ) : result.new_metrics && Object.keys(result.new_metrics).length > 0 ? (
              <div>
                {Object.entries(result.new_metrics).map(([method, metrics]: [string, any]) => (
                  <div key={method} style={{ marginBottom: '16px' }}>
                    <Text strong style={{ display: 'block', marginBottom: '8px' }}>
                      {method.toUpperCase()} 方法
                    </Text>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic 
                          title="ASR" 
                          value={metrics.asr || 0} 
                          precision={2}
                          suffix="%"
                          valueStyle={{ color: '#3f8600' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic 
                          title="AMI" 
                          value={metrics.ami || 0} 
                          precision={1}
                          valueStyle={{ color: '#1890ff' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic 
                          title="ART" 
                          value={metrics.art || 0} 
                          precision={2}
                          suffix="分"
                          valueStyle={{ color: '#fa8c16' }}
                        />
                      </Col>
                    </Row>
                  </div>
                ))}
              </div>
            ) : (
              <Alert message="暂无微调后数据" type="info" />
            )}
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* 性能变化统计 */}
      {avgComp && (
        <Row gutter={16}>
          <Col span={24}>
            <Card title="性能变化统计" style={{ marginBottom: '16px' }}>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic 
                    title="ASR变化" 
                    value={avgComp.asr_change} 
                    precision={2}
                    suffix="%"
                    valueStyle={{ color: avgComp.asr_change < 0 ? '#3f8600' : '#cf1322' }}
                    prefix={avgComp.asr_change < 0 ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                  />
                  <div style={{ fontSize: '12px', color: '#666', marginTop: '8px' }}>
                    {avgComp.old_asr.toFixed(2)}% → {avgComp.new_asr.toFixed(2)}%
                  </div>
                </Col>
                <Col span={8}>
                  <Statistic 
                    title="AMI变化" 
                    value={avgComp.ami_change} 
                    precision={1}
                    valueStyle={{ color: avgComp.ami_change > 0 ? '#1890ff' : '#666' }}
                  />
                  <div style={{ fontSize: '12px', color: '#666', marginTop: '8px' }}>
                    {avgComp.old_ami.toFixed(1)} → {avgComp.new_ami.toFixed(1)}
                  </div>
                </Col>
                <Col span={8}>
                  <Statistic 
                    title="ART变化" 
                    value={avgComp.art_change} 
                    precision={2}
                    suffix="分"
                    valueStyle={{ color: avgComp.art_change < 0 ? '#3f8600' : '#fa8c16' }}
                    prefix={avgComp.art_change < 0 ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                  />
                  <div style={{ fontSize: '12px', color: '#666', marginTop: '8px' }}>
                    {avgComp.old_art.toFixed(2)}分 → {avgComp.new_art.toFixed(2)}分
                  </div>
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>
      )}

      {/* 性能对比柱状图 */}
      {avgComp && (
        <Row gutter={16} style={{ marginTop: '16px' }}>
          <Col span={24}>
            <Card title="增强前后性能对比图表" style={{ marginBottom: '16px' }}>
              <Row gutter={16}>
                <Col span={8}>
                  <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                    <Title level={5}>攻击成功率 (ASR)</Title>
                    <Text type="secondary" style={{ fontSize: '12px' }}>数值越低表示模型越鲁棒</Text>
                  </div>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={[
                        { name: '增强前', value: avgComp.old_asr, fill: '#ff4d4f' },
                        { name: '增强后', value: avgComp.new_asr, fill: '#52c41a' }
                      ]}
                      margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis 
                        label={{ value: 'ASR (%)', angle: -90, position: 'insideLeft' }}
                        domain={[0, 100]}
                      />
                      <Tooltip
                        formatter={(value?: number) => value !== undefined ? [`${value.toFixed(2)}%`, 'ASR'] : ['N/A', 'ASR']}
                      />
                      <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                        {[0, 1].map((index) => (
                          <Cell key={`cell-${index}`} fill={index === 0 ? '#ff4d4f' : '#52c41a'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <div style={{ textAlign: 'center', marginTop: '8px' }}>
                    <Text strong style={{ color: avgComp.asr_change < 0 ? '#52c41a' : '#ff4d4f' }}>
                      {avgComp.asr_change > 0 ? '+' : ''}{avgComp.asr_change.toFixed(2)}%
                    </Text>
                  </div>
                </Col>

                <Col span={8}>
                  <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                    <Title level={5}>平均调用次数 (AMI)</Title>
                    <Text type="secondary" style={{ fontSize: '12px' }}>数值越高表示攻击越困难</Text>
                  </div>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={[
                        { name: '增强前', value: avgComp.old_ami, fill: '#1890ff' },
                        { name: '增强后', value: avgComp.new_ami, fill: '#722ed1' }
                      ]}
                      margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis 
                        label={{ value: 'AMI', angle: -90, position: 'insideLeft' }}
                      />
                      <Tooltip
                        formatter={(value?: number) => value !== undefined ? [value.toFixed(1), 'AMI'] : ['N/A', 'AMI']}
                      />
                      <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                        {[0, 1].map((index) => (
                          <Cell key={`cell-${index}`} fill={index === 0 ? '#1890ff' : '#722ed1'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <div style={{ textAlign: 'center', marginTop: '8px' }}>
                    <Text strong style={{ color: avgComp.ami_change > 0 ? '#52c41a' : '#666' }}>
                      {avgComp.ami_change > 0 ? '+' : ''}{avgComp.ami_change.toFixed(1)}
                    </Text>
                  </div>
                </Col>

                <Col span={8}>
                  <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                    <Title level={5}>平均响应时间 (ART)</Title>
                    <Text type="secondary" style={{ fontSize: '12px' }}>攻击生成对抗样本所需时间</Text>
                  </div>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={[
                        { name: '增强前', value: avgComp.old_art, fill: '#fa8c16' },
                        { name: '增强后', value: avgComp.new_art, fill: '#13c2c2' }
                      ]}
                      margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis 
                        label={{ value: 'ART (分)', angle: -90, position: 'insideLeft' }}
                      />
                      <Tooltip
                        formatter={(value?: number) => value !== undefined ? [`${value.toFixed(2)}分`, 'ART'] : ['N/A', 'ART']}
                      />
                      <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                        {[0, 1].map((index) => (
                          <Cell key={`cell-${index}`} fill={index === 0 ? '#fa8c16' : '#13c2c2'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <div style={{ textAlign: 'center', marginTop: '8px' }}>
                    <Text strong style={{ color: avgComp.art_change < 0 ? '#52c41a' : '#fa8c16' }}>
                      {avgComp.art_change > 0 ? '+' : ''}{avgComp.art_change.toFixed(2)}分
                    </Text>
                  </div>
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>
      )}

      {/* 各攻击方法详细对比 */}
      {result.comparison && Object.keys(result.comparison).length > 0 && (
        <Row gutter={16}>
          <Col span={24}>
            <Card title="各攻击方法性能对比" style={{ marginBottom: '16px' }}>
              {Object.entries(result.comparison).map(([method, comp]: [string, any]) => (
                <div key={method} style={{ marginBottom: '32px', paddingBottom: '24px', borderBottom: '1px solid #f0f0f0' }}>
                  <Text strong style={{ display: 'block', marginBottom: '16px', fontSize: '16px' }}>
                    {method.toUpperCase()} 方法
                  </Text>
                  
                  {/* 数值统计 */}
                  <Row gutter={16} style={{ marginBottom: '24px' }}>
                    <Col span={8}>
                      <Card size="small">
                        <Statistic
                          title="ASR变化"
                          value={comp.asr_change}
                          precision={2}
                          suffix="%"
                          valueStyle={{ color: comp.asr_change < 0 ? '#3f8600' : '#cf1322' }}
                          prefix={comp.asr_change < 0 ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                        />
                        <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                          {comp.old_asr.toFixed(2)}% → {comp.new_asr.toFixed(2)}%
                        </div>
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small">
                        <Statistic
                          title="AMI变化"
                          value={comp.ami_change}
                          precision={1}
                          valueStyle={{ color: comp.ami_change > 0 ? '#1890ff' : '#666' }}
                        />
                        <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                          {comp.old_ami.toFixed(1)} → {comp.new_ami.toFixed(1)}
                        </div>
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small">
                        <Statistic
                          title="ART变化"
                          value={comp.art_change}
                          precision={2}
                          suffix="分"
                          valueStyle={{ color: comp.art_change < 0 ? '#3f8600' : '#fa8c16' }}
                          prefix={comp.art_change < 0 ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                        />
                        <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                          {comp.old_art.toFixed(2)}分 → {comp.new_art.toFixed(2)}分
                        </div>
                      </Card>
                    </Col>
                  </Row>

                  {/* 柱状图可视化 */}
                  <div style={{ marginTop: '16px' }}>
                    <ResponsiveContainer width="100%" height={250}>
                      <BarChart
                        data={[
                          {
                            name: 'ASR (%)',
                            增强前: comp.old_asr,
                            增强后: comp.new_asr
                          },
                          {
                            name: 'AMI',
                            增强前: comp.old_ami,
                            增强后: comp.new_ami
                          },
                          {
                            name: 'ART (分)',
                            增强前: comp.old_art,
                            增强后: comp.new_art
                          }
                        ]}
                        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <Tooltip
                          formatter={(value?: number, name?: string) => {
                            if (value === undefined || name === undefined) {
                              return ['N/A', name || 'Unknown'];
                            }
                            if (name === '增强前' || name === '增强后') {
                              return [value.toFixed(2), name];
                            }
                            return [value, name];
                          }}
                        />
                        <Legend />
                        <Bar dataKey="增强前" fill="#ff7875" radius={[8, 8, 0, 0]} />
                        <Bar dataKey="增强后" fill="#95de64" radius={[8, 8, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ))}
            </Card>
          </Col>
        </Row>
      )}

      <Divider />

      {/* 训练过程可视化 - 后端未提供training_logs数据，已隐藏 */}
      {/* 由于后端不返回training_logs，所有训练曲线图已被移除 */}

      <Row justify="center" style={{ marginTop: '24px' }}>
        <Col>
          <Space size="large">
            <Button 
              icon={<ArrowLeftOutlined />} 
              onClick={handleBack}
              size="large"
              style={{ minWidth: '200px' }}
            >
              返回鲁棒性增强
            </Button>
            <Button 
              type="primary"
              icon={<DownloadOutlined />} 
              onClick={handleDownload}
              loading={downloading}
              size="large"
              style={{ minWidth: '200px' }}
            >
              下载增强模型
            </Button>
          </Space>
        </Col>
      </Row>
    </div>
  );
};

export default FinetuningResult;
