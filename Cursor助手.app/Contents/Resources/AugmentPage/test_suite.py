#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AugmentPage 集成测试套件
完整测试所有功能模块的集成测试和示例
支持跨平台（Windows、macOS、Linux）
-QW
"""

import os
import sys
import json
import time
import platform
from typing import Dict, Any, List
from pathlib import Path


class AugmentPageTestSuite:
    """AugmentPage 集成测试套件 -QW"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.test_results = {}
        self.start_time = time.time()
        
        print("=" * 60)
        print("🧪 AugmentPage 集成测试套件")
        print("=" * 60)
        print(f"系统: {platform.system()} {platform.release()}")
        print(f"Python: {platform.python_version()}")
        print(f"架构: {platform.machine()}")
        print("=" * 60)
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试 -QW"""
        print("\n🚀 开始运行完整测试套件...")
        
        # 测试列表 -QW
        tests = [
            ("系统信息", self.test_system_info),
            ("路径工具", self.test_path_utils),
            ("设备代码生成", self.test_device_codes),
            ("IDE检测", self.test_ide_detection),
            ("适配器功能", self.test_adapter),
            ("API核心", self.test_api_core),
            ("遥测处理器", self.test_telemetry_handler),
            ("数据库处理器", self.test_database_handler),
            ("工作区处理器", self.test_workspace_handler),
            ("JetBrains处理器", self.test_jetbrains_handler),
            ("简单检测器", self.test_simple_detectors),
            ("邮箱验证码", self.test_email_verification),
            ("浏览器管理", self.test_browser_manager),
            ("自动登录", self.test_auto_login),
            ("重置工具", self.test_reset_tools)
        ]
        
        # 执行测试 -QW
        for test_name, test_func in tests:
            print(f"\n📋 测试: {test_name}")
            try:
                result = test_func()
                self.test_results[test_name] = result
                status = "✅ 通过" if result.get("success", False) else "❌ 失败"
                print(f"   {status}: {result.get('message', '无消息')}")
            except Exception as e:
                self.test_results[test_name] = {
                    "success": False,
                    "error": str(e),
                    "message": f"测试异常: {str(e)}"
                }
                print(f"   ❌ 异常: {str(e)}")
        
        # 生成测试报告 -QW
        return self.generate_test_report()
    
    def test_system_info(self) -> Dict[str, Any]:
        """测试系统信息获取 -QW"""
        try:
            from .adapter import get_system_information
            info = get_system_information()
            
            required_keys = ["system", "platform", "python_version"]
            missing_keys = [key for key in required_keys if key not in info]
            
            if missing_keys:
                return {
                    "success": False,
                    "message": f"缺少必要信息: {missing_keys}"
                }
            
            return {
                "success": True,
                "message": f"系统信息获取成功 ({info['system']})",
                "data": info
            }
        except Exception as e:
            return {"success": False, "message": f"系统信息测试失败: {str(e)}"}
    
    def test_path_utils(self) -> Dict[str, Any]:
        """测试路径工具 -QW"""
        try:
            from .utils.paths import (
                get_home_dir,
                get_app_data_dir,
                get_storage_path,
                get_cursor_executable_path
            )
            
            # 测试基本路径 -QW
            home_dir = get_home_dir()
            app_data_dir = get_app_data_dir()
            storage_path = get_storage_path("Cursor")
            executable_path = get_cursor_executable_path()
            
            if not home_dir or not app_data_dir:
                return {"success": False, "message": "基本路径获取失败"}
            
            return {
                "success": True,
                "message": "路径工具测试通过",
                "data": {
                    "home_dir": home_dir,
                    "app_data_dir": app_data_dir,
                    "storage_path": storage_path,
                    "executable_path": executable_path
                }
            }
        except Exception as e:
            return {"success": False, "message": f"路径工具测试失败: {str(e)}"}
    
    def test_device_codes(self) -> Dict[str, Any]:
        """测试设备代码生成 -QW"""
        try:
            from .utils.device_codes import (
                generate_machine_id,
                generate_device_id,
                generate_telemetry_ids,
                validate_machine_id,
                validate_device_id
            )
            
            # 生成代码 -QW
            machine_id = generate_machine_id()
            device_id = generate_device_id()
            telemetry_ids = generate_telemetry_ids()
            
            # 验证代码 -QW
            if not validate_machine_id(machine_id):
                return {"success": False, "message": "机器ID验证失败"}
            
            if not validate_device_id(device_id):
                return {"success": False, "message": "设备ID验证失败"}
            
            if len(telemetry_ids) < 3:
                return {"success": False, "message": "遥测ID集合不完整"}
            
            return {
                "success": True,
                "message": f"设备代码生成测试通过 (生成了{len(telemetry_ids)}个ID)",
                "data": {
                    "machine_id": machine_id[:8] + "...",
                    "device_id": device_id,
                    "telemetry_count": len(telemetry_ids)
                }
            }
        except Exception as e:
            return {"success": False, "message": f"设备代码测试失败: {str(e)}"}
    
    def test_ide_detection(self) -> Dict[str, Any]:
        """测试IDE检测 -QW"""
        try:
            from .utils.ide_detector import detect_ides, IDEDetector
            
            # 测试检测功能 -QW
            result = detect_ides()
            
            if not result.get("success", False):
                return {"success": False, "message": "IDE检测失败"}
            
            # 测试检测器类 -QW
            detector = IDEDetector()
            ides = detector.detect_all_ides()
            
            return {
                "success": True,
                "message": f"IDE检测测试通过 (检测到{result['count']}个IDE)",
                "data": {
                    "detected_count": result["count"],
                    "detector_count": len(ides)
                }
            }
        except Exception as e:
            return {"success": False, "message": f"IDE检测测试失败: {str(e)}"}
    
    def test_adapter(self) -> Dict[str, Any]:
        """测试适配器功能 -QW"""
        try:
            from .adapter import get_adapter, test_augment_modules
            
            # 测试适配器实例 -QW
            adapter = get_adapter()
            
            # 测试模块可用性 -QW
            modules = test_augment_modules()
            available_modules = sum(1 for status in modules.values() if status)
            
            # 测试系统信息 -QW
            system_info = adapter.get_system_info()
            
            return {
                "success": True,
                "message": f"适配器测试通过 ({available_modules}/{len(modules)}个模块可用)",
                "data": {
                    "available_modules": available_modules,
                    "total_modules": len(modules),
                    "system": system_info.get("system", "未知")
                }
            }
        except Exception as e:
            return {"success": False, "message": f"适配器测试失败: {str(e)}"}
    
    def test_api_core(self) -> Dict[str, Any]:
        """测试API核心 -QW"""
        try:
            from .api.core import AugmentPageAPI
            
            # 创建API实例 -QW
            api = AugmentPageAPI()
            
            # 测试基本功能 -QW
            if not hasattr(api, 'status') or api.status != "ready":
                return {"success": False, "message": "API状态异常"}
            
            # 测试编辑器类型设置 -QW
            if hasattr(api, 'set_editor_type'):
                api.set_editor_type("Cursor")
            
            return {
                "success": True,
                "message": "API核心测试通过",
                "data": {
                    "status": api.status,
                    "editor_type": getattr(api, 'editor_type', '未设置')
                }
            }
        except Exception as e:
            return {"success": False, "message": f"API核心测试失败: {str(e)}"}
    
    def test_telemetry_handler(self) -> Dict[str, Any]:
        """测试遥测处理器 -QW"""
        try:
            from .api.handlers.telemetry import modify_telemetry_ids
            
            # 注意：这里只测试函数是否可调用，不实际修改文件 -QW
            # 因为可能没有实际的IDE配置文件
            
            return {
                "success": True,
                "message": "遥测处理器模块加载成功",
                "data": {"function_available": True}
            }
        except Exception as e:
            return {"success": False, "message": f"遥测处理器测试失败: {str(e)}"}
    
    def test_database_handler(self) -> Dict[str, Any]:
        """测试数据库处理器 -QW"""
        try:
            from .api.handlers.database import clean_augment_data, vacuum_database
            
            return {
                "success": True,
                "message": "数据库处理器模块加载成功",
                "data": {"functions_available": True}
            }
        except Exception as e:
            return {"success": False, "message": f"数据库处理器测试失败: {str(e)}"}
    
    def test_workspace_handler(self) -> Dict[str, Any]:
        """测试工作区处理器 -QW"""
        try:
            from .api.handlers.workspace import clean_workspace_storage
            
            return {
                "success": True,
                "message": "工作区处理器模块加载成功",
                "data": {"function_available": True}
            }
        except Exception as e:
            return {"success": False, "message": f"工作区处理器测试失败: {str(e)}"}
    
    def test_jetbrains_handler(self) -> Dict[str, Any]:
        """测试JetBrains处理器 -QW"""
        try:
            from .api.handlers.jetbrains import (
                get_jetbrains_info,
                get_jetbrains_config_dir,
                modify_jetbrains_ids
            )
            
            # 测试配置目录获取 -QW
            config_dir = get_jetbrains_config_dir()
            
            return {
                "success": True,
                "message": "JetBrains处理器模块加载成功",
                "data": {
                    "config_dir": str(config_dir),
                    "config_dir_exists": config_dir.exists()
                }
            }
        except Exception as e:
            return {"success": False, "message": f"JetBrains处理器测试失败: {str(e)}"}
    
    def test_simple_detectors(self) -> Dict[str, Any]:
        """测试简单检测器 -QW"""
        try:
            from . import simple_ide_detector, simple_cleaner
            
            # 测试简单IDE检测 -QW
            if hasattr(simple_ide_detector, 'simple_detect_ides'):
                result = simple_ide_detector.simple_detect_ides()
                detected_count = len(result.get("ides", []))
            else:
                detected_count = 0
            
            return {
                "success": True,
                "message": f"简单检测器测试通过 (检测到{detected_count}个IDE)",
                "data": {"detected_count": detected_count}
            }
        except Exception as e:
            return {"success": False, "message": f"简单检测器测试失败: {str(e)}"}
    
    def test_email_verification(self) -> Dict[str, Any]:
        """测试邮箱验证码功能 -QW"""
        try:
            from . import get_email_code
            
            # 测试邮箱处理器创建 -QW
            if hasattr(get_email_code, 'EmailVerificationHandler'):
                handler = get_email_code.EmailVerificationHandler()
                
                return {
                    "success": True,
                    "message": "邮箱验证码模块加载成功",
                    "data": {"handler_created": True}
                }
            else:
                return {"success": False, "message": "邮箱验证码处理器不可用"}
        except Exception as e:
            return {"success": False, "message": f"邮箱验证码测试失败: {str(e)}"}
    
    def test_browser_manager(self) -> Dict[str, Any]:
        """测试浏览器管理器 -QW"""
        try:
            from . import browser_utils
            
            # 测试浏览器管理器创建 -QW
            if hasattr(browser_utils, 'BrowserManager'):
                manager = browser_utils.BrowserManager()
                
                # 测试依赖检测 -QW
                drission_available = manager._is_drission_page_available()
                selenium_available = manager._is_selenium_available()
                
                return {
                    "success": True,
                    "message": "浏览器管理器模块加载成功",
                    "data": {
                        "drission_available": drission_available,
                        "selenium_available": selenium_available
                    }
                }
            else:
                return {"success": False, "message": "浏览器管理器不可用"}
        except Exception as e:
            return {"success": False, "message": f"浏览器管理器测试失败: {str(e)}"}
    
    def test_auto_login(self) -> Dict[str, Any]:
        """测试自动登录功能 -QW"""
        try:
            from . import CursorAutoLogin
            
            # 测试自动登录器创建 -QW
            if hasattr(CursorAutoLogin, 'CursorAutoLogin'):
                auto_login = CursorAutoLogin.CursorAutoLogin()
                
                # 测试系统支持检测 -QW
                automation_support = auto_login._check_automation_support()
                browser_automation = auto_login._is_browser_automation_available()
                
                return {
                    "success": True,
                    "message": "自动登录模块加载成功",
                    "data": {
                        "automation_support": automation_support,
                        "browser_automation": browser_automation
                    }
                }
            else:
                return {"success": False, "message": "自动登录器不可用"}
        except Exception as e:
            return {"success": False, "message": f"自动登录测试失败: {str(e)}"}
    
    def test_reset_tools(self) -> Dict[str, Any]:
        """测试重置工具 -QW"""
        try:
            from . import totally_reset_cursor, reset_machine_manual
            
            # 测试重置器创建 -QW
            tools_available = 0
            
            if hasattr(totally_reset_cursor, 'CursorIDResetter'):
                tools_available += 1
            
            if hasattr(reset_machine_manual, 'MachineIDResetter'):
                tools_available += 1
            
            return {
                "success": True,
                "message": f"重置工具模块加载成功 ({tools_available}/2个工具可用)",
                "data": {"tools_available": tools_available}
            }
        except Exception as e:
            return {"success": False, "message": f"重置工具测试失败: {str(e)}"}
    
    def generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告 -QW"""
        end_time = time.time()
        duration = end_time - self.start_time
        
        # 统计结果 -QW
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get("success", False))
        failed_tests = total_tests - passed_tests
        
        # 生成报告 -QW
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "duration": duration
            },
            "system_info": {
                "system": platform.system(),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "architecture": platform.machine()
            },
            "test_results": self.test_results
        }
        
        # 打印报告 -QW
        print("\n" + "=" * 60)
        print("📊 测试报告")
        print("=" * 60)
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {failed_tests}")
        print(f"成功率: {report['summary']['success_rate']:.1f}%")
        print(f"耗时: {duration:.2f}秒")
        print("=" * 60)
        
        return report


