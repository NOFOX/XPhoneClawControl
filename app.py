#!/usr/bin/env python3
"""
XPhoneClawControl - 手机群控系统
基于 scrcpy 的手机群控画面系统，支持最多 24 台设备
8x3 固定网格布局，实时画面传输

注意：本系统需要以下依赖:
- adb (Android Debug Bridge)
- scrcpy (开源 Android 投屏工具)

安装方法 (Ubuntu/Debian):
  sudo apt install adb scrcpy

安装方法 (macOS):
  brew install adb scrcpy
"""

import os
import sys
import json
import subprocess
import threading
import signal
import time
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit

# ===== 配置 =====
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'xphone-claw-control-secret-key-2025'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# 全局设备管理
devices = {}  # {serial: {status, name, process, stream_port}}
device_lock = threading.Lock()

# scrcpy 服务端口范围
SCRCPY_BASE_PORT = 27183

# 模拟模式（无真实设备时自动启用）
SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'false').lower() == 'true'
demo_mode = False  # 运行时动态检测模式


def check_adb_installed():
    """检查 adb 是否已安装"""
    try:
        result = subprocess.run(['adb', 'version'], capture_output=True, text=True, timeout=3)
        return result.returncode == 0
    except Exception:
        return False


def check_scrcpy_installed():
    """检查 scrcpy 是否已安装"""
    try:
        result = subprocess.run(['scrcpy', '--version'], capture_output=True, text=True, timeout=3)
        return result.returncode == 0
    except Exception:
        return False


def get_device_serials():
    """
    通过 adb 获取已连接的设备序列号列表，支持 USB 和无线调试。
    自动检测：无设备时启用模拟模式，有设备时退出模拟模式。
    """
    global demo_mode
    
    # 如果强制模拟模式，直接返回虚拟设备
    if os.environ.get('SIMULATION_MODE', 'false').lower() == 'true':
        return [f'EMULATOR-{i:04d}' for i in range(24)]  # 24 台虚拟设备
    
    try:
        # 多次尝试检测，防止 ADB 服务启动延迟
        result = None
        for attempt in range(3):
            result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                break
            time.sleep(1)
        
        if result is None or result.returncode != 0:
            print(f"⚠️ ADB 命令执行失败")
            # ADB 不可用，进入模拟模式
            if not demo_mode:
                print("ℹ️ 未检测到 ADB，自动进入演示模式")
                demo_mode = True
            return [f'EMULATOR-{i:04d}' for i in range(24)]
        
        lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
        serials = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == 'device':
                serials.append(parts[0])
        
        # 动态调整模式
        if len(serials) > 0:
            if demo_mode:
                print(f"ℹ️ 检测到 {len(serials)} 个真实设备，已退出演示模式")
                demo_mode = False
            return serials
        else:
            if not demo_mode:
                print("ℹ️ 未检测到真实设备，自动进入演示模式")
                demo_mode = True
            # 返回 24 台虚拟设备用于演示
            return [f'EMULATOR-{i:04d}' for i in range(24)]
            
    except FileNotFoundError:
        print("⚠️ ADB 未找到，自动进入演示模式")
        if not demo_mode:
            demo_mode = True
        return [f'EMULATOR-{i:04d}' for i in range(24)]
    except Exception as e:
        print(f"获取设备列表失败：{e}")
        if not demo_mode:
            demo_mode = True
        return [f'EMULATOR-{i:04d}' for i in range(24)]


def get_device_model(serial):
    """获取设备型号名称"""
    # 检查是否为模拟设备
    if serial.startswith('EMULATOR-') or demo_mode:
        # 模拟模式下的虚拟设备名称
        models = ['Pixel-7-Pro', 'Galaxy-S24', 'Xiaomi-14', 'OnePlus-12', 'Honor-Magic6', 'Vivo-X100']
        idx = int(serial.split('-')[1]) % len(models)
        return f"{models[idx]}-{serial[-4:]}"
    
    try:
        result = subprocess.run(
            ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.model'],
            capture_output=True,
            text=True,
            timeout=3
        )
        model = result.stdout.strip()
        if model:
            return model
        return f"Device-{serial[-6:]}"
    except Exception:
        return f"Device-{serial[-6:]}"


