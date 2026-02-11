"""
AugmentPage 适配器模块
为主程序提供简化的接口
支持跨平台（Windows、macOS、Linux）
集成所有AugmentPage功能模块
-QW
"""

import os
import sys
import json
import platform
from typing import Dict, Any, List, Optional
from pathlib import Path


class AugmentPageAdapter:
    """AugmentPage 功能适配器 -QW"""

    def __init__(self):
        self.augment_page_path = None
        self.system = platform.system().lower()
        self._setup_path()
        print(f"[AugmentPage适配器] 初始化完成，系统: {self.system}")
    
    def _setup_path(self):
        """设置AugmentPage模块路径"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.augment_page_path = current_dir
            
            if os.path.exists(self.augment_page_path) and self.augment_page_path not in sys.path:
                sys.path.insert(0, self.augment_page_path)
                print(f"[AugmentPage适配器] ✅ 已添加路径: {self.augment_page_path}")
            else:
                print(f"[AugmentPage适配器] ⚠️ 路径不存在: {self.augment_page_path}")
        except Exception as e:
            print(f"[AugmentPage适配器] ❌ 路径设置失败: {str(e)}")
    
    def detect_ides(self) -> Dict[str, Any]:
        """检测系统中的IDE"""
        try:
            from .utils.ide_detector import detect_ides
            result = detect_ides()

            if result["success"] and result["ides"]:
                print(f"[AugmentPage适配器] ✅ 检测到 {len(result['ides'])} 个IDE")
                return result
            else:
                # 返回默认IDE列表，但标记为检测失败
                print("[AugmentPage适配器] ⚠️ IDE检测返回空结果，使用默认IDE列表")
                default_result = self._get_default_ides()
                default_result["detection_failed"] = True
                default_result["message"] = "IDE检测返回空结果"
                return default_result

        except ImportError as e:
            print(f"[AugmentPage适配器] ❌ 导入错误: {str(e)}")
            default_result = self._get_default_ides()
            default_result["detection_failed"] = True
            default_result["message"] = f"导入错误: {str(e)}"
            return default_result
        except Exception as e:
            print(f"[AugmentPage适配器] ❌ IDE检测失败: {str(e)}")
            default_result = self._get_default_ides()
            default_result["detection_failed"] = True
            default_result["message"] = f"检测失败: {str(e)}"
            return default_result
    
    def _get_default_ides(self) -> Dict[str, Any]:
        """获取默认IDE列表"""
        default_ides = [
            {
                "name": "Cursor",
                "display_name": "Cursor",
                "ide_type": "vscode",
                "config_path": "",
                "icon": "🎯"
            },
            {
                "name": "Code",
                "display_name": "VS Code",
                "ide_type": "vscode",
                "config_path": "",
                "icon": "💙"
            },
            {
                "name": "VSCodium",
                "display_name": "VSCodium",
                "ide_type": "vscode",
                "config_path": "",
                "icon": "🔷"
            }
        ]
        
        return {
            "success": True,
            "ides": default_ides,
            "count": len(default_ides),
            "message": "使用默认IDE列表"
        }

    def execute_cleanup(self, ide_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行清理操作"""
        try:
            from .api.core import AugmentPageAPI

            # 创建API实例
            api = AugmentPageAPI()

            # 设置编辑器类型
            api.set_editor_type(ide_data["name"], ide_data)

            # 执行所有清理操作
            result = api.run_all_operations()

            print(f"[AugmentPage适配器] ✅ 清理操作完成: {result.get('message', '未知结果')}")
            return result

        except ImportError as e:
            print(f"[AugmentPage适配器] ⚠️ 缺少依赖，使用简单清理器")
            return self._use_simple_cleaner(ide_data)
        except Exception as e:
            error_msg = f"清理操作失败: {str(e)}"
            print(f"[AugmentPage适配器] ❌ {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "data": {
                    "editor": ide_data,
                    "operations": {},
                    "errors": [str(e)]
                }
            }

    def _use_simple_cleaner(self, ide_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用简单清理器（降级方案）"""
        try:
            from .simple_cleaner import simple_cleanup_ide
            result = simple_cleanup_ide(ide_data)

            if result["success"]:
                # 统计清理结果
                operations = result.get("data", {}).get("operations", {})
                total_operations = len(operations)
                successful_operations = sum(1 for op in operations.values() if op.get("success", False))

                print(f"[AugmentPage适配器] ✅ 简单清理器完成清理 ({successful_operations}/{total_operations} 项操作成功)")
            else:
                errors = result.get("data", {}).get("errors", [])
                print(f"[AugmentPage适配器] ⚠️ 简单清理器部分失败 (发现 {len(errors)} 个错误)")

            return result

        except Exception as e:
            error_msg = f"简单清理器失败: {str(e)}"
            print(f"[AugmentPage适配器] ❌ {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "data": {
                    "editor": ide_data,
                    "operations": {},
                    "errors": [str(e)]
                }
            }
    
    def test_modules(self) -> Dict[str, bool]:
        """测试各个模块是否可用"""
        modules_status = {}
        
        try:
            # 测试IDE检测模块
            from .utils.ide_detector import detect_ides
            modules_status["ide_detector"] = True
        except Exception as e:
            modules_status["ide_detector"] = False
            print(f"[AugmentPage适配器] IDE检测模块不可用: {str(e)}")
        
        try:
            # 测试核心API模块
            from .api.core import AugmentPageAPI
            modules_status["core_api"] = True
        except Exception as e:
            modules_status["core_api"] = False
            print(f"[AugmentPage适配器] 核心API模块不可用: {str(e)}")
        
        try:
            # 测试处理器模块
            from .api.handlers import modify_telemetry_ids, clean_augment_data, clean_workspace_storage
            modules_status["handlers"] = True
        except Exception as e:
            modules_status["handlers"] = False
            print(f"[AugmentPage适配器] 处理器模块不可用: {str(e)}")
        
        return modules_status

    def generate_device_codes(self) -> Dict[str, Any]:
        """生成设备代码 -QW"""
        try:
            from .utils.device_codes import generate_telemetry_ids
            ids = generate_telemetry_ids()

            print(f"[AugmentPage适配器] ✅ 生成了 {len(ids)} 个设备代码")
            return {
                "success": True,
                "ids": ids,
                "count": len(ids),
                "message": "设备代码生成成功"
            }
        except Exception as e:
            error_msg = f"设备代码生成失败: {str(e)}"
            print(f"[AugmentPage适配器] ❌ {error_msg}")
            return {
                "success": False,
                "ids": {},
                "count": 0,
                "message": error_msg
            }

    def get_ide_paths(self, ide_name: str) -> Dict[str, Any]:
        """获取IDE路径信息 -QW"""
        try:
            from .utils.paths import (
                get_storage_path,
                get_db_path,
                get_machine_id_path,
                get_workspace_storage_path
            )

            paths = {
                "storage_path": get_storage_path(ide_name),
                "db_path": get_db_path(ide_name),
                "machine_id_path": get_machine_id_path(ide_name),
                "workspace_storage_path": get_workspace_storage_path(ide_name)
            }

            # 检查路径是否存在 -QW
            existing_paths = {}
            for key, path in paths.items():
                existing_paths[key] = {
                    "path": path,
                    "exists": os.path.exists(path)
                }

            print(f"[AugmentPage适配器] ✅ 获取 {ide_name} 路径信息成功")
            return {
                "success": True,
                "ide_name": ide_name,
                "paths": existing_paths,
                "message": f"{ide_name} 路径信息获取成功"
            }
        except Exception as e:
            error_msg = f"获取 {ide_name} 路径信息失败: {str(e)}"
            print(f"[AugmentPage适配器] ❌ {error_msg}")
            return {
                "success": False,
                "ide_name": ide_name,
                "paths": {},
                "message": error_msg
            }

    def modify_telemetry_only(self, ide_name: str) -> Dict[str, Any]:
        """仅修改遥测ID -QW"""
        try:
            from .api.handlers.telemetry import modify_telemetry_ids
            result = modify_telemetry_ids(ide_name)

            print(f"[AugmentPage适配器] ✅ {ide_name} 遥测ID修改成功")
            return {
                "success": True,
                "ide_name": ide_name,
                "data": result,
                "message": f"{ide_name} 遥测ID修改成功"
            }
        except Exception as e:
            error_msg = f"{ide_name} 遥测ID修改失败: {str(e)}"
            print(f"[AugmentPage适配器] ❌ {error_msg}")
            return {
                "success": False,
                "ide_name": ide_name,
                "data": {},
                "message": error_msg
            }

    def clean_workspace_only(self, ide_name: str) -> Dict[str, Any]:
        """仅清理工作区存储 -QW"""
        try:
            from .api.handlers.workspace import clean_workspace_storage
            result = clean_workspace_storage(ide_name)

            print(f"[AugmentPage适配器] ✅ {ide_name} 工作区清理成功")
            return {
                "success": True,
                "ide_name": ide_name,
                "data": result,
                "message": f"{ide_name} 工作区清理成功"
            }
        except Exception as e:
            error_msg = f"{ide_name} 工作区清理失败: {str(e)}"
            print(f"[AugmentPage适配器] ❌ {error_msg}")
            return {
                "success": False,
                "ide_name": ide_name,
                "data": {},
                "message": error_msg
            }

    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息 -QW"""
        return {
            "system": platform.system(),
            "platform": platform.platform(),
            "architecture": platform.architecture(),
            "python_version": platform.python_version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }


# 创建全局适配器实例
_adapter_instance = None

def get_adapter() -> AugmentPageAdapter:
    """获取适配器实例（单例模式）"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = AugmentPageAdapter()
    return _adapter_instance


def detect_system_ides() -> Dict[str, Any]:
    """检测系统IDE的便捷函数"""
    adapter = get_adapter()
    return adapter.detect_ides()


def cleanup_ide_data(ide_data: Dict[str, Any]) -> Dict[str, Any]:
    """清理IDE数据的便捷函数"""
    adapter = get_adapter()
    return adapter.execute_cleanup(ide_data)


def test_augment_modules() -> Dict[str, bool]:
    """测试AugmentPage模块的便捷函数 -QW"""
    adapter = get_adapter()
    return adapter.test_modules()


def generate_new_device_codes() -> Dict[str, Any]:
    """生成新设备代码的便捷函数 -QW"""
    adapter = get_adapter()
    return adapter.generate_device_codes()


def get_ide_path_info(ide_name: str) -> Dict[str, Any]:
    """获取IDE路径信息的便捷函数 -QW"""
    adapter = get_adapter()
    return adapter.get_ide_paths(ide_name)


def modify_ide_telemetry(ide_name: str) -> Dict[str, Any]:
    """修改IDE遥测ID的便捷函数 -QW"""
    adapter = get_adapter()
    return adapter.modify_telemetry_only(ide_name)


def clean_ide_workspace(ide_name: str) -> Dict[str, Any]:
    """清理IDE工作区的便捷函数 -QW"""
    adapter = get_adapter()
    return adapter.clean_workspace_only(ide_name)


def get_system_information() -> Dict[str, Any]:
    """获取系统信息的便捷函数 -QW"""
    adapter = get_adapter()
    return adapter.get_system_info()


def run_adapter_test():
    """运行适配器测试的函数 -QW"""
    print("=== AugmentPage 适配器测试 ===")

    # 获取系统信息 -QW
    print("\n1. 系统信息:")
    system_info = get_system_information()
    print(f"   🖥️  系统: {system_info['system']}")
    print(f"   🏗️  平台: {system_info['platform']}")
    print(f"   🐍  Python: {system_info['python_version']}")

    # 测试模块可用性 -QW
    print("\n2. 测试模块可用性:")
    modules = test_augment_modules()
    for module, status in modules.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {module}: {'可用' if status else '不可用'}")

    # 测试IDE检测 -QW
    print("\n3. 测试IDE检测:")
    ides_result = detect_system_ides()
    if ides_result["success"]:
        print(f"   ✅ 检测到 {ides_result['count']} 个IDE:")
        for ide in ides_result["ides"]:
            print(f"      {ide['icon']} {ide['display_name']} ({ide['ide_type']})")
    else:
        print(f"   ❌ IDE检测失败: {ides_result.get('message', '未知错误')}")

    # 测试设备代码生成 -QW
    print("\n4. 测试设备代码生成:")
    codes_result = generate_new_device_codes()
    if codes_result["success"]:
        print(f"   ✅ 生成了 {codes_result['count']} 个设备代码")
        for key, value in codes_result["ids"].items():
            print(f"      {key}: {value[:8]}...")
    else:
        print(f"   ❌ 设备代码生成失败: {codes_result.get('message', '未知错误')}")

    # 测试路径获取 -QW
    print("\n5. 测试路径获取 (Cursor):")
    paths_result = get_ide_path_info("Cursor")
    if paths_result["success"]:
        print("   ✅ 路径信息获取成功:")
        for key, info in paths_result["paths"].items():
            status = "存在" if info["exists"] else "不存在"
            print(f"      {key}: {status}")
    else:
        print(f"   ❌ 路径信息获取失败: {paths_result.get('message', '未知错误')}")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    # 只有直接运行此文件时才执行测试
    run_adapter_test()