def run_quick_test():
    """运行快速测试 -QW"""
    print("🚀 运行AugmentPage快速测试...")

    suite = AugmentPageTestSuite()

    # 只运行核心测试 -QW
    core_tests = [
        ("系统信息", suite.test_system_info),
        ("路径工具", suite.test_path_utils),
        ("设备代码生成", suite.test_device_codes),
        ("IDE检测", suite.test_ide_detection),
        ("适配器功能", suite.test_adapter)
    ]

    passed = 0
    for test_name, test_func in core_tests:
        try:
            result = test_func()
            status = "✅" if result.get("success", False) else "❌"
            print(f"{status} {test_name}: {result.get('message', '无消息')}")
            if result.get("success", False):
                passed += 1
        except Exception as e:
            print(f"❌ {test_name}: 测试异常 - {str(e)}")

    print(f"\n📊 快速测试完成: {passed}/{len(core_tests)} 通过")
    return passed == len(core_tests)


def run_full_test():
    """运行完整测试 -QW"""
    suite = AugmentPageTestSuite()
    report = suite.run_all_tests()

    # 保存测试报告 -QW
    try:
        report_file = Path(__file__).parent / "test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n📄 测试报告已保存: {report_file}")
    except Exception as e:
        print(f"\n⚠️ 保存测试报告失败: {str(e)}")

    return report


