import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Typography,
  Statistic,
  Descriptions,
  message,
  Tabs,
  Table,
  Tag,
  Divider,
  Select,
  Space
} from 'antd';
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  CopyOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  BarChartOutlined,
  LineChartOutlined,
  ClockCircleOutlined,
  CodeOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;

// 根据后端实际返回格式定义接口
interface EvaluationReport {
  report_id: string;
  model_name: string;
  task_type: string;
  attack_methods: string[];
  evaluation_metrics: string[];
  method_metrics: MethodMetrics;
  summary_stats: SummaryStats;
  sample_results: BackendSampleResult[];
  generated_at: string;
}

interface MethodMetrics {
  [method: string]: {
    asr: number;
    ami: number;
    art: number;
    avg_identifiers: number;
    avg_program_length: number;
    failed_attacks: number;
    successful_attacks: number;
    total_samples: number;
  };
}

interface SummaryStats {
  asr: number;
  ami: number;
  art: number;
  avg_identifiers: number;
  avg_program_length: number;
  failed_attacks: number;
  successful_attacks: number;
  total_samples: number;
}

// 后端返回的sample_results格式（字段名带空格和大写）
interface BackendSampleResult {
  'Index': number;
  'Original Code': string;
  'Adversarial Code': string | null;
  'Program Length': number;
  'Identifier Num': number;
  'Replaced Identifiers': string | null;
  'Query Times': number;
  'Time Cost': number;
  'Type': string;
  '_file_source'?: string;
}

// 前端使用的标准化格式
interface SampleResult {
  index: number;
  original_code: string;
  adversarial_code: string | null;
  program_length: number;
  identifier_num: number;
  replaced_identifiers: string | null;
  query_times: number;
  time_cost: number;
  attack_success: boolean;
  type: string;
}

interface IdentifierReplacement {
  original: string;
  adversarial: string;
  line: number;
}

