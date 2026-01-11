import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Chip,
  Alert,
  Card,
  CardContent,
  CardHeader,
  Avatar,
  CircularProgress
} from '@mui/material';
import {
  Edit,
  Delete,
  Add,
  AdminPanelSettings,
  People,
  Assessment,
  Security,
  Settings
} from '@mui/icons-material';
import { userAPI, taskAPI, adminAPI } from '../services/api';

interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  status: string;
  department: string;
  position: string;
  last_login: string;
  created_at: string;
}

interface Model {
  id: number;
  model_name: string;
  model_type: string;
  description: string;
  model_path: string;
  tokenizer_path: string;
  mlm_model_path?: string;
  checkpoint_path?: string;
  status: string;
  model_source: string;
  supported_tasks: string[];
  user_id?: number;
  created_at: string;
}

interface Dataset {
  id: number;
  dataset_name: string;
  task_type: string;
  description: string;
  dataset_path: string;
  status: string;
  source: string;
  file_count: number;
  file_types: string[];
  total_size: number;
  user_id?: number;
  created_at: string;
}

interface Task {
  id: string;
  task_type: string;
  status: string;
  progress: number;
  created_at: string;
  model_name?: string;
  dataset_name?: string;
}

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
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Admin: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [users, setUsers] = useState<User[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    totalTasks: 0,
    runningTasks: 0,
    totalModels: 0,
    totalDatasets: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 用户管理对话框
  const [userDialog, setUserDialog] = useState({
    open: false,
    mode: 'add', // 'add' or 'edit'
    user: null as User | null
  });

  const [userForm, setUserForm] = useState({
    username: '',
    email: '',
    full_name: '',
    role: 'user',
    status: 'active',
    department: '',
    position: ''
  });

  // 模型管理对话框
  const [modelDialog, setModelDialog] = useState({
    open: false,
    mode: 'add', // 'add' or 'edit'
    model: null as Model | null
  });

  const [modelForm, setModelForm] = useState({
    model_name: '',
    model_type: 'bert',
    description: '',
    model_path: '',
    tokenizer_path: '',
    mlm_model_path: '',
    checkpoint_path: '',
    model_source: 'user',
    max_length: 512,
    status: 'available',
    supported_tasks: [] as string[]
  });

  // 数据集管理对话框
  const [datasetDialog, setDatasetDialog] = useState({
    open: false,
    mode: 'add', // 'add' or 'edit'
    dataset: null as Dataset | null
  });

  const [datasetForm, setDatasetForm] = useState({
    dataset_name: '',
    task_type: 'clone-detection',
    description: '',
    dataset_path: '',
    file_count: 0,
    file_types: [] as string[],
    total_size: 0,
    source: 'user',
    status: 'available'
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);

      // 加载用户数据
      const usersResponse = await userAPI.getAllUsers();
      if (usersResponse.success) {
        setUsers(usersResponse.users || []);
      }

      // 加载任务数据
      const tasksResponse = await taskAPI.getAllTasks();
      if (tasksResponse.success) {
        setTasks(tasksResponse.tasks || []);
      }

      // 加载模型数据
      const modelsResponse = await adminAPI.getAllModels();
      if (modelsResponse.success) {
        setModels(modelsResponse.models || []);
      }

      // 加载数据集数据
      const datasetsResponse = await adminAPI.getAllDatasets();
      if (datasetsResponse.success) {
        setDatasets(datasetsResponse.datasets || []);
      }

      // 计算统计信息
      const totalUsers = usersResponse.users?.length || 0;
      const activeUsers = usersResponse.users?.filter(u => u.status === 'active').length || 0;
      const totalTasks = tasksResponse.tasks?.length || 0;
      const runningTasks = tasksResponse.tasks?.filter((t: Task) => t.status === 'running').length || 0;
      const totalModels = modelsResponse.models?.length || 0;
      const totalDatasets = datasetsResponse.datasets?.length || 0;

      setStats({
        totalUsers,
        activeUsers,
        totalTasks,
        runningTasks,
        totalModels,
        totalDatasets
      });

    } catch (err: any) {
      setError('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleUserDialogOpen = (mode: 'add' | 'edit', user?: User) => {
    if (mode === 'edit' && user) {
      setUserForm({
        username: user.username,
        email: user.email,
        full_name: user.full_name || '',
        role: user.role,
        status: user.status,
        department: user.department || '',
        position: user.position || ''
      });
      setUserDialog({ open: true, mode, user });
    } else {
      setUserForm({
        username: '',
        email: '',
        full_name: '',
        role: 'user',
        status: 'active',
        department: '',
        position: ''
      });
      setUserDialog({ open: true, mode, user: null });
    }
  };

  const handleUserDialogClose = () => {
    setUserDialog({ open: false, mode: 'add', user: null });
  };

  const handleUserFormChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setUserForm({
      ...userForm,
      [field]: event.target.value
    });
  };

  const handleUserSubmit = async () => {
    try {
      if (userDialog.mode === 'add') {
        const response = await userAPI.createUser(userForm);
        if (response.success) {
          await loadData();
          handleUserDialogClose();
        }
      } else if (userDialog.mode === 'edit' && userDialog.user) {
        const response = await userAPI.updateUser(userDialog.user.id, userForm);
        if (response.success) {
          await loadData();
          handleUserDialogClose();
        }
      }
    } catch (err: any) {
      setError('操作失败');
    }
  };

  const handleUserDelete = async (userId: number) => {
    if (window.confirm('确定要删除这个用户吗？')) {
      try {
        const response = await userAPI.deleteUser(userId);
        if (response.success) {
          await loadData();
        }
      } catch (err: any) {
        setError('删除失败');
      }
    }
  };

  // 模型管理处理函数
  const handleModelDialogOpen = (mode: 'add' | 'edit', model?: Model) => {
    if (mode === 'edit' && model) {
      setModelForm({
        model_name: model.model_name,
        model_type: model.model_type,
        description: model.description,
        model_path: model.model_path,
        tokenizer_path: model.tokenizer_path,
        mlm_model_path: model.mlm_model_path || '',
        checkpoint_path: model.checkpoint_path || '',
        model_source: model.model_source,
        max_length: 512, // API中没有返回这个字段
        status: model.status,
        supported_tasks: model.supported_tasks
      });
    } else {
      setModelForm({
        model_name: '',
        model_type: 'bert',
        description: '',
        model_path: '',
        tokenizer_path: '',
        mlm_model_path: '',
        checkpoint_path: '',
        model_source: 'user',
        max_length: 512,
        status: 'available',
        supported_tasks: []
      });
    }
    setModelDialog({ open: true, mode, model: model || null });
  };

  const handleModelDialogClose = () => {
    setModelDialog({ open: false, mode: 'add', model: null });
  };

  const handleModelSubmit = async () => {
    try {
      let response;
      if (modelDialog.mode === 'add') {
        response = await adminAPI.createModel(modelForm);
      } else if (modelDialog.mode === 'edit' && modelDialog.model) {
        response = await adminAPI.updateModel(modelDialog.model.id, modelForm);
      }

      if (response?.success) {
        await loadData();
        handleModelDialogClose();
      } else {
        setError(response?.message || '操作失败');
      }
    } catch (err: any) {
      setError('操作失败');
    }
  };

  const handleModelDelete = async (modelId: number) => {
    if (window.confirm('确定要删除这个模型吗？')) {
      try {
        const response = await adminAPI.deleteModel(modelId);
        if (response.success) {
          await loadData();
        } else {
          setError(response.message || '删除失败');
        }
      } catch (err: any) {
        setError('删除失败');
      }
    }
  };

  // 数据集管理处理函数
  const handleDatasetDialogOpen = (mode: 'add' | 'edit', dataset?: Dataset) => {
    if (mode === 'edit' && dataset) {
      setDatasetForm({
        dataset_name: dataset.dataset_name,
        task_type: dataset.task_type,
        description: dataset.description,
        dataset_path: dataset.dataset_path,
        file_count: dataset.file_count,
        file_types: dataset.file_types,
        total_size: dataset.total_size,
        source: dataset.source,
        status: dataset.status
      });
    } else {
      setDatasetForm({
        dataset_name: '',
        task_type: 'clone-detection',
        description: '',
        dataset_path: '',
        file_count: 0,
        file_types: [],
        total_size: 0,
        source: 'user',
        status: 'available'
      });
    }
    setDatasetDialog({ open: true, mode, dataset: dataset || null });
  };

  const handleDatasetDialogClose = () => {
    setDatasetDialog({ open: false, mode: 'add', dataset: null });
  };

  const handleDatasetSubmit = async () => {
    try {
      let response;
      if (datasetDialog.mode === 'add') {
        response = await adminAPI.createDataset(datasetForm);
      } else if (datasetDialog.mode === 'edit' && datasetDialog.dataset) {
        response = await adminAPI.updateDataset(datasetDialog.dataset.id, datasetForm);
      }

      if (response?.success) {
        await loadData();
        handleDatasetDialogClose();
      } else {
        setError(response?.message || '操作失败');
      }
    } catch (err: any) {
      setError('操作失败');
    }
  };

  const handleDatasetDelete = async (datasetId: number) => {
    if (window.confirm('确定要删除这个数据集吗？')) {
      try {
        const response = await adminAPI.deleteDataset(datasetId);
        if (response.success) {
          await loadData();
        } else {
          setError(response.message || '删除失败');
        }
      } catch (err: any) {
        setError('删除失败');
      }
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'inactive': return 'warning';
      case 'suspended': return 'error';
      default: return 'default';
    }
  };

  const getRoleIcon = (role: string) => {
    return role === 'admin' ? <AdminPanelSettings /> : <People />;
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <AdminPanelSettings sx={{ mr: 2 }} />
        系统管理后台
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* 统计卡片 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                总用户数
              </Typography>
              <Typography variant="h4">
                {stats.totalUsers}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                活跃用户
              </Typography>
              <Typography variant="h4" color="success.main">
                {stats.activeUsers}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                总任务数
              </Typography>
              <Typography variant="h4">
                {stats.totalTasks}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                运行中任务
              </Typography>
              <Typography variant="h4" color="warning.main">
                {stats.runningTasks}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 标签页 */}
      <Paper sx={{ width: '100%' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="admin tabs">
          <Tab icon={<People />} label="用户管理" />
          <Tab icon={<Settings />} label="模型管理" />
          <Tab icon={<Assessment />} label="数据集管理" />
          <Tab icon={<AdminPanelSettings />} label="任务监控" />
          <Tab icon={<Security />} label="系统统计" />
        </Tabs>

        {/* 用户管理 */}
        <TabPanel value={tabValue} index={0}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">用户管理</Typography>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => handleUserDialogOpen('add')}
            >
              添加用户
            </Button>
          </Box>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>用户名</TableCell>
                  <TableCell>邮箱</TableCell>
                  <TableCell>角色</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>部门</TableCell>
                  <TableCell>最后登录</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar sx={{ mr: 2, width: 32, height: 32 }}>
                          {getRoleIcon(user.role)}
                        </Avatar>
                        <Box>
                          <Typography variant="body2" fontWeight="bold">
                            {user.username}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {user.full_name}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <Chip
                        icon={getRoleIcon(user.role)}
                        label={user.role === 'admin' ? '管理员' : '普通用户'}
                        color={user.role === 'admin' ? 'primary' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={user.status === 'active' ? '活跃' :
                              user.status === 'inactive' ? '未激活' : '已暂停'}
                        color={getStatusColor(user.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{user.department || '-'}</TableCell>
                    <TableCell>
                      {user.last_login ? new Date(user.last_login).toLocaleString() : '从未登录'}
                    </TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => handleUserDialogOpen('edit', user)}
                      >
                        <Edit />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleUserDelete(user.id)}
                        disabled={user.role === 'admin' && user.username === 'admin'}
                      >
                        <Delete />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* 模型管理 */}
        <TabPanel value={tabValue} index={1}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">模型管理</Typography>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => handleModelDialogOpen('add')}
            >
              添加模型
            </Button>
          </Box>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>模型名称</TableCell>
                  <TableCell>类型</TableCell>
                  <TableCell>来源</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>创建时间</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {models.map((model) => (
                  <TableRow key={model.id}>
                    <TableCell>{model.model_name}</TableCell>
                    <TableCell>{model.model_type}</TableCell>
                    <TableCell>
                      <Chip
                        label={model.model_source}
                        size="small"
                        color={model.model_source === 'official' ? 'primary' : 'default'}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={model.status}
                        size="small"
                        color={model.status === 'available' ? 'success' : 'warning'}
                      />
                    </TableCell>
                    <TableCell>{new Date(model.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => handleModelDialogOpen('edit', model)}
                      >
                        <Edit />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleModelDelete(model.id)}
                      >
                        <Delete />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* 数据集管理 */}
        <TabPanel value={tabValue} index={2}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">数据集管理</Typography>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => handleDatasetDialogOpen('add')}
            >
              添加数据集
            </Button>
          </Box>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>数据集名称</TableCell>
                  <TableCell>任务类型</TableCell>
                  <TableCell>来源</TableCell>
                  <TableCell>文件数量</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>创建时间</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {datasets.map((dataset) => (
                  <TableRow key={dataset.id}>
                    <TableCell>{dataset.dataset_name}</TableCell>
                    <TableCell>{dataset.task_type}</TableCell>
                    <TableCell>
                      <Chip
                        label={dataset.source}
                        size="small"
                        color={dataset.source === 'official' ? 'primary' : 'default'}
                      />
                    </TableCell>
                    <TableCell>{dataset.file_count}</TableCell>
                    <TableCell>
                      <Chip
                        label={dataset.status}
                        size="small"
                        color={dataset.status === 'available' ? 'success' : 'warning'}
                      />
                    </TableCell>
                    <TableCell>{new Date(dataset.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => handleDatasetDialogOpen('edit', dataset)}
                      >
                        <Edit />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDatasetDelete(dataset.id)}
                      >
                        <Delete />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* 任务监控 */}
        <TabPanel value={tabValue} index={3}>
          <Typography variant="h6" gutterBottom>
            任务监控
          </Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>任务ID</TableCell>
                  <TableCell>任务类型</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>进度</TableCell>
                  <TableCell>模型</TableCell>
                  <TableCell>数据集</TableCell>
                  <TableCell>创建时间</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tasks.slice(0, 10).map((task) => (
                  <TableRow key={task.id}>
                    <TableCell>{task.id.substring(0, 8)}...</TableCell>
                    <TableCell>{task.task_type}</TableCell>
                    <TableCell>
                      <Chip
                        label={task.status}
                        color={task.status === 'completed' ? 'success' :
                              task.status === 'running' ? 'warning' :
                              task.status === 'failed' ? 'error' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{task.progress}%</TableCell>
                    <TableCell>{task.model_name || '-'}</TableCell>
                    <TableCell>{task.dataset_name || '-'}</TableCell>
                    <TableCell>{new Date(task.created_at).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* 系统统计 */}
        <TabPanel value={tabValue} index={4}>
          <Typography variant="h6" gutterBottom>
            系统统计
          </Typography>

          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardHeader
                  avatar={<People color="primary" />}
                  title="用户统计"
                />
                <CardContent>
                  <Typography variant="h6">总用户数: {stats.totalUsers}</Typography>
                  <Typography variant="h6">活跃用户: {stats.activeUsers}</Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardHeader
                  avatar={<Settings color="secondary" />}
                  title="模型统计"
                />
                <CardContent>
                  <Typography variant="h6">总模型数: {stats.totalModels}</Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardHeader
                  avatar={<Assessment color="success" />}
                  title="数据集统计"
                />
                <CardContent>
                  <Typography variant="h6">总数据集数: {stats.totalDatasets}</Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardHeader
                  avatar={<AdminPanelSettings color="warning" />}
                  title="任务统计"
                />
                <CardContent>
                  <Typography variant="h6">总任务数: {stats.totalTasks}</Typography>
                  <Typography variant="h6">运行中: {stats.runningTasks}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Paper>

      {/* 用户管理对话框 */}
      <Dialog open={userDialog.open} onClose={handleUserDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>
          {userDialog.mode === 'add' ? '添加用户' : '编辑用户'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="用户名"
                value={userForm.username}
                onChange={handleUserFormChange('username')}
                disabled={userDialog.mode === 'edit'}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="邮箱"
                type="email"
                value={userForm.email}
                onChange={handleUserFormChange('email')}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="真实姓名"
                value={userForm.full_name}
                onChange={handleUserFormChange('full_name')}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                fullWidth
                label="角色"
                value={userForm.role}
                onChange={handleUserFormChange('role')}
              >
                <MenuItem value="user">普通用户</MenuItem>
                <MenuItem value="admin">管理员</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                fullWidth
                label="状态"
                value={userForm.status}
                onChange={handleUserFormChange('status')}
              >
                <MenuItem value="active">活跃</MenuItem>
                <MenuItem value="inactive">未激活</MenuItem>
                <MenuItem value="suspended">已暂停</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="部门"
                value={userForm.department}
                onChange={handleUserFormChange('department')}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="职位"
                value={userForm.position}
                onChange={handleUserFormChange('position')}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleUserDialogClose}>取消</Button>
          <Button onClick={handleUserSubmit} variant="contained">
            {userDialog.mode === 'add' ? '添加' : '更新'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 模型管理对话框 */}
      <Dialog open={modelDialog.open} onClose={handleModelDialogClose} maxWidth="md" fullWidth>
        <DialogTitle>
          {modelDialog.mode === 'add' ? '添加模型' : '编辑模型'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                required
                label="模型名称"
                value={modelForm.model_name}
                onChange={(e) => setModelForm({...modelForm, model_name: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                required
                select
                label="模型类型"
                value={modelForm.model_type}
                onChange={(e) => setModelForm({...modelForm, model_type: e.target.value})}
              >
                <MenuItem value="bert">BERT</MenuItem>
                <MenuItem value="gpt2">GPT-2</MenuItem>
                <MenuItem value="roberta">RoBERTa</MenuItem>
                <MenuItem value="codet5">CodeT5</MenuItem>
                <MenuItem value="bart">BART</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={2}
                label="描述"
                value={modelForm.description}
                onChange={(e) => setModelForm({...modelForm, description: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                required
                label="模型路径"
                value={modelForm.model_path}
                onChange={(e) => setModelForm({...modelForm, model_path: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                required
                label="Tokenizer路径"
                value={modelForm.tokenizer_path}
                onChange={(e) => setModelForm({...modelForm, tokenizer_path: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="MLM模型路径"
                value={modelForm.mlm_model_path}
                onChange={(e) => setModelForm({...modelForm, mlm_model_path: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="检查点路径"
                value={modelForm.checkpoint_path}
                onChange={(e) => setModelForm({...modelForm, checkpoint_path: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="来源"
                value={modelForm.model_source}
                onChange={(e) => setModelForm({...modelForm, model_source: e.target.value})}
              >
                <MenuItem value="official">官方</MenuItem>
                <MenuItem value="user">用户上传</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="状态"
                value={modelForm.status}
                onChange={(e) => setModelForm({...modelForm, status: e.target.value})}
              >
                <MenuItem value="available">可用</MenuItem>
                <MenuItem value="unavailable">不可用</MenuItem>
              </TextField>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleModelDialogClose}>取消</Button>
          <Button onClick={handleModelSubmit} variant="contained">
            {modelDialog.mode === 'add' ? '添加' : '更新'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 数据集管理对话框 */}
      <Dialog open={datasetDialog.open} onClose={handleDatasetDialogClose} maxWidth="md" fullWidth>
        <DialogTitle>
          {datasetDialog.mode === 'add' ? '添加数据集' : '编辑数据集'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                required
                label="数据集名称"
                value={datasetForm.dataset_name}
                onChange={(e) => setDatasetForm({...datasetForm, dataset_name: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                required
                select
                label="任务类型"
                value={datasetForm.task_type}
                onChange={(e) => setDatasetForm({...datasetForm, task_type: e.target.value})}
              >
                <MenuItem value="clone-detection">克隆检测</MenuItem>
                <MenuItem value="vulnerability-prediction">漏洞预测</MenuItem>
                <MenuItem value="code-summarization">代码摘要</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={2}
                label="描述"
                value={datasetForm.description}
                onChange={(e) => setDatasetForm({...datasetForm, description: e.target.value})}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                required
                label="数据集路径"
                value={datasetForm.dataset_path}
                onChange={(e) => setDatasetForm({...datasetForm, dataset_path: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="文件数量"
                value={datasetForm.file_count}
                onChange={(e) => setDatasetForm({...datasetForm, file_count: parseInt(e.target.value) || 0})}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="总大小(字节)"
                value={datasetForm.total_size}
                onChange={(e) => setDatasetForm({...datasetForm, total_size: parseInt(e.target.value) || 0})}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                select
                label="来源"
                value={datasetForm.source}
                onChange={(e) => setDatasetForm({...datasetForm, source: e.target.value})}
              >
                <MenuItem value="official">官方</MenuItem>
                <MenuItem value="user">用户上传</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="状态"
                value={datasetForm.status}
                onChange={(e) => setDatasetForm({...datasetForm, status: e.target.value})}
              >
                <MenuItem value="available">可用</MenuItem>
                <MenuItem value="unavailable">不可用</MenuItem>
              </TextField>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDatasetDialogClose}>取消</Button>
          <Button onClick={handleDatasetSubmit} variant="contained">
            {datasetDialog.mode === 'add' ? '添加' : '更新'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Admin;
