"""
AugmentPage 核心API类
支持跨平台（Windows、macOS、Linux）
此模块为AugmentPage操作提供主要的API接口
-QW
"""

import json
import os
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

from .handlers import (
    modify_telemetry_ids,
    clean_augment_data,
    clean_workspace_storage,
    modify_jetbrains_ids,
    get_jetbrains_config_dir,
    get_jetbrains_info
)
from ..utils.paths import (
    get_home_dir,
    get_app_data_dir,
    get_storage_path,
    get_db_path,
    get_machine_id_path,
    get_workspace_storage_path,
)
from ..utils.ide_detector import detect_ides, IDEDetector


class AugmentPageAPI:
    """
    AugmentPage应用程序的主要API类
    支持跨平台（Windows、macOS、Linux）
    此类提供对AugmentCode数据执行各种操作的方法
    -QW
    """

    def __init__(self):
        """初始化API -QW"""
        self.status = "ready"
        self.editor_type = "Cursor"  # 默认编辑器类型改为Cursor -QW
        self.current_ide_info = None  # 存储当前IDE信息 -QW
        print("[AugmentPageAPI] 初始化完成")

    def set_editor_type(self, editor_name: str, ide_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        设置操作的编辑器类型

        Args:
            editor_name (str): 编辑器名称（如 "VSCodium", "Code", "IntelliJ IDEA"）
            ide_info (dict): 可选的IDE检测信息

        Returns:
            dict: 操作结果
        """
        self.editor_type = editor_name
        self.current_ide_info = ide_info

        return {
            "success": True,
            "data": {
                "editor_type": self.editor_type,
                "ide_info": self.current_ide_info
            },
            "message": f"编辑器类型已设置为 {editor_name}"
        }

    def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息和路径

        Returns:
            dict: 包含所有相关路径的系统信息
        """
        try:
            # 确定IDE类型
            ide_type = "vscode"  # 默认值
            if self.current_ide_info:
                ide_type = self.current_ide_info.get("ide_type", "vscode")

            data = {
                "home_dir": get_home_dir(),
                "app_data_dir": get_app_data_dir(),
                "editor_type": self.editor_type,
                "ide_type": ide_type,
            }

            if ide_type == "jetbrains":
                # JetBrains IDE路径
                jetbrains_config = get_jetbrains_config_dir()
                if jetbrains_config:
                    jetbrains_info = get_jetbrains_info(jetbrains_config)
                    data.update({
                        "jetbrains_config_path": jetbrains_config,
                        "jetbrains_info": jetbrains_info,
                    })
            else:
                # VSCode系列路径
                data.update({
                    "storage_path": get_storage_path(self.editor_type),
                    "db_path": get_db_path(self.editor_type),
                    "machine_id_path": get_machine_id_path(self.editor_type),
                    "workspace_storage_path": get_workspace_storage_path(self.editor_type),
                })

            return {
                "success": True,
                "data": data,
                "message": "系统信息获取成功"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "获取系统信息失败"
            }

    def modify_telemetry(self) -> Dict[str, Any]:
        """
        根据IDE类型修改遥测ID

        Returns:
            dict: 包含遥测修改详情的操作结果
        """
        try:
            # 确定IDE类型
            ide_type = "vscode"  # 默认值
            if self.current_ide_info:
                ide_type = self.current_ide_info.get("ide_type", "vscode")

            if ide_type == "jetbrains":
                # 处理JetBrains IDE
                jetbrains_config = get_jetbrains_config_dir()
                if not jetbrains_config:
                    return {
                        "success": False,
                        "error": "JetBrains配置目录未找到",
                        "message": "无法找到JetBrains配置目录"
                    }

                result = modify_jetbrains_ids(jetbrains_config)
                return {
                    "success": result["success"],
                    "data": result.get("data", {}),
                    "message": result.get("message", "JetBrains ID处理完成")
                }
            else:
                # 处理VSCode系列
                result = modify_telemetry_ids(self.editor_type)
                return {
                    "success": True,
                    "data": result,
                    "message": "遥测ID修改成功"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "message": "修改遥测ID失败"
            }

    def clean_database(self) -> Dict[str, Any]:
        """
        从SQLite数据库清理augment数据

        Returns:
            dict: 包含备份信息和删除计数的操作结果
        """
        try:
            result = clean_augment_data(self.editor_type)
            return {
                "success": True,
                "data": result,
                "message": f"数据库清理成功。删除了 {result['deleted_rows']} 行。"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "message": "数据库清理失败"
            }

    def clean_workspace(self) -> Dict[str, Any]:
        """
        清理工作区存储目录

        Returns:
            dict: 包含备份信息和删除计数的操作结果
        """
        try:
            result = clean_workspace_storage(self.editor_type)
            return {
                "success": True,
                "data": result,
                "message": f"工作区清理成功。删除了 {result['deleted_files_count']} 个文件。"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "message": "工作区清理失败"
            }

    def run_all_operations(self) -> Dict[str, Any]:
        """
        根据IDE类型按顺序运行所有清理操作

        Returns:
            dict: 所有操作的综合结果
        """
        # 确定IDE类型
        ide_type = "vscode"  # 默认值
        if self.current_ide_info:
            ide_type = self.current_ide_info.get("ide_type", "vscode")

        results = {
            "telemetry": None,
            "overall_success": True,
            "errors": [],
            "ide_type": ide_type
        }

        # 始终修改遥测ID（对VSCode和JetBrains都有效）
        telemetry_result = self.modify_telemetry()
        results["telemetry"] = telemetry_result
        if not telemetry_result["success"]:
            results["overall_success"] = False
            results["errors"].append(f"遥测: {telemetry_result.get('error', '未知错误')}")

        if ide_type == "vscode":
            # VSCode系列：还需要清理数据库和工作区
            database_result = self.clean_database()
            results["database"] = database_result
            if not database_result["success"]:
                results["overall_success"] = False
                results["errors"].append(f"数据库: {database_result.get('error', '未知错误')}")

            workspace_result = self.clean_workspace()
            results["workspace"] = workspace_result
            if not workspace_result["success"]:
                results["overall_success"] = False
                results["errors"].append(f"工作区: {workspace_result.get('error', '未知错误')}")
        else:
            # JetBrains：只需要修改遥测
            results["database"] = {"success": True, "message": "不适用于JetBrains IDE"}
            results["workspace"] = {"success": True, "message": "不适用于JetBrains IDE"}

        # 设置总体消息
        if results["overall_success"]:
            results["message"] = "所有操作成功完成"
        else:
            error_count = len(results["errors"])
            results["message"] = f"部分操作失败 ({error_count} 个错误)"

        return results

    def detect_ides(self) -> Dict[str, Any]:
        """
        检测系统上安装的所有IDE

        Returns:
            dict: 包含IDE列表和摘要的检测结果
        """
        try:
            result = detect_ides()
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"IDE检测失败: {str(e)}"
            }
