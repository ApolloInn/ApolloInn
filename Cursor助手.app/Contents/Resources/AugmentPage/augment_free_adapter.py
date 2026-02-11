"""
AugmentPage 适配器模块
为主程序提供简化的接口，不依赖webview的轻量级实现
支持跨平台（Windows、macOS、Linux）
-QW
"""

import os
import sys
import json
from typing import Dict, Any, List
from pathlib import Path


class AugmentFreeAdapter:
    """AugmentPage 功能适配器 -QW"""

    def __init__(self):
        self.augment_page_path = None
        self._setup_path()

    def _setup_path(self):
        """设置AugmentPage模块路径 -QW"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.augment_page_path = current_dir
            
            # 确保当前目录在Python路径中 -QW
            if self.augment_page_path not in sys.path:
                sys.path.insert(0, self.augment_page_path)
                print(f"[AugmentPage适配器] ✅ 已添加路径: {self.augment_page_path}")
            else:
                print(f"[AugmentPage适配器] ✅ 路径已存在: {self.augment_page_path}")
        except Exception as e:
            print(f"[AugmentPage适配器] ❌ 路径设置失败: {str(e)}")
    
    def detect_ides(self) -> Dict[str, Any]:
        """检测系统中的IDE -QW"""
        try:
            # 首先尝试使用简单检测器 -QW
            print("[AugmentPage适配器] 🔍 尝试使用简单IDE检测器...")
            return self._use_simple_detector()

        except Exception as e:
            print(f"[AugmentPage适配器] ❌ IDE检测失败: {str(e)}")
            default_result = self._get_default_ides()
            default_result["detection_failed"] = True
            default_result["message"] = f"检测失败: {str(e)}"
            return default_result
    
    def _get_default_ides(self) -> Dict[str, Any]:
        """获取默认IDE列表 -QW"""
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

    def _use_simple_detector(self) -> Dict[str, Any]:
        """使用简单检测器（不依赖webview） -QW"""
        try:
            from simple_ide_detector import simple_detect_ides
            result = simple_detect_ides()

            if result["success"] and result["ides"]:
                print(f"[AugmentPage适配器] ✅ 简单检测器找到 {len(result['ides'])} 个IDE")
                return result
            else:
                print("[AugmentPage适配器] ⚠️ 简单检测器返回空结果，使用默认IDE列表")
                default_result = self._get_default_ides()
                default_result["detection_failed"] = True
                default_result["message"] = "简单检测器返回空结果"
                return default_result

        except Exception as e:
            print(f"[AugmentPage适配器] ❌ 简单检测器失败: {str(e)}")
            default_result = self._get_default_ides()
            default_result["detection_failed"] = True
            default_result["message"] = f"简单检测器失败: {str(e)}"
            return default_result

    def execute_cleanup(self, ide_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行清理操作 -QW"""
        try:
            print(f"[AugmentPage适配器] 🧹 开始清理 {ide_data.get('display_name', '未知IDE')}")
            # 直接使用简单清理器 -QW
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
        """使用简单清理器（不依赖webview） -QW"""
        try:
            from simple_cleaner import simple_cleanup_ide
            result = simple_cleanup_ide(ide_data)

            if result["success"]:
                # 统计清理结果 -QW
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
        """测试各个模块是否可用 -QW"""
        modules_status = {}
        
        try:
            # 测试简单IDE检测模块 -QW
            from simple_ide_detector import simple_detect_ides
            modules_status["simple_ide_detector"] = True
            print("[AugmentPage适配器] ✅ 简单IDE检测器可用")
        except Exception as e:
            modules_status["simple_ide_detector"] = False
            print(f"[AugmentPage适配器] ❌ 简单IDE检测器不可用: {str(e)}")

        try:
            # 测试简单清理器模块 -QW
            from simple_cleaner import simple_cleanup_ide
            modules_status["simple_cleaner"] = True
            print("[AugmentPage适配器] ✅ 简单清理器可用")
        except Exception as e:
            modules_status["simple_cleaner"] = False
            print(f"[AugmentPage适配器] ❌ 简单清理器不可用: {str(e)}")

        try:
            # 测试单实例检查器 -QW
            from single_instance_checker import check_single_instance
            modules_status["single_instance_checker"] = True
            print("[AugmentPage适配器] ✅ 单实例检查器可用")
        except Exception as e:
            modules_status["single_instance_checker"] = False
            print(f"[AugmentPage适配器] ❌ 单实例检查器不可用: {str(e)}")
        
        return modules_status

    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息 -QW"""
        import platform
        
        return {
            "system": platform.system(),
            "platform": platform.platform(),
            "architecture": platform.architecture(),
            "python_version": platform.python_version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }


# 创建全局适配器实例 -QW
_adapter_instance = None

def get_adapter() -> AugmentFreeAdapter:
    """获取适配器实例（单例模式） -QW"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = AugmentFreeAdapter()
    return _adapter_instance


def detect_system_ides() -> Dict[str, Any]:
    """检测系统IDE的便捷函数 -QW"""
    adapter = get_adapter()
    return adapter.detect_ides()


def cleanup_ide_data(ide_data: Dict[str, Any]) -> Dict[str, Any]:
    """清理IDE数据的便捷函数 -QW"""
    adapter = get_adapter()
    return adapter.execute_cleanup(ide_data)


def test_augment_free_modules() -> Dict[str, bool]:
    """测试Augment-Free模块的便捷函数 -QW"""
    adapter = get_adapter()
    return adapter.test_modules()


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
    modules = test_augment_free_modules()
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

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    # 只有直接运行此文件时才执行测试 -QW
    run_adapter_test()
