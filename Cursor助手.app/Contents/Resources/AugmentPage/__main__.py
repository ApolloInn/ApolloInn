#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AugmentPage 主程序入口
支持作为模块运行: python -m AugmentPage
支持跨平台（Windows、macOS、Linux）
-QW
"""

import sys
import os
from pathlib import Path

# 添加当前目录到Python路径 -QW
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


def main():
    """主程序入口 -QW"""
    try:
        # 检查命令行参数 -QW
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command in ["cli", "cmd", "command"]:
                # 运行命令行界面 -QW
                from .cli import main as cli_main
                cli_main()
                return
            
            elif command in ["test", "tests"]:
                # 运行测试 -QW
                from .test_suite import run_quick_test, run_full_test
                
                if len(sys.argv) > 2 and sys.argv[2] == "--full":
                    run_full_test()
                else:
                    run_quick_test()
                return
            
            elif command in ["demo", "example", "examples"]:
                # 运行演示 -QW
                from .examples import demo_basic_usage, demo_advanced_usage
                
                if len(sys.argv) > 2 and sys.argv[2] == "--advanced":
                    demo_advanced_usage()
                else:
                    demo_basic_usage()
                return
            
            elif command in ["config", "configure"]:
                # 配置管理 -QW
                run_config_manager()
                return
            
            elif command in ["status", "info"]:
                # 显示状态信息 -QW
                show_status_info()
                return
            
            elif command in ["help", "-h", "--help"]:
                # 显示帮助 -QW
                show_help()
                return
        
        # 默认行为：显示交互式菜单 -QW
        run_interactive_menu()
        
    except KeyboardInterrupt:
        print("\n⏹️ 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序运行失败: {str(e)}")
        sys.exit(1)


def run_interactive_menu():
    """运行交互式菜单 -QW"""
    print("=" * 60)
    print("🎯 AugmentPage - 跨平台IDE管理工具")
    print("=" * 60)
    print("版本: 2.0.0")
    print("作者: QW")
    print("=" * 60)
    
    while True:
        print("\n📋 请选择操作:")
        print("1. 🔍 检测系统IDE")
        print("2. 🔢 生成设备代码")
        print("3. 📡 修改遥测ID")
        print("4. 🗂️ 清理工作区")
        print("5. 🧹 完整清理")
        print("6. 📁 查看路径信息")
        print("7. 🧪 运行测试")
        print("8. 📚 运行演示")
        print("9. ⚙️ 配置管理")
        print("10. 📊 系统状态")
        print("11. 💻 命令行模式")
        print("0. 🚪 退出")
        
        try:
            choice = input("\n请输入选择 (0-11): ").strip()
            
            if choice == "0":
                print("👋 再见！")
                break
            elif choice == "1":
                run_ide_detection()
            elif choice == "2":
                run_code_generation()
            elif choice == "3":
                run_telemetry_modification()
            elif choice == "4":
                run_workspace_cleanup()
            elif choice == "5":
                run_full_cleanup()
            elif choice == "6":
                run_path_info()
            elif choice == "7":
                run_test_menu()
            elif choice == "8":
                run_demo_menu()
            elif choice == "9":
                run_config_manager()
            elif choice == "10":
                show_status_info()
            elif choice == "11":
                print("💻 启动命令行模式...")
                from .cli import main as cli_main
                cli_main()
            else:
                print("❌ 无效选择，请重试")
                
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 操作失败: {str(e)}")


def run_ide_detection():
    """运行IDE检测 -QW"""
    print("\n🔍 检测系统IDE...")
    try:
        from .adapter import detect_system_ides
        result = detect_system_ides()
        
        if result["success"]:
            print(f"✅ 检测成功，找到 {result['count']} 个IDE:")
            for ide in result["ides"]:
                print(f"   {ide['icon']} {ide['display_name']} ({ide['ide_type']})")
        else:
            print(f"❌ 检测失败: {result.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ IDE检测失败: {str(e)}")


def run_code_generation():
    """运行代码生成 -QW"""
    print("\n🔢 生成设备代码...")
    try:
        from .adapter import generate_new_device_codes
        result = generate_new_device_codes()
        
        if result["success"]:
            print(f"✅ 生成成功，共 {result['count']} 个代码:")
            for key, value in result["ids"].items():
                print(f"   {key}: {value[:8]}...")
        else:
            print(f"❌ 生成失败: {result.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ 代码生成失败: {str(e)}")


def run_telemetry_modification():
    """运行遥测修改 -QW"""
    ide_name = input("\n请输入IDE名称 (如: Cursor): ").strip()
    if not ide_name:
        print("❌ IDE名称不能为空")
        return
    
    print(f"📡 修改 {ide_name} 遥测ID...")
    print("⚠️ 警告: 这将修改IDE配置文件，操作前会自动备份")
    
    confirm = input("是否继续? (y/N): ").strip().lower()
    if confirm != 'y':
        print("操作已取消")
        return
    
    try:
        from .adapter import modify_ide_telemetry
        result = modify_ide_telemetry(ide_name)
        
        if result["success"]:
            print("✅ 遥测ID修改成功")
        else:
            print(f"❌ 修改失败: {result.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ 遥测修改失败: {str(e)}")


def run_workspace_cleanup():
    """运行工作区清理 -QW"""
    ide_name = input("\n请输入IDE名称 (如: Cursor): ").strip()
    if not ide_name:
        print("❌ IDE名称不能为空")
        return
    
    print(f"🗂️ 清理 {ide_name} 工作区...")
    print("⚠️ 警告: 这将删除工作区中的所有文件，操作前会自动备份")
    
    confirm = input("是否继续? (y/N): ").strip().lower()
    if confirm != 'y':
        print("操作已取消")
        return
    
    try:
        from .adapter import clean_ide_workspace
        result = clean_ide_workspace(ide_name)
        
        if result["success"]:
            print("✅ 工作区清理成功")
        else:
            print(f"❌ 清理失败: {result.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ 工作区清理失败: {str(e)}")


def run_full_cleanup():
    """运行完整清理 -QW"""
    ide_name = input("\n请输入IDE名称 (如: Cursor): ").strip()
    if not ide_name:
        print("❌ IDE名称不能为空")
        return
    
    print(f"🧹 完整清理 {ide_name}...")
    print("⚠️ 警告: 这将执行完整清理操作，包括遥测ID重置、工作区清理等")
    print("操作前会自动备份所有文件")
    
    confirm = input("是否继续? (y/N): ").strip().lower()
    if confirm != 'y':
        print("操作已取消")
        return
    
    try:
        from .adapter import cleanup_ide_data
        result = cleanup_ide_data(ide_name)
        
        if result["success"]:
            print("✅ 完整清理成功")
        else:
            print(f"❌ 清理失败: {result.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ 完整清理失败: {str(e)}")


def run_path_info():
    """运行路径信息 -QW"""
    ide_name = input("\n请输入IDE名称 (如: Cursor): ").strip()
    if not ide_name:
        print("❌ IDE名称不能为空")
        return
    
    print(f"📁 获取 {ide_name} 路径信息...")
    try:
        from .adapter import get_ide_path_info
        result = get_ide_path_info(ide_name)
        
        if result["success"]:
            print(f"✅ {ide_name} 路径信息:")
            for key, info in result["paths"].items():
                status = "存在" if info["exists"] else "不存在"
                print(f"   {key}: {status}")
                print(f"      路径: {info['path']}")
        else:
            print(f"❌ 获取失败: {result.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ 路径信息获取失败: {str(e)}")


def run_test_menu():
    """运行测试菜单 -QW"""
    print("\n🧪 测试选项:")
    print("1. 快速测试")
    print("2. 完整测试")
    
    choice = input("请选择 (1-2): ").strip()
    
    try:
        if choice == "1":
            from .test_suite import run_quick_test
            run_quick_test()
        elif choice == "2":
            from .test_suite import run_full_test
            run_full_test()
        else:
            print("❌ 无效选择")
    except Exception as e:
        print(f"❌ 测试运行失败: {str(e)}")


def run_demo_menu():
    """运行演示菜单 -QW"""
    print("\n📚 演示选项:")
    print("1. 基本演示")
    print("2. 高级演示")
    
    choice = input("请选择 (1-2): ").strip()
    
    try:
        if choice == "1":
            from .examples import demo_basic_usage
            demo_basic_usage()
        elif choice == "2":
            from .examples import demo_advanced_usage
            demo_advanced_usage()
        else:
            print("❌ 无效选择")
    except Exception as e:
        print(f"❌ 演示运行失败: {str(e)}")


def run_config_manager():
    """运行配置管理 -QW"""
    print("\n⚙️ 配置管理")
    try:
        from .config_manager import get_config_manager
        manager = get_config_manager()
        
        print(f"配置目录: {manager.config_dir}")
        print(f"自动备份: {manager.is_auto_backup_enabled()}")
        print(f"首选IDE: {manager.get_preferred_ide()}")
        print(f"调试模式: {manager.is_debug_mode()}")
        
        # 配置验证 -QW
        validation = manager.validate_config()
        if validation["valid"]:
            print("✅ 配置验证通过")
        else:
            print("❌ 配置验证失败:")
            for issue in validation["issues"]:
                print(f"   - {issue}")
        
        if validation["warnings"]:
            print("⚠️ 配置警告:")
            for warning in validation["warnings"]:
                print(f"   - {warning}")
                
    except Exception as e:
        print(f"❌ 配置管理失败: {str(e)}")


def show_status_info():
    """显示状态信息 -QW"""
    print("\n📊 系统状态")
    try:
        from .adapter import get_system_information
        info = get_system_information()
        
        print(f"系统: {info['system']}")
        print(f"平台: {info['platform']}")
        print(f"架构: {info['machine']}")
        print(f"Python: {info['python_version']}")
        
    except Exception as e:
        print(f"❌ 状态信息获取失败: {str(e)}")


def show_help():
    """显示帮助信息 -QW"""
    print("""
🎯 AugmentPage - 跨平台IDE管理工具

用法:
  python -m AugmentPage [命令] [选项]

命令:
  cli, cmd, command     启动命令行界面
  test [--full]         运行测试（--full 为完整测试）
  demo [--advanced]     运行演示（--advanced 为高级演示）
  config, configure     配置管理
  status, info          显示系统状态
  help, -h, --help      显示此帮助信息

无参数运行时将启动交互式菜单。

示例:
  python -m AugmentPage                    # 交互式菜单
  python -m AugmentPage cli                # 命令行界面
  python -m AugmentPage test --full        # 完整测试
  python -m AugmentPage demo --advanced    # 高级演示
  python -m AugmentPage status             # 系统状态
    """)


if __name__ == "__main__":
    main()
