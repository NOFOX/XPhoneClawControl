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

## 使用演示模式

如果您没有真实的 Android 设备或尚未安装 ADB/scrcpy，系统会自动进入**演示模式**。在演示模式下：

- 系统会模拟显示 24 台虚拟设备
- 所有控制功能（截图、录屏、按键等）都会模拟响应
- 适合体验界面功能和测试系统交互

**手动触发演示模式：**
只需确保没有连接任何真实设备且未安装 ADB，系统启动时会自动检测并进入演示模式。您也可以在启动时设置环境变量强制启用：

```bash
# Linux/macOS
export DEMO_MODE=true
python3 app.py

# Windows (PowerShell)
$env:DEMO_MODE="true"
python app.py
```

## Windows 部署方法

### 1. 安装必需依赖

#### 安装 Python
1. 访问 [Python 官网](https://www.python.org/downloads/) 下载 Python 3.8+
2. 运行安装程序，**务必勾选 "Add Python to PATH"**
3. 验证安装：`python --version`

#### 安装 ADB 和 scrcpy

**方法一：使用 Chocolatey 包管理器（推荐）**
```powershell
# 安装 Chocolatey（如未安装）
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安装 ADB 和 scrcpy
choco install adb scrcpy -y
```

**方法二：手动下载安装**
1. **ADB**: 下载 [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)，解压后将路径添加到系统环境变量 PATH
2. **scrcpy**: 从 [GitHub Releases](https://github.com/Genymobile/scrcpy/releases) 下载最新版，解压后将路径添加到系统环境变量 PATH

### 2. 安装 Python 依赖

打开 PowerShell 或命令提示符（管理员权限）：

```powershell
pip install flask flask-socketio eventlet
```

### 3. 配置 USB 调试

1. 在 Android 设备上启用**开发者选项**（连续点击"版本号"7次）
2. 进入开发者选项，启用**USB 调试**
3. 通过 USB 连接设备到电脑
4. 首次连接时，设备上会弹出授权提示，点击**允许**

### 4. 启动服务

```powershell
cd XPhoneClawControl
python app.py
```

### 5. 访问界面

打开浏览器访问：http://localhost:5000

### 常见问题

**问题：无法识别设备**
- 确保已安装正确的 USB 驱动程序
- 检查 USB 线是否支持数据传输
- 运行 `adb devices` 查看设备列表
- 重启 ADB 服务：`adb kill-server && adb start-server`

**问题：scrcpy 无法启动**
- 确认 scrcpy 已正确添加到 PATH
- 运行 `scrcpy --version` 验证安装
- 确保设备已通过 USB 调试授权

**问题：端口被占用**
- 修改 `app.py` 中的端口号（默认 5000）
- 或关闭占用 5000 端口的其他程序

## 技术栈

- **后端**：Python 3, Flask, Flask-SocketIO
- **前端**：HTML5, CSS3, JavaScript, Socket.IO
- **投屏核心**：scrcpy, ADB