def demo_basic_usage():
    """演示基本用法 -QW"""
    print("\n" + "=" * 60)
    print("📚 AugmentPage 基本用法演示")
    print("=" * 60)

    try:
        # 1. 导入适配器 -QW
        print("\n1. 导入适配器:")
        from .adapter import get_adapter
        adapter = get_adapter()
        print("   ✅ 适配器导入成功")

        # 2. 检测IDE -QW
        print("\n2. 检测系统IDE:")
        ides_result = adapter.detect_ides()
        if ides_result["success"]:
            print(f"   ✅ 检测到 {ides_result['count']} 个IDE")
            for ide in ides_result["ides"][:3]:  # 只显示前3个
                print(f"      {ide['icon']} {ide['display_name']}")
        else:
            print("   ❌ IDE检测失败")

        # 3. 生成设备代码 -QW
        print("\n3. 生成设备代码:")
        codes_result = adapter.generate_device_codes()
        if codes_result["success"]:
            print(f"   ✅ 生成了 {codes_result['count']} 个设备代码")
            for key, value in list(codes_result["ids"].items())[:2]:  # 只显示前2个
                print(f"      {key}: {value[:8]}...")
        else:
            print("   ❌ 设备代码生成失败")

        # 4. 获取系统信息 -QW
        print("\n4. 获取系统信息:")
        system_info = adapter.get_system_info()
        print(f"   ✅ 系统: {system_info['system']}")
        print(f"   ✅ 平台: {system_info['platform']}")
        print(f"   ✅ Python: {system_info['python_version']}")

        # 5. 测试模块可用性 -QW
        print("\n5. 测试模块可用性:")
        modules = adapter.test_modules()
        available = sum(1 for status in modules.values() if status)
        print(f"   ✅ {available}/{len(modules)} 个模块可用")

        print("\n" + "=" * 60)
        print("✅ 基本用法演示完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {str(e)}")


