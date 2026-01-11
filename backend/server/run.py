#!/usr/bin/env python
"""
ITGen Flask应用启动文件
"""
import os
from app import create_app
from app.config import Config

# 创建应用实例
app = create_app(Config)

# 从app获取socketio实例
socketio = app.socketio

if __name__ == '__main__':
    # 开发环境配置
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"\n{'='*60}")
    print(f"Flask服务器启动在: http://0.0.0.0:{port}")
    print(f"调试模式: {'开启' if debug else '关闭'}")
    print(f"访问地址: http://localhost:{port}/api/health")
    print(f"{'='*60}\n")
    
    # 使用socketio启动（支持WebSocket）
    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=debug,
            allow_unsafe_werkzeug=True,
            log_output=True
        )
    except Exception as e:
        print(f"\n启动错误: {e}")
        print("请检查端口是否被占用，或尝试更换端口：")
        print("  set PORT=5001")
        print("  python run.py")
