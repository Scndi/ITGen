import React, { useState, useEffect } from 'react';
import { Layout, Menu, Avatar, Button, Dropdown, Space, Divider } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  HomeOutlined,
  RobotOutlined,
  BugOutlined,
  BarChartOutlined,
  SettingOutlined,
  ExperimentOutlined,
  SafetyOutlined,
  AppstoreOutlined,
  UserOutlined,
  LogoutOutlined,
  LoginOutlined
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

const { Sider } = Layout;

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [currentUser, setCurrentUser] = useState<any>(null);

  useEffect(() => {
    // 获取当前用户信息
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        setCurrentUser(JSON.parse(userStr));
      } catch (error) {
        console.error('解析用户信息失败:', error);
      }
    }
  }, []);

  const baseMenuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: '/models',
      icon: <RobotOutlined />,
      label: '模型管理',
    },
    {
      key: '/attack',
      icon: <BugOutlined />,
      label: '对抗攻击',
    },
    {
      key: '/batch-testing',
      icon: <ExperimentOutlined />,
      label: '批量对抗样本生成',
    },
    {
      key: '/evaluation',
      icon: <BarChartOutlined />,
      label: '安全测试',
    },
    {
      key: '/finetuning',
      icon: <SettingOutlined />,
      label: '鲁棒性增强',
    },
    {
      key: '/tasks',
      icon: <AppstoreOutlined />,
      label: '任务管理',
    },
  ];

  // 如果是管理员，添加管理菜单
  const menuItems = currentUser?.role === 'admin'
    ? [
        ...baseMenuItems,
        { type: 'divider' as const },
        {
          key: '/admin',
          icon: <SettingOutlined />,
          label: '系统管理',
        },
      ]
    : baseMenuItems;

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '登出',
      danger: true,
    },
  ];

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      handleLogout();
    } else if (key === 'profile') {
      // TODO: 实现个人资料页面
      console.log('个人资料');
    }
  };

  // 如果未登录，不显示侧边栏
  if (!currentUser) {
    return null;
  }

  return (
    <Sider
      width={240}
      style={{
        background: '#fff',
        boxShadow: '2px 0 8px rgba(0,0,0,0.1)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Logo区域 */}
      <div style={{
        padding: '16px',
        textAlign: 'center',
        borderBottom: '1px solid #f0f0f0',
        marginBottom: '16px'
      }}>
        <SafetyOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
        <div style={{ marginTop: '8px', fontWeight: 'bold', color: '#1890ff', fontSize: '14px' }}>
            ITGen 系统
        </div>
        <div style={{ marginTop: '4px', fontSize: '12px', color: '#666' }}>
            代码对抗攻击平台
        </div>
      </div>

      {/* 导航菜单 */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ border: 'none' }}
        />
      </div>

      {/* 用户信息区域 */}
      <div style={{
        padding: '16px',
        borderTop: '1px solid #f0f0f0',
        background: '#fafafa'
      }}>
        <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }} trigger={['click']}>
          <Button
            type="text"
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-start',
              padding: '8px 12px'
            }}
          >
            <Space>
              <Avatar
                size="small"
                style={{
                  backgroundColor: currentUser.role === 'admin' ? '#f5222d' : '#1890ff'
                }}
              >
                {currentUser.role === 'admin' ? <SettingOutlined /> : <UserOutlined />}
              </Avatar>
              <div style={{ textAlign: 'left', flex: 1 }}>
                <div style={{
                  fontSize: '12px',
                  fontWeight: 'bold',
                  color: '#000',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: '140px'
                }}>
                  {currentUser.full_name || currentUser.username}
                </div>
                <div style={{
                  fontSize: '11px',
                  color: '#666',
                  marginTop: '2px'
                }}>
                  {currentUser.role === 'admin' ? '管理员' : '普通用户'}
                </div>
              </div>
            </Space>
          </Button>
        </Dropdown>
      </div>
    </Sider>
  );
};

export default Sidebar;
