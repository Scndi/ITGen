import axios, { AxiosInstance, AxiosResponse } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://172.28.241.93:5000';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 120000, // 增加到120秒，适应长时间运行的任务
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 请求拦截器
    this.api.interceptors.request.use(
      (config) => {
        console.log('API请求:', config.method?.toUpperCase(), config.url);

        // 添加认证token
        const token = localStorage.getItem('token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
      },
      (error) => {
        console.error('API请求错误:', error);
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.api.interceptors.response.use(
      (response: AxiosResponse) => {
        console.log('API响应:', response.status, response.config.url);
        return response;
      },
      (error) => {
        console.error('API响应错误:', error);
        return Promise.reject(error);
      }
    );
  }

  // ===== 用户认证API =====
  async login(username: string, password: string): Promise<{
    success: boolean;
    token?: string;
    user?: any;
    message?: string;
  }> {
    try {
      const response = await this.api.post('/auth/login', { username, password });
      return {
        success: true,
        token: response.data.token,
        user: response.data.user
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '登录失败'
      };
    }
  }

  async register(userData: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
    department?: string;
  }): Promise<{
    success: boolean;
    message?: string;
  }> {
    try {
      await this.api.post('/auth/register', userData);
      return { success: true };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '注册失败'
      };
    }
  }

  async getCurrentUser(): Promise<{
    success: boolean;
    user?: any;
    message?: string;
  }> {
    try {
      const response = await this.api.get('/auth/me');
      return {
        success: true,
        user: response.data.user
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '获取用户信息失败'
      };
    }
  }

  // ===== 用户管理API =====
  async getAllUsers(): Promise<{
    success: boolean;
    users?: any[];
    message?: string;
  }> {
    try {
      const response = await this.api.get('/admin/users');
      return {
        success: true,
        users: response.data.users
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '获取用户列表失败'
      };
    }
  }

  async createUser(userData: any): Promise<{
    success: boolean;
    user?: any;
    message?: string;
  }> {
    try {
      const response = await this.api.post('/admin/users', userData);
      return {
        success: true,
        user: response.data.user
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '创建用户失败'
      };
    }
  }

  async updateUser(userId: number, userData: any): Promise<{
    success: boolean;
    user?: any;
    message?: string;
  }> {
    try {
      const response = await this.api.put(`/admin/users/${userId}`, userData);
      return {
        success: true,
        user: response.data.user
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '更新用户失败'
      };
    }
  }

  async deleteUser(userId: number): Promise<{
    success: boolean;
    message?: string;
  }> {
    try {
      await this.api.delete(`/admin/users/${userId}`);
      return { success: true };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '删除用户失败'
      };
    }
  }

  async resetUserPassword(userId: number): Promise<{
    success: boolean;
    new_password?: string;
    message?: string;
  }> {
    try {
      const response = await this.api.post(`/admin/users/${userId}/reset-password`);
      return {
        success: true,
        new_password: response.data.new_password
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '重置密码失败'
      };
    }
  }

  // ===== 模型管理API =====
  // 基础类型定义
  public static readonly SupportedTasks = ['clone_detection','vulnerability_detection','code_summarization','code_generation'] as const;
  public static readonly ModelTypes = ['encoder','decoder','encoder-decoder'] as const;

  async getModels(): Promise<{
    success: boolean;
    data: Array<{
      id: string;
      model_name: string;
      description: string;
      model_path: string;
      tokenizer_path: string;
      max_length: number;
      supported_tasks: string[];
      model_type?: string;
      status: string;
      is_predefined: boolean;
    }>;
  }> {
    try {
      console.log('📡 获取模型列表...');
      const response = await this.api.get('/api/models');
      console.log('✅ 模型列表获取成功:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('❌ 获取模型列表失败:', error.message);
      return { success: false, data: [] };
    }
  }

  async addModel(modelData: {
    model_name: string;
    model_type: string; // 前端必填：模型类型
    description: string;
    model_path: string;
    tokenizer_path: string;
    max_length: number;
    supported_tasks: string[];
  }): Promise<{ success: boolean; model_id?: string; error?: string }> {
    const response = await this.api.post('/api/models', modelData);
    return response.data;
  }

  // 删除模型功能已移至管理员API (deleteModelAdmin)

  // ===== 新的异步任务管理系统API =====

  // 任务管理API（使用attack/status端点避免认证问题）
  async getTask(taskId: string) {
    console.log('🔍 getTask 调用:', taskId);
    console.log('🌐 请求URL:', this.api.defaults.baseURL + `/api/attack/status/${taskId}`);

    try {
      const response = await this.api.get(`/api/attack/status/${taskId}`, {
        timeout: 10000 // 10秒超时
      });
      console.log('✅ getTask 响应:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('❌ getTask 失败:', error.message);
      
      // 如果是404错误（任务不存在），直接抛出错误，让前端处理
      if (error.response?.status === 404) {
        console.log('⚠️ 任务不存在 (404)');
        return {
          success: false,
          error: '任务不存在',
          task_not_found: true
        };
      }

      // 返回真实的错误信息
      console.error('❌ API连接失败:', error.message);
      return {
        success: false,
        error: error.message || '网络连接失败',
        status: {
          status: 'failed',
          progress: 0,
          message: 'API连接失败，无法获取任务状态',
          error: error.message || '网络连接失败'
        }
      };
    }
  }

  async getTasks(params?: {
    task_type?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) {
    const response = await this.api.get('/api/tasks', { params });
    return response.data;
  }

  async getTaskStatistics(days?: number) {
    const response = await this.api.get('/api/tasks/stats', {
      params: days ? { days } : {}
    });
    return response.data;
  }

  async cancelTask(taskId: string, reason?: string) {
    console.log('📡 前端取消任务请求:', taskId, '原因:', reason);
    console.log('🌐 请求URL:', `${this.api.defaults.baseURL}/api/task/${taskId}/cancel`);

    try {
      const response = await this.api.post(`/api/task/${taskId}/cancel`, {
        reason: reason || '用户主动取消'
      });
      console.log('✅ 取消任务响应成功:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('❌ 取消任务请求失败:', error);
      console.error('🔍 错误详情:', {
        message: error.message,
        status: error.response?.status,
        responseData: error.response?.data
      });
      throw error;
    }
  }

  async updateTaskStatus(taskId: string, statusData: any) {
    console.log('📡 更新任务状态:', taskId, statusData);
    console.log('🌐 请求URL:', this.api.defaults.baseURL + `/api/task/${taskId}/status`);

    try {
      const response = await this.api.put(`/api/task/${taskId}/status`, statusData, {
        timeout: 10000 // 10秒超时
      });
      console.log('✅ 更新任务状态响应:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('❌ 更新任务状态失败:', error.message);
      console.error('🔍 错误详情:', {
        message: error.message,
        status: error.response?.status,
        responseData: error.response?.data
      });

      // 返回真实的错误信息
      console.error('❌ API调用失败:', error.message);
      return {
        success: false,
        error: error.message || 'API调用失败',
        message: '任务状态更新失败'
      };
    }
  }

  async getQueueStatus(queueName?: string) {
    const response = await this.api.get('/api/queues/status', {
      params: queueName ? { queue_name: queueName } : {}
    });
    return response.data;
  }

  // 对抗攻击API（新的异步版本）
  async startAttack(attackData: any) {
    console.log('🚀 前端API调用: startAttack');
    console.log('📤 请求数据:', attackData);
    console.log('📋 请求数据结构检查:', {
      hasMethod: 'method' in attackData,
      hasModelName: 'model_name' in attackData,
      hasTaskType: 'task_type' in attackData,
      hasCodeData: 'code_data' in attackData,
      hasParameters: 'parameters' in attackData,
      codeDataKeys: attackData.code_data ? Object.keys(attackData.code_data) : 'undefined',
      methodValue: attackData.method,
      modelNameValue: attackData.model_name,
      taskTypeValue: attackData.task_type
    });
    console.log('🌐 请求URL:', this.api.defaults.baseURL + '/api/attack/start');
    console.log('🔗 完整请求URL:', `${this.api.defaults.baseURL}/api/attack/start`);
    console.log('📦 发送的JSON字符串:', JSON.stringify(attackData));

    try {
      console.log('📡 发送HTTP请求...');
      const response = await this.api.post('/api/attack/start', attackData, {
        timeout: 30000 // 30秒足够创建任务
      });
      console.log('✅ 前端API响应成功');
      console.log('📥 响应数据:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('❌ 前端API调用失败:', error);
      console.error('🔍 详细错误信息:', {
        message: error.message,
        name: error.name,
        code: error.code,
        status: error.response?.status,
        statusText: error.response?.statusText,
        responseData: error.response?.data,
        requestData: error.config?.data,
        requestHeaders: error.config?.headers
      });

      // 检查是否是网络错误
      if (error.code === 'ECONNREFUSED') {
        console.error('🔌 网络连接被拒绝 - 后端服务器可能没有启动');
      } else if (error.code === 'ENOTFOUND') {
        console.error('🌐 DNS解析失败 - 检查网络连接');
      } else if (error.response) {
        console.error('📡 服务器响应错误 - 检查请求数据格式');
        console.error('📋 服务器返回的错误详情:', error.response.data);
      } else if (error.request) {
        console.error('📡 请求发送失败 - 网络问题');
      }

      throw error;
    }
  }

  async getSupportedAttackMethods() {
    try {
      console.log('📡 获取攻击方法列表...');
      const response = await this.api.get('/api/attack/methods');
      console.log('✅ 攻击方法列表获取成功:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('❌ 获取攻击方法列表失败:', error.message);
      return { success: false, methods: [] };
    }
  }

  // 评估API（新的异步版本）
  async startEvaluation(evaluationData: any) {
    const response = await this.api.post('/api/evaluation/start', evaluationData, {
      timeout: 30000
    });
    return response.data;
  }

  // 微调API（新的异步版本）
  async startFinetuning(finetuningData: any) {
    const response = await this.api.post('/api/finetuning/start', finetuningData, {
      timeout: 30000
    });
    return response.data;
  }

  // 兼容性API（保留旧接口）
  async getAttackStatus(taskId: string) {
    return this.getTask(taskId);
  }

  async getAttackResults(taskId: string) {
    return this.getTask(taskId);
  }

  async getEvaluationStatus(taskId: string) {
    try {
      const response = await this.api.get(`/api/evaluation/status/${taskId}`);
      return response.data;
    } catch (error: any) {
      // 如果是404错误，返回任务不存在的标识
      if (error.response && error.response.status === 404) {
        return {
          success: false,
          error: '任务不存在',
          isTaskNotFound: true
        };
      }
      throw error;
    }
  }

  async getFinetuningStatus(taskId: string) {
    try {
      const response = await this.api.get(`/api/finetuning/status/${taskId}`);
      return response.data;
    } catch (error: any) {
      // 如果是404错误，返回任务不存在的标识
      if (error.response && error.response.status === 404) {
        return {
          success: false,
          error: '任务不存在',
          isTaskNotFound: true
        };
      }
      throw error;
    }
  }

  // 评估报告API
  async getEvaluationReports() {
    const response = await this.api.get('/api/evaluation/reports');
    return response.data;
  }

  async getEvaluationReport(reportId: string) {
    const response = await this.api.get(`/api/evaluation/reports/${reportId}`);
    return response.data;
  }

  // 安全测试结果API（详细数据）
  async getEvaluationResults(taskId: string) {
    const response = await this.api.get(`/api/evaluation/results/${taskId}`);
    return response.data;
  }

  // 对抗性微调API
  async getFinetuningResults(taskId: string) {
    const response = await this.api.get(`/api/finetuning/results/${taskId}`);
    return response.data;
  }

  async downloadModel(modelId: string) {
    const response = await this.api.get(`/api/models/${modelId}/download`, {
      responseType: 'blob'
    });
    return response.data;
  }

  // 批量测试API
  async startBatchTesting(batchData: any) {
    const response = await this.api.post('/api/batch-testing/start', batchData);
    return response.data;
  }

  async getBatchTestingStatus(taskId: string) {
    try {
      const response = await this.api.get(`/api/batch-testing/status/${taskId}`);
      return response.data;
    } catch (error: any) {
      // 如果是404错误，返回任务不存在的标识
      if (error.response && error.response.status === 404) {
        return {
          success: false,
          error: '任务不存在',
          isTaskNotFound: true
        };
      }
      throw error;
    }
  }

  // 批量测试结果API
  async getBatchTestingResults(taskId: string) {
    const response = await this.api.get(`/api/batch-testing/results/${taskId}`);
    return response.data;
  }

  // 数据/模型上传API（支持元数据）
  async uploadFile(
    file: File,
    options?: {
      fileType?: 'model' | 'dataset';
      taskType?: 'clone_detection' | 'vulnerability_detection' | 'code_summarization' | 'code_generation';
      purpose?: 'attack' | 'evaluation' | 'finetuning' | 'batch_testing';
      modelName?: string; // 若为模型文件可附带
      modelType?: string; // 若为模型文件可附带
      datasetName?: string; // 若为数据集可附带
    }
  ) {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.fileType) formData.append('file_type', options.fileType);
    if (options?.taskType) formData.append('task_type', options.taskType);
    if (options?.purpose) formData.append('purpose', options.purpose);
    if (options?.modelName) formData.append('model_name', options.modelName);
    if (options?.modelType) formData.append('model_type', options.modelType);
    if (options?.datasetName) formData.append('dataset_name', options.datasetName);
    
    const response = await this.api.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  // 任务状态API
  async getTaskStatus(taskId: string) {
    const response = await this.api.get(`/api/tasks/status/${taskId}`);
    return response.data;
  }

  async getAllTasks() {
    const response = await this.api.get('/api/tasks');
    return response.data;
  }

  // 健康检查API
  async healthCheck() {
    const response = await this.api.get('/api/health');
    return response.data;
  }

  // 模型下载API
  async downloadModelFile(modelPath: string, fileName: string) {
    const response = await this.api.get(`/api/models/download`, {
      params: { path: modelPath },
      responseType: 'blob'
    });

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    return { success: true };
  }

  // ===== 管理功能API =====

  // 系统统计
  async getSystemStats(): Promise<{
    success: boolean;
    stats?: any;
    message?: string;
  }> {
    try {
      const response = await this.api.get('/admin/stats');
      return {
        success: true,
        stats: response.data.stats
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '获取系统统计失败'
      };
    }
  }

  // 模型管理
  async getAllModels(params?: any): Promise<{
    success: boolean;
    models?: any[];
    total?: number;
    message?: string;
  }> {
    try {
      const response = await this.api.get('/admin/models', { params });
      return {
        success: true,
        models: response.data.models,
        total: response.data.total
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '获取模型列表失败'
      };
    }
  }

  async createModel(modelData: any): Promise<{
    success: boolean;
    model?: any;
    message?: string;
  }> {
    try {
      const response = await this.api.post('/admin/models', modelData);
      return {
        success: true,
        model: response.data.model
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '创建模型失败'
      };
    }
  }

  async updateModel(modelId: number, modelData: any): Promise<{
    success: boolean;
    model?: any;
    message?: string;
  }> {
    try {
      const response = await this.api.put(`/admin/models/${modelId}`, modelData);
      return {
        success: true,
        model: response.data.model
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '更新模型失败'
      };
    }
  }

  async deleteModelAdmin(modelId: number): Promise<{
    success: boolean;
    message?: string;
  }> {
    try {
      await this.api.delete(`/admin/models/${modelId}`);
      return {
        success: true
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '删除模型失败'
      };
    }
  }

  // 攻击方法管理
  async getAttackMethods(): Promise<{
    success: boolean;
    attack_methods?: any[];
    total?: number;
    message?: string;
  }> {
    try {
      const response = await this.api.get('/admin/attack-methods');
      return {
        success: true,
        attack_methods: response.data.attack_methods,
        total: response.data.total
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '获取攻击方法列表失败'
      };
    }
  }

  async getAttackMethodDetails(methodName: string): Promise<{
    success: boolean;
    attack_method?: any;
    message?: string;
  }> {
    try {
      const response = await this.api.get(`/admin/attack-methods/${methodName}`);
      return {
        success: true,
        attack_method: response.data.attack_method
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '获取攻击方法详情失败'
      };
    }
  }

  // ===== 数据集管理API =====

  async getAllDatasets(params?: any): Promise<{
    success: boolean;
    datasets?: any[];
    total?: number;
    message?: string;
  }> {
    try {
      const response = await this.api.get('/admin/datasets', { params });
      return {
        success: true,
        datasets: response.data.datasets,
        total: response.data.total
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '获取数据集列表失败'
      };
    }
  }

  async createDataset(datasetData: any): Promise<{
    success: boolean;
    dataset?: any;
    message?: string;
  }> {
    try {
      const response = await this.api.post('/admin/datasets', datasetData);
      return {
        success: true,
        dataset: response.data.dataset
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '创建数据集失败'
      };
    }
  }

  async updateDataset(datasetId: number, datasetData: any): Promise<{
    success: boolean;
    dataset?: any;
    message?: string;
  }> {
    try {
      const response = await this.api.put(`/admin/datasets/${datasetId}`, datasetData);
      return {
        success: true,
        dataset: response.data.dataset
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '更新数据集失败'
      };
    }
  }

  async deleteDataset(datasetId: number): Promise<{
    success: boolean;
    message?: string;
  }> {
    try {
      await this.api.delete(`/admin/datasets/${datasetId}`);
      return {
        success: true
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || '删除数据集失败'
      };
    }
  }

  // ===== 模型测试API =====

  async testModel(modelId: number, testData: any): Promise<{
    success: boolean;
    result?: any;
    error?: string;
  }> {
    try {
      const response = await this.api.post(`/api/models/${modelId}/test`, testData);
      return {
        success: true,
        result: response.data
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.error || '模型测试失败'
      };
    }
  }
}

// 创建API服务实例
const apiService = new ApiService();

// 导出服务实例
export { apiService };

// 导出各个API模块
export const authAPI = {
  login: (username: string, password: string) => apiService.login(username, password),
  register: (userData: any) => apiService.register(userData),
  getCurrentUser: () => apiService.getCurrentUser(),
};

export const userAPI = {
  getAllUsers: () => apiService.getAllUsers(),
  createUser: (userData: any) => apiService.createUser(userData),
  updateUser: (userId: number, userData: any) => apiService.updateUser(userId, userData),
  deleteUser: (userId: number) => apiService.deleteUser(userId),
  resetUserPassword: (userId: number) => apiService.resetUserPassword(userId),
};

export const adminAPI = {
  // 系统统计
  getSystemStats: () => apiService.getSystemStats(),

  // 模型管理
  getAllModels: (params?: any) => apiService.getAllModels(params),
  createModel: (modelData: any) => apiService.createModel(modelData),
  updateModel: (modelId: number, modelData: any) => apiService.updateModel(modelId, modelData),
  deleteModel: (modelId: number) => apiService.deleteModelAdmin(modelId),

  // 数据集管理
  getAllDatasets: (params?: any) => apiService.getAllDatasets(params),
  createDataset: (datasetData: any) => apiService.createDataset(datasetData),
  updateDataset: (datasetId: number, datasetData: any) => apiService.updateDataset(datasetId, datasetData),
  deleteDataset: (datasetId: number) => apiService.deleteDataset(datasetId),

  // 攻击方法管理
  getAttackMethods: () => apiService.getAttackMethods(),
  getAttackMethodDetails: (methodName: string) => apiService.getAttackMethodDetails(methodName),

  // 模型测试
  testModel: (modelId: number, testData: any) => apiService.testModel(modelId, testData),
};

export const taskAPI = {
  getAllTasks: () => apiService.getAllTasks(),
  getTask: (taskId: string) => apiService.getTask(taskId),
  getTasks: (params?: any) => apiService.getTasks(params),
  getTaskStatistics: (days?: number) => apiService.getTaskStatistics(days),
  cancelTask: (taskId: string, reason?: string) => apiService.cancelTask(taskId, reason),
};

export const modelAPI = {
  getModels: () => apiService.getModels(),
  addModel: (modelData: any) => apiService.addModel(modelData),
};

export default new ApiService();