const EvaluationResult: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [reportData, setReportData] = useState<EvaluationReport | null>(null);
  const [selectedSample, setSelectedSample] = useState<SampleResult | null>(null);
  const [copiedType, setCopiedType] = useState<string>('');
  const [selectedView, setSelectedView] = useState<string>('side-by-side');

  // 将后端返回的sample转换为前端使用的格式
  const convertBackendSample = (backendSample: BackendSampleResult): SampleResult => {
    return {
      index: backendSample['Index'],
      original_code: backendSample['Original Code'],
      adversarial_code: backendSample['Adversarial Code'],
      program_length: backendSample['Program Length'],
      identifier_num: backendSample['Identifier Num'],
      replaced_identifiers: backendSample['Replaced Identifiers'],
      query_times: backendSample['Query Times'],
      time_cost: backendSample['Time Cost'],
      attack_success: backendSample['Adversarial Code'] !== null,
      type: backendSample['Type']
    };
  };

  useEffect(() => {
    // 优先从路由state获取数据
    const stateData = location.state as any;
    if (stateData && stateData.result) {
      console.log('📦 从路由state加载评估结果', stateData);
      const data = stateData.result;
      setReportData(data);
      
      // 转换并选择第一个成功的样本
      if (data.sample_results && data.sample_results.length > 0) {
        const convertedSamples = data.sample_results.map(convertBackendSample);
        const firstSuccessSample = convertedSamples.find((s: SampleResult) => s.attack_success);
        setSelectedSample(firstSuccessSample || convertedSamples[0] || null);
      }
    } else {
      // 如果没有路由参数，尝试从sessionStorage获取（兼容旧版本）
      const storedData = sessionStorage.getItem('evaluationReport');
      if (storedData) {
        const data = JSON.parse(storedData);
        console.log('📊 从sessionStorage获取报告数据:', data);
        setReportData(data);
        
        // 转换并选择第一个成功的样本
        if (data.sample_results && data.sample_results.length > 0) {
          const convertedSamples = data.sample_results.map(convertBackendSample);
          const firstSuccessSample = convertedSamples.find((s: SampleResult) => s.attack_success);
          setSelectedSample(firstSuccessSample || convertedSamples[0] || null);
        }
      } else {
        message.warning('未找到安全测试报告，请重新执行测试');
        navigate('/evaluation');
      }
    }
  }, [navigate, location]);

  const handleBack = () => {
    navigate('/evaluation');
  };

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

  const handleDownload = () => {
    if (!reportData) return;
    
    const dataStr = JSON.stringify(reportData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `evaluation_report_${reportData.report_id}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    message.success('报告下载成功');
  };

  // 解析标识符替换字符串
  const parseIdentifierReplacements = (replacedStr: string | null): IdentifierReplacement[] => {
    if (!replacedStr) return [];
    const pairs = replacedStr.split(',').filter(p => p.trim());
    return pairs.map((pair, index) => {
      const [original, adversarial] = pair.split(':');
      return {
        original: original?.trim() || '',
        adversarial: adversarial?.trim() || '',
        line: index + 1
      };
    });
  };

  if (!reportData) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Text>加载中...</Text>
      </div>
    );
  }

  const replacementColumns = [
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
  ];

  const identifierReplacements = selectedSample 
    ? parseIdentifierReplacements(selectedSample.replaced_identifiers)
    : [];

  return (
    <div>
      {/* 返回按钮和标题 */}
      <div style={{ marginBottom: '24px' }}>
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={handleBack}
          style={{ marginBottom: '16px' }}
        >
          返回安全测试页面
        </Button>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Title level={2}>安全测试结果</Title>
          <Button 
            type="primary" 
            icon={<DownloadOutlined />}
            onClick={handleDownload}
          >
            下载报告
          </Button>
        </Space>
      </div>

      {/* 测试配置信息 */}
      <Card title="测试配置" style={{ marginBottom: '16px' }}>
        <Descriptions bordered column={3}>
          <Descriptions.Item label="报告ID" span={3}>{reportData.report_id}</Descriptions.Item>
          <Descriptions.Item label="测试模型">
            <Tag color="purple">{reportData.model_name}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="任务类型">
            <Tag color="orange">
              {reportData.task_type === 'clone-detection' ? '克隆检测' :
               reportData.task_type === 'vulnerability-detection' ? '漏洞检测' :
               reportData.task_type === 'code-summarization' ? '代码摘要' : reportData.task_type}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="攻击方法">
            {(reportData.attack_methods || []).map(method => (
              <Tag key={method} color="blue" style={{ marginRight: '4px' }}>
                {method.toUpperCase()}
              </Tag>
            ))}
          </Descriptions.Item>
          <Descriptions.Item label="总样本数">{reportData.summary_stats?.total_samples || 0}</Descriptions.Item>
          <Descriptions.Item label="成功攻击数">
            <Text type="success">{reportData.summary_stats?.successful_attacks || 0}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="失败攻击数">
            <Text type="danger">{reportData.summary_stats?.failed_attacks || 0}</Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 核心性能指标 */}
      <Card title="核心性能指标" style={{ marginBottom: '16px' }}>
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title="ASR (攻击成功率)"
                value={reportData.summary_stats?.asr || 0}
                precision={1}
                suffix="%"
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: (reportData.summary_stats?.asr || 0) >= 70 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="AMI (平均模型调用)"
                value={reportData.summary_stats?.ami || 0}
                precision={1}
                prefix={<BarChartOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="ART (平均响应时间)"
                value={reportData.summary_stats?.art || 0}
                precision={2}
                suffix="分钟"
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均程序长度"
                value={reportData.summary_stats?.avg_program_length || 0}
                precision={1}
                prefix={<CodeOutlined />}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 性能指标对比图表 */}
      <Card title="性能指标对比图表" style={{ marginBottom: '16px' }}>
        <Row gutter={16}>
          {reportData.method_metrics && Object.keys(reportData.method_metrics).length > 0 ? Object.entries(reportData.method_metrics).map(([method, metrics]) => (
            <Col span={8} key={method}>
              <Card size="small" title={method.toUpperCase()}>
                <Row gutter={[8, 8]}>
                  <Col span={12}>
                    <Statistic
                      title="ASR"
                      value={metrics.asr}
                      precision={1}
                      suffix="%"
                      valueStyle={{ fontSize: '16px' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="AMI"
                      value={metrics.ami}
                      precision={1}
                      valueStyle={{ fontSize: '16px' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="ART"
                      value={metrics.art}
                      precision={2}
                      suffix="分"
                      valueStyle={{ fontSize: '16px' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="成功率"
                      value={(metrics.successful_attacks / metrics.total_samples * 100)}
                      precision={1}
                      suffix="%"
                      valueStyle={{ fontSize: '16px' }}
                    />
                  </Col>
                </Row>
              </Card>
            </Col>
          )) : (
            <Col span={24}>
              <Text type="secondary">暂无方法指标数据</Text>
            </Col>
          )}
        </Row>

        {/* 可视化对比图 */}
        <Divider />
        <Row gutter={16} style={{ marginTop: '16px' }}>
          <Col span={8}>
            <Card size="small" title="ASR 对比">
              <div style={{ height: '200px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', padding: '20px 0' }}>
                {reportData.method_metrics && Object.keys(reportData.method_metrics).length > 0 ? Object.entries(reportData.method_metrics).map(([method, metrics]) => (
                  <div key={method} style={{ textAlign: 'center', flex: 1 }}>
                    <div
                      style={{
                        height: `${metrics.asr * 1.5}px`,
                        background: method === 'itgen' ? '#52c41a' : method === 'alert' ? '#1890ff' : '#faad14',
                        margin: '0 10px',
                        borderRadius: '4px 4px 0 0',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'white',
                        fontWeight: 'bold'
                      }}
                    >
                      {metrics.asr ? metrics.asr.toFixed(1) : 0}%
                    </div>
                    <Text type="secondary" style={{ fontSize: '12px', marginTop: '8px', display: 'block' }}>
                      {method.toUpperCase()}
                    </Text>
                  </div>
                )) : (
                  <Text type="secondary">暂无数据</Text>
                )}
              </div>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title="AMI 对比">
              <div style={{ height: '200px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', padding: '20px 0' }}>
                {reportData.method_metrics && Object.keys(reportData.method_metrics).length > 0 ? Object.entries(reportData.method_metrics).map(([method, metrics]) => {
                  const maxAMI = Math.max(...Object.values(reportData.method_metrics || {}).map(m => m.ami || 0));
                  const heightPercent = (metrics.ami / maxAMI) * 100;
                  return (
                    <div key={method} style={{ textAlign: 'center', flex: 1 }}>
                      <div
                        style={{
                          height: `${heightPercent}px`,
                          background: method === 'itgen' ? '#52c41a' : method === 'alert' ? '#1890ff' : '#faad14',
                          margin: '0 10px',
                          borderRadius: '4px 4px 0 0',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'white',
                          fontWeight: 'bold',
                          fontSize: '12px'
                        }}
                      >
                        {metrics.ami ? metrics.ami.toFixed(1) : 0}
                      </div>
                      <Text type="secondary" style={{ fontSize: '12px', marginTop: '8px', display: 'block' }}>
                        {method.toUpperCase()}
                    </Text>
                  </div>
                  );
                }) : (
                  <Text type="secondary">暂无数据</Text>
                )}
              </div>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title="ART 对比">
              <div style={{ height: '200px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', padding: '20px 0' }}>
                {reportData.method_metrics && Object.keys(reportData.method_metrics).length > 0 ? Object.entries(reportData.method_metrics).map(([method, metrics]) => {
                  const maxART = Math.max(...Object.values(reportData.method_metrics || {}).map(m => m.art || 0));
                  const heightPercent = (metrics.art / maxART) * 100;
                  return (
                    <div key={method} style={{ textAlign: 'center', flex: 1 }}>
                      <div
                        style={{
                          height: `${heightPercent}px`,
                          background: method === 'itgen' ? '#52c41a' : method === 'alert' ? '#1890ff' : '#faad14',
                          margin: '0 10px',
                          borderRadius: '4px 4px 0 0',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'white',
                          fontWeight: 'bold',
                          fontSize: '12px'
                        }}
                      >
                        {metrics.art ? metrics.art.toFixed(2) : 0}
                      </div>
                      <Text type="secondary" style={{ fontSize: '12px', marginTop: '8px', display: 'block' }}>
                        {method.toUpperCase()}
                    </Text>
                  </div>
                  );
                }) : (
                  <Text type="secondary">暂无数据</Text>
                )}
              </div>
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 对抗样本浏览器 */}
      <Card title="对抗样本浏览器" style={{ marginBottom: '16px' }}>
        {/* 样本选择器 */}
        <div style={{ marginBottom: '16px' }}>
          <Space>
            <Text strong>选择样本:</Text>
            <Select
              style={{ width: 300 }}
              value={selectedSample?.index}
              onChange={(value) => {
                const convertedSamples = (reportData.sample_results || []).map(convertBackendSample);
                const sample = convertedSamples.find(s => s.index === value);
                setSelectedSample(sample || null);
              }}
            >
              {(reportData.sample_results || []).map((backendSample) => {
                const converted = convertBackendSample(backendSample);
                return (
                  <Option key={converted.index} value={converted.index}>
                    样本 #{converted.index} - {converted.attack_success ? 
                      <Tag color="success" style={{ marginLeft: '8px' }}>成功</Tag> : 
                      <Tag color="error" style={{ marginLeft: '8px' }}>失败</Tag>
                    }
                  </Option>
                );
              })}
            </Select>
            <Text type="secondary">
              查询次数: {selectedSample?.query_times || 0} | 
              时间: {selectedSample?.time_cost ? selectedSample.time_cost.toFixed(2) : 0}分钟
            </Text>
          </Space>
        </div>

        {selectedSample && (
          <>
            {/* 对比方式选择 */}
            <div style={{ marginBottom: '16px' }}>
              <Space>
                <Text strong>对比方式:</Text>
                <Select
                  value={selectedView}
                  onChange={setSelectedView}
                  style={{ width: 150 }}
                >
                  <Option value="side-by-side">并排对比</Option>
                  <Option value="unified">统一视图</Option>
                </Select>
              </Space>
            </div>

            <Tabs defaultActiveKey="comparison">
              <TabPane tab="代码对比" key="comparison">
                {selectedSample.adversarial_code ? (
                  selectedView === 'side-by-side' ? (
                    <Row gutter={16}>
                      <Col span={12}>
                        <Card 
                          size="small" 
                          title="原始代码" 
                          extra={
                            <Button
                              type="text"
                              size="small"
                              icon={<CopyOutlined />}
                              onClick={() => handleCopy(selectedSample.original_code, 'original')}
                              style={{
                                color: copiedType === 'original' ? '#52c41a' : undefined
                              }}
                            >
                              {copiedType === 'original' ? '已复制' : '复制'}
                            </Button>
                          }
                        >
                          <pre style={{
                            background: '#f5f5f5',
                            padding: '16px',
                            borderRadius: '4px',
                            fontSize: '13px',
                            lineHeight: '1.6',
                            fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                            overflow: 'auto',
                            maxHeight: '400px',
                            margin: 0
                          }}>
                            {selectedSample.original_code}
                          </pre>
                        </Card>
                      </Col>
                      <Col span={12}>
                        <Card 
                          size="small" 
                          title="对抗代码" 
                          extra={
                            <Button
                              type="text"
                              size="small"
                              icon={<CopyOutlined />}
                              onClick={() => handleCopy(selectedSample.adversarial_code || '', 'adversarial')}
                              style={{
                                color: copiedType === 'adversarial' ? '#52c41a' : undefined
                              }}
                            >
                              {copiedType === 'adversarial' ? '已复制' : '复制'}
                            </Button>
                          }
                        >
                          <pre style={{
                            background: '#e6fffb',
                            padding: '16px',
                            borderRadius: '4px',
                            fontSize: '13px',
                            lineHeight: '1.6',
                            fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                            overflow: 'auto',
                            maxHeight: '400px',
                            border: '1px solid #b7eb8f',
                            margin: 0
                          }}>
                            {selectedSample.adversarial_code}
                          </pre>
                        </Card>
                      </Col>
                    </Row>
                  ) : (
                    <Card size="small" title="统一视图">
                      <div style={{ fontFamily: 'Monaco, Consolas, "Courier New", monospace', fontSize: '13px' }}>
                        {selectedSample.original_code ? (selectedSample.original_code.split('\n') || []).map((line, index) => {
                          const advLine = selectedSample.adversarial_code?.split('\n')[index] || '';
                          const isDifferent = line !== advLine;
                          return (
                            <div key={index} style={{ marginBottom: '8px' }}>
                              <div style={{
                                background: isDifferent ? '#fff1f0' : '#f5f5f5',
                                padding: '4px 8px',
                                borderLeft: isDifferent ? '3px solid #ff4d4f' : '3px solid #d9d9d9'
                              }}>
                                <Text type="secondary" style={{ marginRight: '8px', fontFamily: 'monospace' }}>
                                  {index + 1}
                                </Text>
                                <Text delete={isDifferent}>{line}</Text>
                              </div>
                              {isDifferent && advLine && (
                                <div style={{
                                  background: '#f6ffed',
                                  padding: '4px 8px',
                                  borderLeft: '3px solid #52c41a',
                                  marginTop: '2px'
                                }}>
                                  <Text type="secondary" style={{ marginRight: '8px', fontFamily: 'monospace' }}>
                                    {index + 1}
                                  </Text>
                                  <Text style={{ color: '#52c41a' }}>{advLine}</Text>
                                </div>
                              )}
                            </div>
                          );
                        }) : (
                          <Text type="secondary">暂无原始代码</Text>
                        )}
                      </div>
                    </Card>
                  )
                ) : (
                  <Card size="small">
                    <Text type="danger">攻击未成功，无对抗代码生成</Text>
                  </Card>
                )}
              </TabPane>

              <TabPane tab="标识符替换" key="replacements">
                <Card size="small">
                  {identifierReplacements.length > 0 ? (
                    <>
                      <Table
                        columns={replacementColumns}
                        dataSource={identifierReplacements}
                        pagination={false}
                        size="small"
                        rowKey={(record) => `${record.line}-${record.original}`}
                      />
                      <Divider />
                      <Statistic
                        title="总替换数"
                        value={identifierReplacements.length}
                        prefix={<CheckCircleOutlined />}
                        valueStyle={{ color: '#1890ff' }}
                      />
                    </>
                  ) : (
                    <Text type="secondary">无标识符替换</Text>
                  )}
                </Card>
              </TabPane>
            </Tabs>
          </>
        )}
      </Card>

      {/* 返回按钮 */}
      <Row justify="center" style={{ marginTop: '24px' }}>
        <Col>
          <Button type="primary" onClick={handleBack} size="large" style={{ minWidth: '200px' }}>
            返回安全测试页面
          </Button>
        </Col>
      </Row>
    </div>
  );
};

export default EvaluationResult;
