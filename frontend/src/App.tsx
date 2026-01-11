import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from 'antd';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import AuthGuard from './components/AuthGuard';
import Home from './pages/Home';
import Models from './pages/Models';
import Attack from './pages/Attack';
import AttackResult from './pages/AttackResult';
import Evaluation from './pages/Evaluation';
import EvaluationResult from './pages/EvaluationResult';
import Finetuning from './pages/Finetuning';
import FinetuningResult from './pages/FinetuningResult';
import BatchTesting from './pages/BatchTesting';
import TaskManager from './pages/TaskManager';
import Login from './pages/Login';
import Admin from './pages/Admin';
import './App.css';

const { Content } = Layout;

// 受保护的布局组件
const ProtectedLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Layout style={{ minHeight: '100vh' }}>
    <Sidebar />
    <Layout>
      <Header />
      <Content style={{ margin: '24px 16px', padding: 24, background: '#fff', minHeight: 280 }}>
        {children}
      </Content>
    </Layout>
  </Layout>
);

const App: React.FC = () => {
  return (
    <Routes>
      {/* 公开路由 */}
      <Route path="/login" element={<Login />} />

      {/* 受保护的主应用路由 */}
      <Route path="/" element={
        <AuthGuard>
          <ProtectedLayout>
            <Home />
          </ProtectedLayout>
        </AuthGuard>
      } />

      <Route path="/models" element={
        <AuthGuard>
          <ProtectedLayout>
            <Models />
          </ProtectedLayout>
        </AuthGuard>
      } />

      <Route path="/attack" element={
        <AuthGuard>
          <ProtectedLayout>
            <Attack />
          </ProtectedLayout>
        </AuthGuard>
      } />

      <Route path="/attack/result" element={
        <AuthGuard>
          <ProtectedLayout>
            <AttackResult />
          </ProtectedLayout>
        </AuthGuard>
      } />

      <Route path="/evaluation" element={
        <AuthGuard>
          <ProtectedLayout>
            <Evaluation />
          </ProtectedLayout>
        </AuthGuard>
      } />

      <Route path="/evaluation/result" element={
        <AuthGuard>
          <ProtectedLayout>
            <EvaluationResult />
          </ProtectedLayout>
        </AuthGuard>
      } />

      <Route path="/finetuning" element={
        <AuthGuard>
          <ProtectedLayout>
            <Finetuning />
          </ProtectedLayout>
        </AuthGuard>
      } />

      <Route path="/finetuning/result" element={
        <AuthGuard>
          <ProtectedLayout>
            <FinetuningResult />
          </ProtectedLayout>
        </AuthGuard>
      } />

      <Route path="/batch-testing" element={
        <AuthGuard>
          <ProtectedLayout>
            <BatchTesting />
          </ProtectedLayout>
        </AuthGuard>
      } />

      <Route path="/tasks" element={
        <AuthGuard>
          <ProtectedLayout>
            <TaskManager />
          </ProtectedLayout>
        </AuthGuard>
      } />

      {/* 管理员专用路由 */}
      <Route path="/admin" element={
        <AuthGuard requireAdmin={true}>
          <Admin />
        </AuthGuard>
      } />

      {/* 默认重定向 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
