"""
AugmentPage 路径工具模块
提供跨平台的路径获取功能
支持跨平台（Windows、macOS、Linux）
-QW
"""

import os
import sys
from pathlib import Path


def get_home_dir() -> str:
    """
    获取用户主目录路径（跨平台） -QW

    Returns:
        str: 用户主目录路径
    """
    return str(Path.home())


def get_app_data_dir() -> str:
    """
    获取应用程序数据目录路径（跨平台） -QW

    Returns:
        str: 应用程序数据目录路径

    平台特定路径:
        - Windows: %APPDATA% (通常是 C:\\Users\\<用户名>\\AppData\\Roaming)
        - macOS: ~/Library/Application Support
        - Linux: ~/.local/share
    """
    if sys.platform == "win32":
        # Windows系统 -QW
        return os.getenv("APPDATA", "")
    elif sys.platform == "darwin":
        # macOS系统 -QW
        return os.path.join(str(Path.home()), "Library", "Application Support")
    else:
        # Linux和其他Unix系统 -QW
        return os.path.join(str(Path.home()), ".local", "share")


def get_storage_path(editor_type: str = "Cursor") -> str:
    """
    获取storage.json文件路径（跨平台） -QW

    Args:
        editor_type (str): 编辑器类型，"Cursor"、"VSCodium" 或 "Code" (VS Code)

    Returns:
        str: storage.json文件路径

    平台特定路径:
        - Windows: %APPDATA%/{editor_type}/User/globalStorage/storage.json
        - macOS: ~/Library/Application Support/{editor_type}/User/globalStorage/storage.json
        - Linux: ~/.config/{editor_type}/User/globalStorage/storage.json
    """
    if sys.platform == "win32":
        # Windows系统 -QW
        base_path = os.getenv("APPDATA", "")
        return os.path.join(base_path, editor_type, "User", "globalStorage", "storage.json")
    elif sys.platform == "darwin":
        # macOS系统 -QW
        return os.path.join(str(Path.home()), "Library", "Application Support", editor_type, "User", "globalStorage", "storage.json")
    else:
        # Linux和其他Unix系统 -QW
        return os.path.join(str(Path.home()), ".config", editor_type, "User", "globalStorage", "storage.json")


def get_db_path(editor_type: str = "Cursor") -> str:
    """
    获取state.vscdb数据库文件路径（跨平台） -QW

    Args:
        editor_type (str): 编辑器类型，"Cursor"、"VSCodium" 或 "Code" (VS Code)

    Returns:
        str: state.vscdb文件路径

    平台特定路径:
        - Windows: %APPDATA%/{editor_type}/User/globalStorage/state.vscdb
        - macOS: ~/Library/Application Support/{editor_type}/User/globalStorage/state.vscdb
        - Linux: ~/.config/{editor_type}/User/globalStorage/state.vscdb
    """
    if sys.platform == "win32":
        # Windows系统 -QW
        base_path = os.getenv("APPDATA", "")
        return os.path.join(base_path, editor_type, "User", "globalStorage", "state.vscdb")
    elif sys.platform == "darwin":
        # macOS系统 -QW
        return os.path.join(str(Path.home()), "Library", "Application Support", editor_type, "User", "globalStorage", "state.vscdb")
    else:
        # Linux和其他Unix系统 -QW
        return os.path.join(str(Path.home()), ".config", editor_type, "User", "globalStorage", "state.vscdb")


def get_machine_id_path(editor_type: str = "Cursor") -> str:
    """
    获取机器ID文件路径（跨平台） -QW

    Args:
        editor_type (str): 编辑器类型，"Cursor"、"VSCodium" 或 "Code" (VS Code)

    Returns:
        str: 机器ID文件路径

    平台特定路径:
        - Windows: %APPDATA%/{editor_type}/machineid
        - macOS: ~/Library/Application Support/{editor_type}/machineid
        - Linux: ~/.config/{editor_type}/machineid
    """
    if sys.platform == "win32":
        # Windows系统 -QW
        base_path = os.getenv("APPDATA", "")
        return os.path.join(base_path, editor_type, "machineid")
    elif sys.platform == "darwin":
        # macOS系统 -QW
        return os.path.join(str(Path.home()), "Library", "Application Support", editor_type, "machineid")
    else:
        # Linux和其他Unix系统 -QW
        return os.path.join(str(Path.home()), ".config", editor_type, "machineid")


