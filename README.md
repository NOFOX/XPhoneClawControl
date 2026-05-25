# XPhoneClawControl

手机群控系统，支持传统的手机群控，支持 Claw Agent 集群操作。基于 scrcpy 实现 Android 设备画面实时投屏和群控管理。

## 功能特性

- **8x3 固定网格布局**：最多支持 24 台设备同时显示
- **实时画面投屏**：基于 scrcpy 的低延迟视频流传输
- **设备管理**：自动检测连接设备，支持手动刷新
- **批量控制**：截图、录屏、键鼠输入、屏幕旋转
- **响应式设计**：自适应不同屏幕尺寸
- **模拟模式**：无真实设备时可演示系统功能

## 系统要求

### 必需依赖

1. **Python 3.8+**
2. **ADB (Android Debug Bridge)** - 用于与 Android 设备通信
3. **scrcpy** - 开源 Android 投屏工具

### 安装依赖

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install adb scrcpy python3-pip
pip3 install flask flask-socketio eventlet
```

#### macOS

```bash
brew install adb scrcpy
pip3 install flask flask-socketio eventlet
```

## 快速开始

### 1. 启动服务

```bash
cd /workspace
python3 app.py
```

### 2. 访问界面

打开浏览器访问：http://localhost:5000

## 技术栈

- **后端**：Python 3, Flask, Flask-SocketIO
- **前端**：HTML5, CSS3, JavaScript, Socket.IO
- **投屏核心**：scrcpy, ADB
