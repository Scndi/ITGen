import { useEffect, useState } from 'react';
import io, { Socket } from 'socket.io-client';

interface WebSocketHook {
  socket: Socket | null;
  isConnected: boolean;
  lastMessage: MessageEvent | null;
  sendMessage: (message: any) => void;
}

// 从环境变量获取API URL，如果没有则使用默认值
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://192.168.3.115:5000';

export const useWebSocket = (): WebSocketHook => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);

  useEffect(() => {
    console.log('🔌 尝试连接 WebSocket:', API_BASE_URL);
    
    const newSocket = io(API_BASE_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5
    });

    newSocket.on('connect', () => {
      setIsConnected(true);
      console.log('✅ WebSocket连接成功');
    });

    newSocket.on('disconnect', (reason) => {
      setIsConnected(false);
      console.log('🔌 WebSocket连接断开, 原因:', reason);
    });

    newSocket.on('connect_error', (error) => {
      console.error('❌ WebSocket连接错误:', error.message);
    });

    newSocket.on('reconnect_attempt', (attemptNumber) => {
      console.log(`🔄 WebSocket重连尝试 #${attemptNumber}`);
    });

    newSocket.on('reconnect_failed', () => {
      console.error('❌ WebSocket重连失败，已达最大尝试次数');
    });

    newSocket.on('task_update', (data) => {
      console.log('📨 收到任务更新:', data);
      setLastMessage({ data: JSON.stringify(data) } as MessageEvent);
    });

    newSocket.on('connected', (data) => {
      console.log('✅ 服务器确认连接:', data);
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []);

  const sendMessage = (message: any) => {
    if (socket && isConnected) {
      socket.emit('subscribe_task', message);
    }
  };

  return {
    socket,
    isConnected,
    lastMessage,
    sendMessage
  };
};
