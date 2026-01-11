# ITGen - 深度代码模型鲁棒性评估与增强平台

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-18.2.0-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-4.9.0-blue.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📋 项目简介

ITGen是一个基于深度学习的代码模型鲁棒性评估与增强平台，支持多种编程语言的代码克隆检测、漏洞检测和代码摘要生成任务。通过对抗性攻击测试和模型微调，提升代码模型的鲁棒性和安全性。

### 🔗 项目链接

- **GitHub仓库**: [https://github.com/Scndi/ITGen](https://github.com/Scndi/ITGen)
- **文档**: [https://github.com/Scndi/ITGen/blob/main/README.md](https://github.com/Scndi/ITGen/blob/main/README.md)

### ✨ 主要特性

- 🔍 **代码克隆检测**: 支持多种深度学习模型进行代码相似性分析
- 🛡️ **鲁棒性评估**: 基于对抗性攻击的模型安全性测试
- ⚡ **批量攻击测试**: 支持大规模数据集的自动化测试
- 📊 **性能监控**: 实时任务进度跟踪和详细评估报告
- 🔧 **模型微调**: 基于评估结果的模型鲁棒性增强
- 🌐 **Web界面**: 现代化的React前端界面

### 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐
│   React Frontend│    │   Flask Backend │
│   (TypeScript)  │◄──►│   (Python)      │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────────────────┘
                 │
       ┌─────────────────┐
       │   SQLite DB     │
       │ (SQLAlchemy)    │
       └─────────────────┘
```

## 🚀 快速开始

### 📋 系统要求

- **操作系统**: Linux/Windows/macOS
- **Python**: 3.8+
- **Node.js**: 16+
- **内存**: 8GB+ 推荐
- **存储**: 10GB+ 可用空间

### 🔧 环境准备

#### 1. 创建Conda环境

```bash
# 创建名为itgen的conda环境
conda create -n itgen python=3.9 -y
conda activate itgen
```

#### 2. 安装Python依赖

```bash
# 进入项目backend目录
cd ITGen/backend

# 安装Python依赖
pip install -r requirements.txt

# 如果需要GPU支持，根据CUDA版本安装PyTorch
# CUDA 12.1:
pip install torch==2.9.0 torchaudio==2.9.0 torchvision==0.24.0 --index-url https://download.pytorch.org/whl/cu121

# 或者CPU版本:
pip install torch==2.9.0 torchaudio==2.9.0 torchvision==0.24.0 --index-url https://download.pytorch.org/whl/cpu
```

#### 3. 安装Node.js依赖

```bash
# 进入项目frontend目录
cd ../frontend

# 安装前端依赖
npm install
```

### 🏃‍♂️ 启动应用

#### 开发环境启动

1. **启动后端服务**:
```bash
# 在itgen conda环境中
cd ITGen/backend/server
python run.py
```
后端将在 `http://localhost:5000` 启动

2. **启动前端服务**:
```bash
# 打开新的终端窗口
cd ITGen/frontend
npm start
```
前端将在 `http://localhost:3000` 启动

3. **访问应用**:
打开浏览器访问 `http://localhost:3000`

#### 生产环境部署

```bash
# 构建前端
cd ITGen/frontend
npm run build

# 使用Gunicorn启动后端
cd ../backend/server
gunicorn --bind 0.0.0.0:5000 --workers 4 run:app
```

### 🔧 配置说明

#### 后端配置

配置文件位于: `backend/server/app/config.py`

```python
class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///itgen.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 任务调度配置
    SCHEDULER_CHECK_INTERVAL = 5  # 检查间隔(秒)
    TASK_TIMEOUT = 1800  # 任务超时时间(秒)

    # 模型路径配置
    MODEL_DIR = '/path/to/models'
    CHECKPOINT_DIR = '/path/to/checkpoints'
```

#### 前端配置

环境变量文件: `frontend/.env`

```bash
REACT_APP_API_BASE_URL=http://localhost:5000
REACT_APP_WS_URL=http://localhost:5000
```

## 📁 项目结构

```
ITGen/
├── backend/                 # 后端服务
│   ├── server/             # Flask应用
│   │   ├── app/           # 应用核心
│   │   │   ├── api/       # API路由
│   │   │   ├── models/    # 数据模型
│   │   │   ├── services/  # 业务逻辑
│   │   │   └── utils/     # 工具函数
│   │   └── run.py         # 启动脚本
│   ├── algorithms/        # 算法实现
│   ├── checkpoints/       # 模型检查点
│   ├── saved_models/      # 保存的模型
│   └── requirements.txt   # Python依赖
├── frontend/               # 前端应用
│   ├── public/            # 静态资源
│   ├── src/               # 源代码
│   │   ├── components/    # React组件
│   │   ├── pages/         # 页面组件
│   │   ├── services/      # API服务
│   │   └── utils/         # 工具函数
│   ├── package.json       # Node.js依赖
│   └── tsconfig.json      # TypeScript配置
├── docs/                  # 文档
└── README.md             # 项目说明
```

## 🎯 核心功能

### 1. 代码克隆检测
- 支持多种深度学习模型 (CodeBERT, CodeT5, GraphCodeBERT等)
- 批量处理代码对相似性分析
- 可视化相似性评分和结果

### 2. 鲁棒性评估
- 基于对抗性攻击的模型测试
- 支持多种攻击方法 (ITGen, ALERT, MHM, WIR等)
- 实时进度监控和详细报告

### 3. 模型微调
- 基于评估结果的模型增强
- 对抗性训练和鲁棒性优化
- 性能对比和效果验证

### 4. 任务管理
- 异步任务队列管理
- 优先级调度和状态跟踪
- 失败重试和超时处理

## 🔧 API文档

### 主要API端点

#### 评估相关
- `POST /api/evaluation/start` - 开始鲁棒性评估
- `GET /api/evaluation/reports` - 获取评估报告列表
- `GET /api/evaluation/results/{id}` - 获取评估结果

#### 攻击相关
- `POST /api/attack/start` - 开始单次攻击
- `POST /api/batch-testing/start` - 开始批量测试
- `GET /api/attack/status/{id}` - 获取任务状态

#### 微调相关
- `POST /api/finetuning/start` - 开始模型微调
- `GET /api/finetuning/results/{id}` - 获取微调结果

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 项目维护者: ITGen Team
- 邮箱: developer@itgen.com

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

**注意**: 本项目仅用于学术研究和教育目的，请勿用于非法用途。
