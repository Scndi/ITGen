import React from 'react';
import { Card, Row, Col, Button, Typography, Space } from 'antd';
import {
  PlayCircleOutlined,
  RobotOutlined,
  BugOutlined,
  SettingOutlined,
  ExperimentOutlined,
  ArrowRightOutlined,
  CloudUploadOutlined,
  ThunderboltOutlined,
  AppstoreOutlined,
  BarChartOutlined,
  SafetyOutlined,
  SafetyCertificateOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Paragraph, Text } = Typography;

// 卡片悬浮效果样式
const cardHoverStyle: React.CSSProperties = {
  transition: 'all 0.3s ease',
  cursor: 'pointer'
};

const Home: React.FC = () => {
  const navigate = useNavigate();

  // 添加悬浮效果处理
  const handleCardMouseEnter = (e: React.MouseEvent<HTMLDivElement>) => {
    const card = e.currentTarget;
    card.style.transform = 'translateY(-8px)';
    card.style.boxShadow = '0 12px 24px rgba(0, 0, 0, 0.15)';
  };

  const handleCardMouseLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    const card = e.currentTarget;
    card.style.transform = 'translateY(0)';
    card.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.09)';
  };

  const features = [
    {
      icon: <RobotOutlined style={{ fontSize: '48px', color: '#1890ff' }} />,
      title: '模型管理',
      description: '支持主流DCM（CodeBERT、GraphCodeBERT、CodeGPT等）的快速接入，提供标准化的预测接口（API或Docker容器），确保模型集成和调用的便捷性。',
      action: () => navigate('/models'),
      actionText: '管理模型'
    },
    {
      icon: <BugOutlined style={{ fontSize: '48px', color: '#52c41a' }} />,
      title: '对抗攻击',
      description: '基于ITGen核心算法，支持用户自定义攻击预算（最大查询次数、时间限制），生成单个代码段的代码变体，即单个对抗样本生成，测试模型脆弱性。',
      action: () => navigate('/attack'),
      actionText: '开始攻击'
    },
    {
      icon: <ExperimentOutlined style={{ fontSize: '48px', color: '#722ed1' }} />,
      title: '批量对抗样本生成',
      description: '支持多个模型、多个任务（漏洞检测、克隆检测、代码摘要）的批量测试，与基线方法（ALERT、BeamAttack）自动对比，批量生成对抗样本。',
      action: () => navigate('/batch-testing'),
      actionText: '批量对抗样本生成'
    },
    {
      icon: <BarChartOutlined style={{ fontSize: '48px', color: '#fa8c16' }} />,
      title: '安全测试',
      description: '使用测试代码集对被测模型进行全面的鲁棒性评估。通过ITGen攻击引擎，利用贝叶斯优化生成对抗样本，输出ASR、AMI、ART等关键指标，生成详尽的评测报告。',
      action: () => navigate('/evaluation'),
      actionText: '开始评估'
    },
    {
      icon: <SettingOutlined style={{ fontSize: '48px', color: '#eb2f96' }} />,
      title: '鲁棒性增强',
      description: '通过在线对抗训练提升模型鲁棒性。利用ITGen生成高价值对抗样本并结合DPP采样确保多样性，混合训练原始样本和对抗样本，输出增强后的模型。',
      action: () => navigate('/finetuning'),
      actionText: '开始增强'
    },
    {
      icon: <AppstoreOutlined style={{ fontSize: '48px', color: '#13c2c2' }} />,
      title: '任务管理',
      description: '统一管理所有异步任务的状态和结果。实时监控任务执行进度，支持任务取消、历史查询和性能统计，是您管理复杂工作流的中央控制台。',
      action: () => navigate('/tasks'),
      actionText: '任务中心'
    }
  ];

  return (
    <div>
      {/* 欢迎区域 */}
      <div style={{ textAlign: 'center', marginBottom: '48px' }}>
        <Title level={1} style={{ marginBottom: '16px' }}>
          深度代码模型攻击与增强工具
        </Title>
        <Paragraph style={{ fontSize: '16px', color: '#666', maxWidth: '800px', margin: '0 auto' }}>
          基于ITGen算法的自动化工具，用于评估和提升深度代码模型在面对对抗攻击时的鲁棒性。
          支持CodeBERT、GraphCodeBERT、CodeGPT等主流模型。
        </Paragraph>
        <Space size="large" style={{ marginTop: '24px' }}>
          <Button 
            type="primary" 
            size="large" 
            icon={<PlayCircleOutlined />}
            onClick={() => navigate('/attack')}
          >
            开始攻击
          </Button>
        </Space>
      </div>

      {/* 功能特性 */}
      <Title level={2} style={{ textAlign: 'center', marginBottom: '32px' }}>
        核心功能
      </Title>
      <Row gutter={[24, 24]}>
        {features.slice(0, 3).map((feature, index) => (
          <Col xs={24} sm={12} lg={8} key={index}>
            <Card
              hoverable
              className="core-feature-card"
              style={{ height: '100%' }}
              bodyStyle={{ padding: '24px' }}
              onClick={feature.action}
            >
              <div className="feature-content">
                <div className="feature-icon" style={{ textAlign: 'center', marginBottom: '16px' }}>
                  {feature.icon}
                </div>
                <Title level={4} className="feature-title" style={{ textAlign: 'center', marginBottom: '12px' }}>
                  {feature.title}
                </Title>
                <Paragraph style={{ textAlign: 'center', marginBottom: '20px', minHeight: '120px' }}>
                  {feature.description}
                </Paragraph>
                <div style={{ textAlign: 'center' }}>
                  <Button 
                    type="primary" 
                    className="feature-button" 
                    onClick={(e) => {
                      e.stopPropagation();
                      feature.action();
                    }}
                  >
                    {feature.actionText}
                  </Button>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
      <Row gutter={[24, 24]} style={{ marginTop: '24px' }}>
        {features.slice(3, 5).map((feature, index) => (
          <Col xs={24} sm={12} lg={12} key={index + 3}>
            <Card
              hoverable
              className="core-feature-card"
              style={{ height: '100%' }}
              bodyStyle={{ padding: '24px' }}
              onClick={feature.action}
            >
              <div className="feature-content">
                <div className="feature-icon" style={{ textAlign: 'center', marginBottom: '16px' }}>
                  {feature.icon}
                </div>
                <Title level={4} className="feature-title" style={{ textAlign: 'center', marginBottom: '12px' }}>
                  {feature.title}
                </Title>
                <Paragraph style={{ textAlign: 'center', marginBottom: '20px', minHeight: '120px' }}>
                  {feature.description}
                </Paragraph>
                <div style={{ textAlign: 'center' }}>
                  <Button 
                    type="primary" 
                    className="feature-button" 
                    onClick={(e) => {
                      e.stopPropagation();
                      feature.action();
                    }}
                  >
                    {feature.actionText}
                  </Button>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 平台使用流程 */}
      <div style={{ marginTop: '48px' }}>
        <Title level={2} style={{ textAlign: 'center', marginBottom: '32px' }}>
          平台使用流程
        </Title>
        
        {/* 第一排：模型管理 → 对抗攻击 → 批量对抗样本生成 */}
        <Row gutter={[24, 24]} justify="center" style={{ marginBottom: '24px' }}>
          {/* 步骤1: 模型管理 */}
          <Col xs={24} md={6}>
            <Card
              hoverable
              style={{ height: '100%', borderColor: '#1890ff', borderWidth: '2px', ...cardHoverStyle }}
              bodyStyle={{ padding: '24px' }}
              onClick={() => navigate('/models')}
              onMouseEnter={handleCardMouseEnter}
              onMouseLeave={handleCardMouseLeave}
            >
              <div style={{ textAlign: 'center' }}>
                <div style={{ 
                  width: '60px', 
                  height: '60px', 
                  borderRadius: '50%', 
                  background: '#e6f7ff', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '0 auto 16px'
                }}>
                  <CloudUploadOutlined style={{ fontSize: '32px', color: '#1890ff' }} />
                </div>
                <div style={{ 
                  background: '#1890ff', 
                  color: '#fff', 
                  width: '32px', 
                  height: '32px', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '0 auto 12px',
                  fontWeight: 'bold',
                  fontSize: '16px'
                }}>1</div>
                <Title level={4} style={{ marginBottom: '12px' }}>模型管理</Title>
                <Paragraph style={{ color: '#666', marginBottom: '16px' }}>
                  上传并管理深度代码模型（CodeBERT、GraphCodeBERT等），配置模型参数
                </Paragraph>
                <Button type="primary" size="small">上传模型</Button>
              </div>
            </Card>
          </Col>

          {/* 箭头 */}
          <Col xs={0} md={1} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ArrowRightOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
          </Col>

          {/* 步骤2: 对抗攻击 */}
          <Col xs={24} md={6}>
            <Card
              hoverable
              style={{ height: '100%', borderColor: '#52c41a', borderWidth: '2px', ...cardHoverStyle }}
              bodyStyle={{ padding: '24px' }}
              onClick={() => navigate('/attack')}
              onMouseEnter={handleCardMouseEnter}
              onMouseLeave={handleCardMouseLeave}
            >
              <div style={{ textAlign: 'center' }}>
                <div style={{ 
                  width: '60px', 
                  height: '60px', 
                  borderRadius: '50%', 
                  background: '#f6ffed', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '0 auto 16px'
                }}>
                  <ThunderboltOutlined style={{ fontSize: '32px', color: '#52c41a' }} />
                </div>
                <div style={{ 
                  background: '#52c41a', 
                  color: '#fff', 
                  width: '32px', 
                  height: '32px', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '0 auto 12px',
                  fontWeight: 'bold',
                  fontSize: '16px'
                }}>2</div>
                <Title level={4} style={{ marginBottom: '12px' }}>对抗攻击</Title>
                <Paragraph style={{ color: '#666', marginBottom: '16px' }}>
                  生成单个代码段的代码变体，即单个对抗样本生成，测试模型脆弱性
                </Paragraph>
                <Button type="primary" style={{ background: '#52c41a', borderColor: '#52c41a' }} size="small">生成对抗样本</Button>
              </div>
            </Card>
          </Col>

          {/* 箭头 */}
          <Col xs={0} md={1} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ArrowRightOutlined style={{ fontSize: '24px', color: '#52c41a' }} />
          </Col>

          {/* 步骤3: 批量对抗样本生成 */}
          <Col xs={24} md={6}>
            <Card
              hoverable
              style={{ height: '100%', borderColor: '#722ed1', borderWidth: '2px', ...cardHoverStyle }}
              bodyStyle={{ padding: '24px' }}
              onClick={() => navigate('/batch-testing')}
              onMouseEnter={handleCardMouseEnter}
              onMouseLeave={handleCardMouseLeave}
            >
              <div style={{ textAlign: 'center' }}>
                <div style={{ 
                  width: '60px', 
                  height: '60px', 
                  borderRadius: '50%', 
                  background: '#f9f0ff', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '0 auto 16px'
                }}>
                  <AppstoreOutlined style={{ fontSize: '32px', color: '#722ed1' }} />
                </div>
                <div style={{ 
                  background: '#722ed1', 
                  color: '#fff', 
                  width: '32px', 
                  height: '32px', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '0 auto 12px',
                  fontWeight: 'bold',
                  fontSize: '16px'
                }}>3</div>
                <Title level={4} style={{ marginBottom: '12px' }}>批量对抗样本生成</Title>
                <Paragraph style={{ color: '#666', marginBottom: '16px' }}>
                  批量生成对抗样本，支持多模型、多任务的对比测试
                </Paragraph>
                <Button type="primary" style={{ background: '#722ed1', borderColor: '#722ed1' }} size="small">批量生成</Button>
              </div>
            </Card>
          </Col>
        </Row>

        {/* 第二排：安全测试 → 鲁棒性增强 */}
        <Row gutter={[24, 24]} justify="center" style={{ marginBottom: '24px' }}>
          {/* 步骤4: 安全测试 */}
          <Col xs={24} md={6}>
            <Card
              hoverable
              style={{ height: '100%', borderColor: '#fa8c16', borderWidth: '2px', ...cardHoverStyle }}
              bodyStyle={{ padding: '24px' }}
              onClick={() => navigate('/evaluation')}
              onMouseEnter={handleCardMouseEnter}
              onMouseLeave={handleCardMouseLeave}
            >
              <div style={{ textAlign: 'center' }}>
                <div style={{ 
                  width: '60px', 
                  height: '60px', 
                  borderRadius: '50%', 
                  background: '#fff7e6', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '0 auto 16px'
                }}>
                  <SafetyOutlined style={{ fontSize: '32px', color: '#fa8c16' }} />
                </div>
                <div style={{ 
                  background: '#fa8c16', 
                  color: '#fff', 
                  width: '32px', 
                  height: '32px', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '0 auto 12px',
                  fontWeight: 'bold',
                  fontSize: '16px'
                }}>4</div>
                <Title level={4} style={{ marginBottom: '12px' }}>安全测试</Title>
                <Paragraph style={{ color: '#666', marginBottom: '16px' }}>
                  使用测试代码集评估模型鲁棒性，输出ASR、AMI、ART等指标
                </Paragraph>
                <Button type="primary" style={{ background: '#fa8c16', borderColor: '#fa8c16' }} size="small">开始评估</Button>
              </div>
            </Card>
          </Col>

          {/* 箭头 */}
          <Col xs={0} md={1} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ArrowRightOutlined style={{ fontSize: '24px', color: '#fa8c16' }} />
          </Col>

          {/* 步骤5: 鲁棒性增强 */}
          <Col xs={24} md={6}>
            <Card
              hoverable
              style={{ height: '100%', borderColor: '#eb2f96', borderWidth: '2px', ...cardHoverStyle }}
              bodyStyle={{ padding: '24px' }}
              onClick={() => navigate('/finetuning')}
              onMouseEnter={handleCardMouseEnter}
              onMouseLeave={handleCardMouseLeave}
            >
              <div style={{ textAlign: 'center' }}>
                <div style={{ 
                  width: '60px', 
                  height: '60px', 
                  borderRadius: '50%', 
                  background: '#fff0f6', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '0 auto 16px'
                }}>
                  <SafetyCertificateOutlined style={{ fontSize: '32px', color: '#eb2f96' }} />
                </div>
                <div style={{ 
                  background: '#eb2f96', 
                  color: '#fff', 
                  width: '32px', 
                  height: '32px', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '0 auto 12px',
                  fontWeight: 'bold',
                  fontSize: '16px'
                }}>5</div>
                <Title level={4} style={{ marginBottom: '12px' }}>鲁棒性增强</Title>
                <Paragraph style={{ color: '#666', marginBottom: '16px' }}>
                  通过在线对抗训练提升模型鲁棒性，输出增强后的模型
                </Paragraph>
                <Button type="primary" style={{ background: '#eb2f96', borderColor: '#eb2f96' }} size="small">开始增强</Button>
              </div>
            </Card>
          </Col>
        </Row>

        {/* 流程说明 */}
        <Card style={{ background: '#f0f2f5', borderColor: '#d9d9d9' }}>
          <Title level={4} style={{ textAlign: 'center', marginBottom: '16px' }}>完整工作流程</Title>
          <Row gutter={16} align="middle">
            <Col xs={24} md={24} lg={24 / 5} style={{ textAlign: 'center', padding: '12px' }}>
              <Text strong style={{ fontSize: '14px', color: '#1890ff' }}>
                <CloudUploadOutlined style={{ marginRight: '8px' }} />
                上传模型
              </Text>
            </Col>
            <Col xs={0} lg={24 / 5} style={{ textAlign: 'center', padding: '12px' }}>
              <Text strong style={{ fontSize: '14px', color: '#52c41a' }}>
                <ThunderboltOutlined style={{ marginRight: '8px' }} />
                单个样本测试
              </Text>
            </Col>
            <Col xs={24} md={24} lg={24 / 5} style={{ textAlign: 'center', padding: '12px' }}>
              <Text strong style={{ fontSize: '14px', color: '#722ed1' }}>
                <AppstoreOutlined style={{ marginRight: '8px' }} />
                批量样本生成
              </Text>
            </Col>
            <Col xs={24} md={12} lg={24 / 5} style={{ textAlign: 'center', padding: '12px' }}>
              <Text strong style={{ fontSize: '14px', color: '#fa8c16' }}>
                <SafetyOutlined style={{ marginRight: '8px' }} />
                安全测试
              </Text>
            </Col>
            <Col xs={24} md={12} lg={24 / 5} style={{ textAlign: 'center', padding: '12px' }}>
              <Text strong style={{ fontSize: '14px', color: '#eb2f96' }}>
                <SafetyCertificateOutlined style={{ marginRight: '8px' }} />
                鲁棒性增强
              </Text>
            </Col>
          </Row>
          <Paragraph style={{ textAlign: 'center', marginTop: '16px', marginBottom: '0', color: '#666' }}>
            从模型接入到鲁棒性增强的完整自动化流程，全面保障代码模型的安全性与可靠性
          </Paragraph>
        </Card>
      </div>
    </div>
  );
};

export default Home;