def start_scrcpy_stream(serial, port):
    """启动 scrcpy 视频流服务"""
    # 检查是否为模拟设备
    if serial.startswith('EMULATOR-') or demo_mode:
        # 模拟模式下不实际启动 scrcpy
        print(f"[模拟] 启动设备流：{serial} 端口:{port}")
        return None
    
    try:
        # 使用 scrcpy-server 推送到设备并启动
        cmd = [
            'adb', '-s', serial,
            'forward', f'tcp:{port}', 'localabstract:scrcpy'
        ]
        subprocess.run(cmd, capture_output=True, timeout=3)
        
        # 启动 scrcpy 无窗口模式，只推送视频流
        scrcpy_cmd = [
            'scrcpy',
            '-s', serial,
            '--no-window',
            '--bit-rate', '2M',
            '--max-size', '800',
            '--max-fps', '15',
            '--push-target', '/data/local/tmp'
        ]
        
        proc = subprocess.Popen(
            scrcpy_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return proc
    except Exception as e:
        print(f"启动 scrcpy 流失败 ({serial}): {e}")
        return None


def stop_scrcpy_stream(serial):
    """停止设备的 scrcpy 流"""
    with device_lock:
        if serial in devices:
            dev_info = devices[serial]
            if dev_info.get('process'):
                try:
                    dev_info['process'].terminate()
                except Exception:
                    pass
            # 移除 adb forward
            try:
                port = dev_info.get('stream_port')
                if port:
                    subprocess.run(
                        ['adb', '-s', serial, 'forward', '--remove', f'tcp:{port}'],
                        capture_output=True,
                        timeout=2
                    )
            except Exception:
                pass
            del devices[serial]


@socketio.on('connect')
def handle_connect():
    """客户端连接时的处理"""
    print("客户端已连接")
    # 发送当前设备列表
    refresh_devices()


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    print("客户端已断开")


@socketio.on('refresh_devices')
def handle_refresh_devices():
    """手动刷新设备列表"""
    refresh_devices()


@socketio.on('start_device')
def handle_start_device(data):
    """启动指定设备的 scrcpy 流"""
    serial = data.get('serial')
    if not serial:
        emit('error', {'message': '缺少设备序列号'})
        return
    
    with device_lock:
        if serial in devices and devices[serial].get('status') == 'online':
            emit('device_status', {'serial': serial, 'status': 'already_running'})
            return
    
    # 启动 scrcpy 流
    port = SCRCPY_BASE_PORT + list(devices.keys()).index(serial) if serial in devices else SCRCPY_BASE_PORT + len(devices)
    
    try:
        # 检查设备是否在线
        result = subprocess.run(
            ['adb', '-s', serial, 'get-state'],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.stdout.strip() != 'device':
            emit('device_status', {'serial': serial, 'status': 'offline'})
            return
        
        model = get_device_model(serial)
        
        with device_lock:
            devices[serial] = {
                'status': 'online',
                'name': model,
                'stream_port': port,
                'process': None  # scrcpy 进程
            }
        
        emit('device_status', {
            'serial': serial,
            'status': 'online',
            'name': model,
            'port': port
        })
        
        # 广播设备更新
        socketio.emit('devices_updated', get_devices_list())
        
    except Exception as e:
        print(f"启动设备失败 ({serial}): {e}")
        emit('device_status', {'serial': serial, 'status': 'error', 'message': str(e)})


@socketio.on('stop_device')
def handle_stop_device(data):
    """停止指定设备的 scrcpy 流"""
    serial = data.get('serial')
    if not serial:
        emit('error', {'message': '缺少设备序列号'})
        return
    
    stop_scrcpy_stream(serial)
    emit('devices_updated', get_devices_list())


@socketio.on('take_screenshot')
def handle_screenshot(data):
    """截取设备屏幕"""
    serial = data.get('serial')
    if not serial:
        emit('error', {'message': '缺少设备序列号'})
        return
    
    try:
        # 使用 adb 截图
        result = subprocess.run(
            ['adb', '-s', serial, 'shell', 'screencap', '-p', '/sdcard/screenshot.png'],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            # 拉取截图到本地
            filename = f"screenshot_{serial.replace(':', '_')}.png"
            filepath = os.path.join('static', 'screenshots', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            result = subprocess.run(
                ['adb', '-s', serial, 'pull', '/sdcard/screenshot.png', filepath],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                emit('screenshot_taken', {
                    'serial': serial,
                    'path': f'/static/screenshots/{filename}'
                })
                return
        
        emit('error', {'message': f'截图失败：{serial}'})
    except Exception as e:
        emit('error', {'message': f'截图异常：{str(e)}'})


@socketio.on('input_key')
def handle_input_key(data):
    """发送按键输入到设备"""
    serial = data.get('serial')
    keycode = data.get('keycode')
    if not serial or keycode is None:
        emit('error', {'message': '参数不完整'})
        return
    
    try:
        subprocess.run(
            ['adb', '-s', serial, 'shell', 'input', 'keyevent', str(keycode)],
            capture_output=True,
            timeout=3
        )
    except Exception as e:
        emit('error', {'message': f'按键失败：{str(e)}'})


@socketio.on('input_text')
def handle_input_text(data):
    """发送文本输入到设备"""
    serial = data.get('serial')
    text = data.get('text')
    if not serial or not text:
        emit('error', {'message': '参数不完整'})
        return
    
    try:
        # 转义特殊字符
        escaped_text = text.replace(' ', '%s').replace('&', '\\&')
        subprocess.run(
            ['adb', '-s', serial, 'shell', 'input', 'text', escaped_text],
            capture_output=True,
            timeout=3
        )
    except Exception as e:
        emit('error', {'message': f'文本输入失败：{str(e)}'})


@socketio.on('input_touch')
def handle_input_touch(data):
    """发送触摸事件到设备"""
    serial = data.get('serial')
    x = data.get('x')
    y = data.get('y')
    action = data.get('action', 'tap')  # tap, swipe_start, swipe_end
    
    if not serial or x is None or y is None:
        emit('error', {'message': '参数不完整'})
        return
    
    try:
        if action == 'tap':
            subprocess.run(
                ['adb', '-s', serial, 'shell', 'input', 'tap', str(x), str(y)],
                capture_output=True,
                timeout=3
            )
        elif action == 'swipe_start':
            subprocess.run(
                ['adb', '-s', serial, 'shell', 'input', 'swipe', str(x), str(y), str(x), str(y)],
                capture_output=True,
                timeout=3
            )
    except Exception as e:
        emit('error', {'message': f'触摸事件失败：{str(e)}'})


def get_devices_list():
    """获取设备列表（用于前端渲染）"""
    with device_lock:
        return [
            {
                'serial': serial,
                'name': info['name'],
                'status': info['status'],
                'port': info.get('stream_port')
            }
            for serial, info in devices.items()
        ]


def refresh_devices():
    """刷新设备列表并通知客户端"""
    serials = get_device_serials()
    
    with device_lock:
        # 移除已断开的设备
        to_remove = [s for s in devices if s not in serials]
        for serial in to_remove:
            stop_scrcpy_stream(serial)
        
        # 添加新设备
        for serial in serials:
            if serial not in devices:
                model = get_device_model(serial)
                devices[serial] = {
                    'status': 'online',
                    'name': model,
                    'stream_port': None,
                    'process': None
                }
    
    # 发送更新后的设备列表
    socketio.emit('devices_updated', get_devices_list())


# 启动时初始化设备列表
with app.app_context():
    refresh_devices()


@app.route('/')
def index():
    """主页 - 渲染手机墙界面"""
    return render_template('index.html')


@app.route('/api/devices')
def api_devices():
    """API: 获取设备列表"""
    return jsonify(get_devices_list())


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """API: 刷新设备列表"""
    refresh_devices()
    return jsonify({'status': 'ok'})


@app.route('/api/device/<serial>/start', methods=['POST'])
def api_start_device(serial):
    """API: 启动设备流"""
    with device_lock:
        if serial in devices:
            return jsonify({'status': 'already_running'})
    
    port = SCRCPY_BASE_PORT + len(devices)
    model = get_device_model(serial)
    
    with device_lock:
        devices[serial] = {
            'status': 'online',
            'name': model,
            'stream_port': port,
            'process': None
        }
    
    socketio.emit('devices_updated', get_devices_list())
    return jsonify({'status': 'started', 'port': port})


@app.route('/api/device/<serial>/stop', methods=['POST'])
def api_stop_device(serial):
    """API: 停止设备流"""
    stop_scrcpy_stream(serial)
    socketio.emit('devices_updated', get_devices_list())
    return jsonify({'status': 'stopped'})


def periodic_device_check():
    """定期检查设备连接状态"""
    while True:
        import time
        time.sleep(5)
        refresh_devices()


@app.before_request
def before_request():
    """请求前处理"""
    pass


def cleanup_on_exit(signum, frame):
    """程序退出时清理资源"""
    print("\n正在清理 scrcpy 进程...")
    with device_lock:
        for serial in list(devices.keys()):
            stop_scrcpy_stream(serial)
    sys.exit(0)


if __name__ == '__main__':
    # 注册信号处理器
    signal.signal(signal.SIGINT, cleanup_on_exit)
    signal.signal(signal.SIGTERM, cleanup_on_exit)
    
    # 创建必要的目录
    os.makedirs('static/screenshots', exist_ok=True)
    
    # 检查依赖
    adb_installed = check_adb_installed()
    scrcpy_installed = check_scrcpy_installed()
    
    if not adb_installed or not scrcpy_installed:
        print("\n" + "=" * 50)
        print("警告：部分依赖未安装")
        print("=" * 50)
        if not adb_installed:
            print("  - ADB 未安装 (adb)")
        if not scrcpy_installed:
            print("  - Scrcpy 未安装 (scrcpy)")
        print("\n系统将以模拟模式运行，显示虚拟设备。")
        print("\n安装方法:")
        print("  Ubuntu/Debian: sudo apt install adb scrcpy")
        print("  macOS: brew install adb scrcpy")
        print("=" * 50 + "\n")
        
        # 自动启用演示模式
        demo_mode = True
    
    # 启动设备检查线程
    check_thread = threading.Thread(target=periodic_device_check, daemon=True)
    check_thread.start()
    
    print("=" * 50)
    print("XPhoneClawControl - 手机群控系统")
    print("=" * 50)
    if demo_mode:
        print("运行模式：DEMO (演示模式 - 无真实设备)")
    else:
        print("运行模式：PRODUCTION (生产模式 - 有真实设备)")
    print("访问地址：http://localhost:5000")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    
    # 启动 Flask 服务器
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
