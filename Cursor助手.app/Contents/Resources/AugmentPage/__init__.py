"""
AugmentPage - 跨平台IDE管理工具
支持跨平台（Windows、macOS、Linux）

主要功能:
- 智能IDE检测（VSCode系列、JetBrains系列）
- 配置管理（遥测ID、工作区、数据库）
- 自动化工具（邮箱验证码、浏览器管理、自动登录）
- 重置工具（完全重置、手动重置）
- 跨平台支持（Windows、macOS、Linux）

-QW
"""

from .adapter import (
    AugmentPageAdapter,
    get_adapter,
    detect_system_ides,
    cleanup_ide_data,
    test_augment_modules,
    generate_new_device_codes,
    get_ide_path_info,
    modify_ide_telemetry,
    clean_ide_workspace,
    get_system_information
)

from .api.core import AugmentPageAPI

from .utils.ide_detector import detect_ides, IDEDetector
from .utils.device_codes import generate_telemetry_ids, generate_machine_id, generate_device_id
from .utils.paths import (
    get_home_dir,
    get_app_data_dir,
    get_storage_path,
    get_db_path,
    get_machine_id_path,
    get_workspace_storage_path
)

from .config_manager import ConfigManager, get_config_manager, get_config, set_config
from .ui_integration import UIIntegrationManager, get_ui_manager

# 版本信息 -QW
__version__ = "2.0.0"
__author__ = "QW"
__description__ = "跨平台IDE管理工具"

# 导出的主要接口 -QW
__all__ = [
    # 适配器接口
    "AugmentPageAdapter",
    "get_adapter",

    # 便捷函数
    "detect_system_ides",
    "cleanup_ide_data",
    "test_augment_modules",
    "generate_new_device_codes",
    "get_ide_path_info",
    "modify_ide_telemetry",
    "clean_ide_workspace",
    "get_system_information",

    # 核心API
    "AugmentPageAPI",

    # 工具函数
    "detect_ides",
    "IDEDetector",
    "generate_telemetry_ids",
    "generate_machine_id",
    "generate_device_id",
    "get_home_dir",
    "get_app_data_dir",
    "get_storage_path",
    "get_db_path",
    "get_machine_id_path",
    "get_workspace_storage_path",

    # 配置管理
    "ConfigManager",
    "get_config_manager",
    "get_config",
    "set_config",

    # UI集成
    "UIIntegrationManager",
    "get_ui_manager",
]
