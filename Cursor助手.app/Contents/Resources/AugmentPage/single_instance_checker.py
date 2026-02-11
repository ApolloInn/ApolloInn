#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单实例检查模块
用于检查程序是否已有实例在运行，支持跨平台（Windows、macOS、Linux）
-QW
"""

import os
import sys
import platform
import tempfile
import time
import json
from pathlib import Path


def check_single_instance():
    """
    跨平台单实例检查方法
    支持 Windows 和 macOS 系统
    返回锁对象用于保持单实例状态，程序结束时自动释放
    -QW
    """
    system = platform.system().lower()
    print(f"[单实例检查] 系统类型: {system}")  # 添加系统检测日志 -QW

    if system == "windows":
        print("[单实例检查] Windows")  # 添加方式选择日志 -QW
        return _check_single_instance_windows()
    elif system == "darwin":  # macOS
        print("[单实例检查] Mac")  # 添加方式选择日志 -QW
        return _check_single_instance_macos()
    else:  # Linux 或其他系统
        print("[单实例检查] Linux")  # 添加方式选择日志 -QW
        return _check_single_instance_unix()


def _check_single_instance_windows():
    """Windows 系统的单实例检查（使用命名互斥锁） -QW"""
    import ctypes
    from ctypes import wintypes

    # 创建唯一的互斥锁名称 -QW
    mutex_name = "Global\\CursorLoginAssistant_Mutex_2024_v1"

    kernel32 = ctypes.windll.kernel32

    # 尝试创建互斥锁 -QW
    mutex_handle = kernel32.CreateMutexW(
        None,  # 安全属性
        True,  # 初始拥有者
        mutex_name  # 互斥锁名称
    )

    if not mutex_handle:
        print("创建互斥锁失败")  # 调试信息 -QW
        return None

    # 检查是否已存在 -QW
    last_error = kernel32.GetLastError()
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        # 已有实例在运行 -QW
        kernel32.CloseHandle(mutex_handle)

        if _show_duplicate_instance_dialog():
            # 用户选择强制启动，尝试再次创建互斥锁 -QW
            mutex_handle = kernel32.CreateMutexW(None, True, mutex_name)
        else:
            sys.exit(0)

    # 返回互斥锁句柄包装器 -QW
    return WindowsMutexLock(mutex_handle)


def _check_single_instance_macos():
    """macOS 系统的单实例检查（使用文件锁） -QW"""
    import fcntl

    # 获取应用程序专用的锁文件路径 -QW
    lock_file_path = _get_lock_file_path()

    try:
        # 尝试打开并锁定文件 -QW
        lock_file = open(lock_file_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        # 写入当前进程信息 -QW
        process_info = {
            'pid': os.getpid(),
            'start_time': time.time(),
            'executable': sys.executable,
            'argv': sys.argv
        }
        lock_file.write(json.dumps(process_info, indent=2))
        lock_file.flush()

        # 返回文件锁包装器 -QW
        return MacOSFileLock(lock_file, lock_file_path)

    except (IOError, OSError):
        # 文件已被锁定，说明有其他实例在运行 -QW
        if 'lock_file' in locals():
            lock_file.close()

        # 尝试读取现有实例信息 -QW
        existing_info = _read_existing_instance_info(lock_file_path)

        if _show_duplicate_instance_dialog(existing_info):
            # 用户选择强制启动，强制删除锁文件 -QW
            try:
                os.remove(lock_file_path)
                return _check_single_instance_macos()  # 递归重试 -QW
            except:
                pass
        else:
            sys.exit(0)

    return None


def _check_single_instance_unix():
    """Linux/Unix 系统的单实例检查（使用文件锁） -QW"""
    # 与 macOS 使用相同的方法 -QW
    return _check_single_instance_macos()


def _get_lock_file_path():
    """获取锁文件路径 -QW"""
    system = platform.system().lower()

    if system == "windows":
        # Windows: 使用 APPDATA -QW
        app_data = os.getenv('APPDATA')
        if app_data:
            lock_dir = os.path.join(app_data, 'CursorLoginAssistant')
        else:
            lock_dir = tempfile.gettempdir()
    elif system == "darwin":
        # macOS: 使用 ~/Library/Application Support -QW
        home = Path.home()
        lock_dir = home / "Library" / "Application Support" / "CursorLoginAssistant"
    else:
        # Linux: 使用 ~/.local/share -QW
        home = Path.home()
        lock_dir = home / ".local" / "share" / "CursorLoginAssistant"

    # 确保目录存在 -QW
    try:
        os.makedirs(lock_dir, exist_ok=True)
    except:
        lock_dir = tempfile.gettempdir()

    return os.path.join(lock_dir, 'cursor_assistant.lock')


def _read_existing_instance_info(lock_file_path):
    """读取现有实例信息 -QW"""
    try:
        with open(lock_file_path, 'r') as f:
            return json.loads(f.read())
    except:
        return None


def _show_duplicate_instance_dialog(existing_info=None):
    """显示重复实例对话框 -QW"""
    system = platform.system().lower()

    # 构建消息文本 -QW
    message = "检测到Cursor登录助手已经在运行中。\n\n"

    if existing_info:
        message += f"现有实例信息:\n"
        message += f"进程ID: {existing_info.get('pid', '未知')}\n"
        if existing_info.get('start_time'):
            start_time = time.ctime(existing_info['start_time'])
            message += f"启动时间: {start_time}\n"

    message += "\n点击'确定'强制启动，点击'取消'退出程序。"

    if system == "windows":
        # Windows: 使用系统API -QW
        import ctypes
        result = ctypes.windll.user32.MessageBoxW(
            0,
            message,
            "Cursor登录助手",
            0x31  # MB_OKCANCEL | MB_ICONWARNING
        )
        return result == 1  # IDOK

    elif system == "darwin":
        # macOS: 使用 osascript -QW
        import subprocess
        try:
            # 转义消息中的特殊字符 -QW
            escaped_message = message.replace('"', '\\"').replace('\n', '\\n')

            script = f'''
            tell application "System Events"
                set response to display dialog "{escaped_message}" ¬
                    with title "Cursor登录助手" ¬
                    with icon caution ¬
                    buttons {{"取消", "确定"}} ¬
                    default button "取消"
                return button returned of response
            end tell
            '''

            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=30
            )

            return result.stdout.strip() == "确定"
        except:
            # 如果 osascript 失败，默认允许启动 -QW
            print("无法显示对话框，默认允许启动")
            return True

    else:
        # Linux: 尝试使用 zenity 或 kdialog，失败则使用控制台 -QW
        import subprocess

        try:
            # 尝试 zenity -QW
            result = subprocess.run([
                'zenity', '--question',
                '--title=Cursor登录助手',
                '--text=' + message.replace('\n\n', '\n'),
                '--ok-label=确定',
                '--cancel-label=取消'
            ], timeout=30)
            return result.returncode == 0
        except:
            try:
                # 尝试 kdialog -QW
                result = subprocess.run([
                    'kdialog', '--yesno', message,
                    '--title', 'Cursor登录助手'
                ], timeout=30)
                return result.returncode == 0
            except:
                # 使用控制台输入 -QW
                print(message)
                response = input("输入 'y' 强制启动，其他任意键退出: ").lower()
                return response == 'y'


class WindowsMutexLock:
    """Windows 互斥锁包装器 -QW"""

    def __init__(self, mutex_handle):
        self.mutex_handle = mutex_handle
        # 在初始化时保存 CloseHandle 函数的引用，避免程序退出时被垃圾回收 -QW
        import ctypes
        self._close_handle = ctypes.windll.kernel32.CloseHandle

    def __del__(self):
        """析构函数，自动释放互斥锁 -QW"""
        try:
            # 检查互斥锁句柄和关闭函数是否有效 -QW
            if (hasattr(self, 'mutex_handle') and
                    self.mutex_handle and
                    hasattr(self, '_close_handle') and
                    self._close_handle):
                self._close_handle(self.mutex_handle)
                self.mutex_handle = None  # 防止重复释放 -QW
        except Exception:
            # 忽略析构时的任何异常，避免程序退出时报错 -QW
            pass


class MacOSFileLock:
    """macOS/Linux 文件锁包装器 -QW"""

    def __init__(self, lock_file, lock_file_path):
        self.lock_file = lock_file
        self.lock_file_path = lock_file_path

    def __del__(self):
        """析构函数，自动释放文件锁 -QW"""
        try:
            # 安全地关闭文件和删除锁文件 -QW
            if hasattr(self, 'lock_file') and self.lock_file:
                try:
                    self.lock_file.close()
                except Exception:
                    pass  # 忽略关闭文件时的异常 -QW
                self.lock_file = None

            # 删除锁文件 -QW
            if (hasattr(self, 'lock_file_path') and
                    self.lock_file_path and
                    os.path.exists(self.lock_file_path)):
                try:
                    os.remove(self.lock_file_path)
                except Exception:
                    pass  # 忽略删除文件时的异常 -QW
        except Exception:
            # 忽略析构时的任何异常，避免程序退出时报错 -QW
            pass
