"""
AugmentPage API模块
支持跨平台（Windows、macOS、Linux）
-QW
"""

from .core import AugmentPageAPI
from .handlers import (
    modify_telemetry_ids,
    clean_augment_data,
    clean_workspace_storage,
    modify_jetbrains_ids,
    get_jetbrains_config_dir,
    get_jetbrains_info
)

__all__ = [
    "AugmentPageAPI",           # 核心API类
    "modify_telemetry_ids",     # 修改遥测ID
    "clean_augment_data",       # 清理Augment数据
    "clean_workspace_storage",  # 清理工作区存储
    "modify_jetbrains_ids",     # 修改JetBrains ID
    "get_jetbrains_config_dir", # 获取JetBrains配置目录
    "get_jetbrains_info"        # 获取JetBrains信息
]