def get_workspace_storage_path(editor_type: str = "Cursor") -> str:
    """
    获取工作区存储目录路径（跨平台） -QW

    Args:
        editor_type (str): 编辑器类型，"Cursor"、"VSCodium" 或 "Code" (VS Code)

    Returns:
        str: 工作区存储目录路径

    平台特定路径:
        - Windows: %APPDATA%/{editor_type}/User/workspaceStorage
        - macOS: ~/Library/Application Support/{editor_type}/User/workspaceStorage
        - Linux: ~/.config/{editor_type}/User/workspaceStorage
    """
    if sys.platform == "win32":
        # Windows系统 -QW
        base_path = os.getenv("APPDATA", "")
        return os.path.join(base_path, editor_type, "User", "workspaceStorage")
    elif sys.platform == "darwin":
        # macOS系统 -QW
        return os.path.join(str(Path.home()), "Library", "Application Support", editor_type, "User", "workspaceStorage")
    else:
        # Linux和其他Unix系统 -QW
        return os.path.join(str(Path.home()), ".config", editor_type, "User", "workspaceStorage")


def get_cursor_app_path() -> str:
    """
    获取Cursor应用程序路径（macOS专用） -QW
    
    Returns:
        str: Cursor应用程序路径
    """
    if sys.platform == "darwin":
        return "/Applications/Cursor.app"
    else:
        return ""


def get_cursor_executable_path() -> str:
    """
    获取Cursor可执行文件路径（跨平台） -QW
    
    Returns:
        str: Cursor可执行文件路径
    """
    if sys.platform == "win32":
        # Windows系统 -QW
        localappdata = os.getenv("LOCALAPPDATA", "")
        return os.path.join(localappdata, "Programs", "cursor", "Cursor.exe")
    elif sys.platform == "darwin":
        # macOS系统 -QW
        return "/Applications/Cursor.app/Contents/MacOS/Cursor"
    else:
        # Linux系统 -QW
        return "/usr/bin/cursor"


def get_cursor_workbench_js_path() -> str:
    """
    获取Cursor workbench.desktop.main.js文件路径（跨平台） -QW
    
    Returns:
        str: workbench.desktop.main.js文件路径
    """
    if sys.platform == "win32":
        # Windows系统 -QW
        localappdata = os.getenv("LOCALAPPDATA", "")
        return os.path.join(localappdata, "Programs", "cursor", "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js")
    elif sys.platform == "darwin":
        # macOS系统 -QW
        return "/Applications/Cursor.app/Contents/Resources/app/out/vs/workbench/workbench.desktop.main.js"
    else:
        # Linux系统 -QW
        return "/opt/Cursor/resources/app/out/vs/workbench/workbench.desktop.main.js"


if __name__ == "__main__":
    # 测试路径获取功能 -QW
    print("=== AugmentPage 路径工具测试 ===")
    print(f"系统平台: {sys.platform}")
    print(f"用户主目录: {get_home_dir()}")
    print(f"应用数据目录: {get_app_data_dir()}")
    print(f"Cursor存储路径: {get_storage_path('Cursor')}")
    print(f"Cursor数据库路径: {get_db_path('Cursor')}")
    print(f"Cursor机器ID路径: {get_machine_id_path('Cursor')}")
    print(f"Cursor工作区路径: {get_workspace_storage_path('Cursor')}")
    
    if sys.platform == "darwin":
        print(f"Cursor应用路径: {get_cursor_app_path()}")
    
    print(f"Cursor可执行文件路径: {get_cursor_executable_path()}")
    print(f"Cursor Workbench JS路径: {get_cursor_workbench_js_path()}")
    print("=== 测试完成 ===")
