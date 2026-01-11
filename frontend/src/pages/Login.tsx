import React, { useState } from 'react';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Tab,
  Tabs,
  Alert,
  CircularProgress,
  Link,
  Grid,
  Avatar,
  FormControlLabel,
  Checkbox
} from '@mui/material';
import { LockOutlined, PersonAdd } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`auth-tabpanel-${index}`}
      aria-labelledby={`auth-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const Login: React.FC = () => {
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // 登录表单
  const [loginData, setLoginData] = useState({
    username: '',
    password: '',
    remember: false
  });

  // 注册表单
  const [registerData, setRegisterData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
    department: ''
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setError('');
  };

  const handleLoginChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setLoginData({
      ...loginData,
      [field]: field === 'remember' ? event.target.checked : event.target.value
    });
  };

  const handleRegisterChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setRegisterData({
      ...registerData,
      [field]: event.target.value
    });
  };

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!loginData.username || !loginData.password) {
      setError('请输入用户名和密码');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await authAPI.login(loginData.username, loginData.password);

      if (response.success) {
        localStorage.setItem('token', response.token || '');
        localStorage.setItem('user', JSON.stringify(response.user));

        // 根据用户角色跳转
        if (response.user.role === 'admin') {
          navigate('/admin');
        } else {
          navigate('/');
        }
      } else {
        setError(response.message || '登录失败');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '登录失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!registerData.username || !registerData.email || !registerData.password) {
      setError('请填写所有必填字段');
      return;
    }

    if (registerData.password !== registerData.confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    if (registerData.password.length < 6) {
      setError('密码长度至少6位');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await authAPI.register({
        username: registerData.username,
        email: registerData.email,
        password: registerData.password,
        full_name: registerData.fullName,
        department: registerData.department
      });

      if (response.success) {
        setError('');
        alert('注册成功！请登录您的账户。');
        setTabValue(0); // 切换到登录标签
        setRegisterData({
          username: '',
          email: '',
          password: '',
          confirmPassword: '',
          fullName: '',
          department: ''
        });
      } else {
        setError(response.message || '注册失败');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '注册失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container component="main" maxWidth="sm" sx={{ mt: 8 }}>
      <Paper
        elevation={6}
        sx={{
          p: 4,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          borderRadius: 2
        }}
      >
        <Avatar sx={{ m: 1, bgcolor: 'primary.main' }}>
          <LockOutlined />
        </Avatar>
        <Typography component="h1" variant="h4" gutterBottom>
          ITGen 系统
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          代码对抗攻击生成与鲁棒性评估平台
        </Typography>

        <Box sx={{ borderBottom: 1, borderColor: 'divider', width: '100%' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="auth tabs">
            <Tab label="登录" />
            <Tab label="注册" />
          </Tabs>
        </Box>

        {error && (
          <Alert severity="error" sx={{ width: '100%', mt: 2 }}>
            {error}
          </Alert>
        )}

        {/* 登录表单 */}
        <TabPanel value={tabValue} index={0}>
          <Box component="form" onSubmit={handleLogin} sx={{ mt: 1, width: '100%' }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="username"
              label="用户名或邮箱"
              name="username"
              autoComplete="username"
              autoFocus
              value={loginData.username}
              onChange={handleLoginChange('username')}
              disabled={loading}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="密码"
              type="password"
              id="password"
              autoComplete="current-password"
              value={loginData.password}
              onChange={handleLoginChange('password')}
              disabled={loading}
            />
            <FormControlLabel
              control={
                <Checkbox
                  value={loginData.remember}
                  onChange={handleLoginChange('remember')}
                  color="primary"
                  disabled={loading}
                />
              }
              label="记住我"
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2, height: 48 }}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : '登录'}
            </Button>
            <Grid container>
              <Grid item xs>
                <Link href="#" variant="body2">
                  忘记密码？
                </Link>
              </Grid>
            </Grid>
          </Box>
        </TabPanel>

        {/* 注册表单 */}
        <TabPanel value={tabValue} index={1}>
          <Box component="form" onSubmit={handleRegister} sx={{ mt: 1, width: '100%' }}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  autoComplete="username"
                  name="username"
                  required
                  fullWidth
                  id="register-username"
                  label="用户名"
                  value={registerData.username}
                  onChange={handleRegisterChange('username')}
                  disabled={loading}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  required
                  fullWidth
                  id="email"
                  label="邮箱地址"
                  name="email"
                  autoComplete="email"
                  value={registerData.email}
                  onChange={handleRegisterChange('email')}
                  disabled={loading}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  required
                  fullWidth
                  id="fullName"
                  label="真实姓名"
                  name="fullName"
                  autoComplete="name"
                  value={registerData.fullName}
                  onChange={handleRegisterChange('fullName')}
                  disabled={loading}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  id="department"
                  label="部门（可选）"
                  name="department"
                  value={registerData.department}
                  onChange={handleRegisterChange('department')}
                  disabled={loading}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  required
                  fullWidth
                  name="password"
                  label="密码"
                  type="password"
                  id="register-password"
                  autoComplete="new-password"
                  value={registerData.password}
                  onChange={handleRegisterChange('password')}
                  disabled={loading}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  required
                  fullWidth
                  name="confirmPassword"
                  label="确认密码"
                  type="password"
                  id="confirm-password"
                  value={registerData.confirmPassword}
                  onChange={handleRegisterChange('confirmPassword')}
                  disabled={loading}
                />
              </Grid>
            </Grid>
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2, height: 48 }}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : '注册'}
            </Button>
          </Box>
        </TabPanel>
      </Paper>

      <Box sx={{ mt: 4, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          默认管理员账户：admin / admin123<br/>
          默认普通用户：demo_user / user123
        </Typography>
      </Box>
    </Container>
  );
};

export default Login;