def demo_advanced_usage():
    """演示高级用法 -QW"""
    print("\n" + "=" * 60)
    print("🔧 AugmentPage 高级用法演示")
    print("=" * 60)

    try:
        # 1. 使用API核心 -QW
        print("\n1. 使用API核心:")
        from .api.core import AugmentPageAPI
        api = AugmentPageAPI()
        print(f"   ✅ API状态: {api.status}")

        # 2. 使用路径工具 -QW
        print("\n2. 使用路径工具:")
        from .utils.paths import get_storage_path, get_cursor_executable_path
        storage_path = get_storage_path("Cursor")
        executable_path = get_cursor_executable_path()
        print(f"   ✅ Cursor存储路径: {storage_path}")
        print(f"   ✅ Cursor可执行文件: {executable_path}")

        # 3. 使用设备代码工具 -QW
        print("\n3. 使用设备代码工具:")
        from .utils.device_codes import generate_machine_id, generate_device_id
        machine_id = generate_machine_id()
        device_id = generate_device_id()
        print(f"   ✅ 机器ID: {machine_id[:8]}...")
        print(f"   ✅ 设备ID: {device_id}")

        # 4. 使用IDE检测器 -QW
        print("\n4. 使用IDE检测器:")
        from .utils.ide_detector import IDEDetector
        detector = IDEDetector()
        vscode_ides = detector.detect_vscode_variants()
        jetbrains_ides = detector.detect_jetbrains_ides()
        print(f"   ✅ VSCode系列: {len(vscode_ides)} 个")
        print(f"   ✅ JetBrains系列: {len(jetbrains_ides)} 个")

        print("\n" + "=" * 60)
        print("✅ 高级用法演示完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AugmentPage 测试套件")
    parser.add_argument("--quick", action="store_true", help="运行快速测试")
    parser.add_argument("--full", action="store_true", help="运行完整测试")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--demo-advanced", action="store_true", help="运行高级演示")

    args = parser.parse_args()

    if args.quick:
        run_quick_test()
    elif args.full:
        run_full_test()
    elif args.demo:
        demo_basic_usage()
    elif args.demo_advanced:
        demo_advanced_usage()
    else:
        # 默认运行快速测试和基本演示 -QW
        print("🎯 运行默认测试和演示...")
        run_quick_test()
        demo_basic_usage()
