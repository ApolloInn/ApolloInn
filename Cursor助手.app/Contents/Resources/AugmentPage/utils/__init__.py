"""
AugmentPage 工具模块
支持跨平台（Windows、macOS、Linux）
-QW
"""

from .paths import (
    get_home_dir,
    get_app_data_dir,
    get_storage_path,
    get_db_path,
    get_machine_id_path,
    get_workspace_storage_path,
)
from .device_codes import generate_machine_id, generate_device_id
from .ide_detector import detect_ides, IDEDetector

__all__ = [
    "get_home_dir",                  # 获取用户主目录
    "get_app_data_dir",              # 获取应用数据目录
    "get_storage_path",              # 获取存储文件路径
    "get_db_path",                   # 获取数据库路径
    "get_machine_id_path",           # 获取机器ID文件路径
    "get_workspace_storage_path",    # 获取工作区存储路径
    "generate_machine_id",           # 生成机器ID
    "generate_device_id",            # 生成设备ID
    "detect_ides",                   # 检测IDE
    "IDEDetector"                    # IDE检测器类
]
