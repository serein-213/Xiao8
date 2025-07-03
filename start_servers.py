#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xiao8 启动脚本
同时启动主服务器和memory server
"""

import subprocess
import sys
import time
import os
from multiprocessing import Process

def start_memory_server():
    """启动memory server"""
    print("正在启动 Memory Server...")
    subprocess.run([sys.executable, "memory_server.py"])

def start_main_server():
    """启动主服务器"""
    print("正在启动 Main Server...")
    subprocess.run([sys.executable, "main_server.py"])

def main():
    print("=== Xiao8 启动脚本 ===")
    print("这个脚本将同时启动主服务器和memory server")
    print()
    
    # 检查配置文件
    try:
        from config import MAIN_SERVER_PORT, MEMORY_SERVER_PORT
        print(f"主服务器端口: {MAIN_SERVER_PORT}")
        print(f"Memory服务器端口: {MEMORY_SERVER_PORT}")
        print()
    except ImportError as e:
        print(f"❌ 配置文件错误: {e}")
        print("请确保config文件夹中有正确的配置文件")
        return
    
    try:
        # 启动memory server进程
        memory_process = Process(target=start_memory_server)
        memory_process.start()
        
        # 等待一会让memory server启动
        print("等待Memory Server启动...")
        time.sleep(2)
        
        # 启动主服务器
        print("启动Main Server...")
        start_main_server()
        
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        if 'memory_process' in locals():
            memory_process.terminate()
            memory_process.join()
        print("所有服务器已关闭")
    except Exception as e:
        print(f"❌ 启动错误: {e}")
        if 'memory_process' in locals():
            memory_process.terminate()
            memory_process.join()

if __name__ == "__main__":
    main() 