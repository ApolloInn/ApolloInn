"""
AugmentPage API处理器模块

此模块包含不同操作的独立处理器:
- telemetry: 遥测ID修改
- database: SQLite数据库清理
- workspace: 工作区存储清理
- jetbrains: JetBrains IDE处理
"""

from .telemetry import modify_telemetry_ids
from .database import clean_augment_data
from .workspace import clean_workspace_storage
from .jetbrains import modify_jetbrains_ids, get_jetbrains_config_dir, get_jetbrains_info

__all__ = [
    "modify_telemetry_ids",     # 修改遥测ID
    "clean_augment_data",       # 清理Augment数据
    "clean_workspace_storage",  # 清理工作区存储
    "modify_jetbrains_ids",     # 修改JetBrains ID
    "get_jetbrains_config_dir", # 获取JetBrains配置目录
    "get_jetbrains_info"        # 获取JetBrains信息
]
