import React, { useState, useEffect } from 'react';
import { Layout, Typography, Avatar, Button, Dropdown, Space, Badge } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  BellOutlined
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

const { Header: AntHeader } = Layout;
const { Title } = Typography;

const Header: React.FC = () => {
  const navigate = useNavigate();
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
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置',
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
    } else if (key === 'settings') {
      // TODO: 实现设置页面
      console.log('设置');
    }
  };

  // 如果未登录，不显示Header
  if (!currentUser) {
    return null;
  }

  return (
    <AntHeader style={{
      background: '#fff',
      padding: '0 24px',
      borderBottom: '1px solid #f0f0f0',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)'
    }}>
      <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
        ITGen 代码对抗攻击生成与鲁棒性评估平台
      </Title>

      <Space>
        {/* 通知按钮 */}
        <Button
          type="text"
          icon={<Badge count={0} size="small"><BellOutlined /></Badge>}
          style={{ color: '#666' }}
        />

        {/* 用户菜单 */}
        <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }} trigger={['click']}>
          <Button
            type="text"
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '4px 8px',
              height: 'auto'
            }}
          >
            <Space>
              <Avatar
                size="small"
                style={{
                  backgroundColor: currentUser.role === 'admin' ? '#f5222d' : '#1890ff'
                }}
              >
                {currentUser.role === 'admin' ? '管' : '用'}
              </Avatar>
              <span style={{ color: '#666', fontSize: '14px' }}>
                {currentUser.full_name || currentUser.username}
              </span>
            </Space>
          </Button>
        </Dropdown>
      </Space>
    </AntHeader>
  );
};

export default Header;
