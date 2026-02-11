#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AugmentPage 使用示例
展示各种功能的具体使用方法
支持跨平台（Windows、macOS、Linux）
-QW
"""

import json
import time
from typing import Dict, Any


def example_basic_ide_detection():
    """示例：基本IDE检测 -QW"""
    print("=" * 50)
    print("📋 示例：基本IDE检测")
    print("=" * 50)
    
    try:
        from .adapter import detect_system_ides
        
        print("正在检测系统中的IDE...")
        result = detect_system_ides()
        
        if result["success"]:
            print(f"✅ 检测成功，找到 {result['count']} 个IDE:")
            for ide in result["ides"]:
                print(f"   {ide['icon']} {ide['display_name']} ({ide['ide_type']})")
                print(f"      配置路径: {ide['config_path']}")
        else:
            print(f"❌ 检测失败: {result.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 示例执行失败: {str(e)}")


def example_device_code_generation():
    """示例：设备代码生成 -QW"""
    print("\n" + "=" * 50)
    print("🔢 示例：设备代码生成")
    print("=" * 50)
    
    try:
        from .utils.device_codes import (
            generate_machine_id,
            generate_device_id,
            generate_telemetry_ids,
            generate_realistic_machine_id
        )
        
        print("生成基本设备代码:")
        machine_id = generate_machine_id()
        device_id = generate_device_id()
        print(f"   机器ID: {machine_id}")
        print(f"   设备ID: {device_id}")
        
        print("\n生成完整遥测ID集合:")
        telemetry_ids = generate_telemetry_ids()
        for key, value in telemetry_ids.items():
            print(f"   {key}: {value}")
        
        print("\n生成真实感机器ID:")
        realistic_id = generate_realistic_machine_id()
        print(f"   真实感机器ID: {realistic_id}")
        
    except Exception as e:
        print(f"❌ 示例执行失败: {str(e)}")


def example_path_utilities():
    """示例：路径工具使用 -QW"""
    print("\n" + "=" * 50)
    print("📁 示例：路径工具使用")
    print("=" * 50)
    
    try:
        from .utils.paths import (
            get_home_dir,
            get_app_data_dir,
            get_storage_path,
            get_db_path,
            get_machine_id_path,
            get_workspace_storage_path,
            get_cursor_executable_path,
            get_cursor_workbench_js_path
        )
        
        print("基本路径:")
        print(f"   用户主目录: {get_home_dir()}")
        print(f"   应用数据目录: {get_app_data_dir()}")
        
        print("\nCursor相关路径:")
        print(f"   存储文件: {get_storage_path('Cursor')}")
        print(f"   数据库文件: {get_db_path('Cursor')}")
        print(f"   机器ID文件: {get_machine_id_path('Cursor')}")
        print(f"   工作区存储: {get_workspace_storage_path('Cursor')}")
        print(f"   可执行文件: {get_cursor_executable_path()}")
        print(f"   Workbench JS: {get_cursor_workbench_js_path()}")
        
    except Exception as e:
        print(f"❌ 示例执行失败: {str(e)}")


def example_telemetry_modification():
    """示例：遥测ID修改 -QW"""
    print("\n" + "=" * 50)
    print("📡 示例：遥测ID修改")
    print("=" * 50)
    
    try:
        from .api.handlers.telemetry import modify_telemetry_ids
        from .utils.paths import get_storage_path
        import os
        
        # 检查配置文件是否存在 -QW
        storage_path = get_storage_path("Cursor")
        if not os.path.exists(storage_path):
            print(f"⚠️ Cursor配置文件不存在: {storage_path}")
            print("   这是正常的，如果您没有安装Cursor")
            return
        
        print("正在修改Cursor遥测ID...")
        print("⚠️ 注意：这将修改实际的配置文件，请确保已备份")
        
        # 询问用户确认 -QW
        confirm = input("是否继续？(y/N): ").strip().lower()
        if confirm != 'y':
            print("操作已取消")
            return
        
        result = modify_telemetry_ids("Cursor")
        
        print("修改结果:")
        print(f"   编辑器类型: {result['editor_type']}")
        print(f"   备份路径: {result['storage_backup_path']}")
        print(f"   新ID数量: {len(result['new_ids'])}")
        
        print("\n新生成的ID:")
        for key, value in result['new_ids'].items():
            print(f"   {key}: {value}")
            
    except FileNotFoundError as e:
        print(f"⚠️ 文件未找到: {str(e)}")
    except Exception as e:
        print(f"❌ 示例执行失败: {str(e)}")


def example_workspace_cleanup():
    """示例：工作区清理 -QW"""
    print("\n" + "=" * 50)
    print("🗂️ 示例：工作区清理")
    print("=" * 50)
    
    try:
        from .api.handlers.workspace import clean_workspace_storage
        from .utils.paths import get_workspace_storage_path
        import os
        
        # 检查工作区目录是否存在 -QW
        workspace_path = get_workspace_storage_path("Cursor")
        if not os.path.exists(workspace_path):
            print(f"⚠️ Cursor工作区目录不存在: {workspace_path}")
            print("   这是正常的，如果您没有使用过Cursor")
            return
        
        print("正在清理Cursor工作区存储...")
        print("⚠️ 注意：这将删除工作区中的所有文件，请确保已备份")
        
        # 询问用户确认 -QW
        confirm = input("是否继续？(y/N): ").strip().lower()
        if confirm != 'y':
            print("操作已取消")
            return
        
        result = clean_workspace_storage("Cursor")
        
        print("清理结果:")
        print(f"   备份路径: {result['backup_path']}")
        print(f"   删除文件数: {result['deleted_files_count']}")
        print(f"   失败操作数: {len(result['failed_operations'])}")
        print(f"   压缩失败数: {len(result['failed_compressions'])}")
        
        if result['failed_operations']:
            print("\n失败的操作:")
            for failure in result['failed_operations'][:3]:  # 只显示前3个
                print(f"   {failure['type']}: {failure['path']}")
                
    except FileNotFoundError as e:
        print(f"⚠️ 文件未找到: {str(e)}")
    except Exception as e:
        print(f"❌ 示例执行失败: {str(e)}")


def example_jetbrains_handling():
    """示例：JetBrains IDE处理 -QW"""
    print("\n" + "=" * 50)
    print("🧠 示例：JetBrains IDE处理")
    print("=" * 50)
    
    try:
        from .api.handlers.jetbrains import get_jetbrains_info, modify_jetbrains_ids
        
        print("获取JetBrains IDE信息...")
        info = get_jetbrains_info()
        
        if info['success']:
            print(f"✅ 找到 {info['count']} 个JetBrains IDE:")
            for ide in info['ides']:
                print(f"   📁 {ide['name']}")
                print(f"      路径: {ide['path']}")
                print(f"      设备ID文件: {'存在' if ide['device_id_exists'] else '不存在'}")
                print(f"      用户ID文件: {'存在' if ide['user_id_exists'] else '不存在'}")
            
            # 如果有IDE，演示修改ID -QW
            if info['ides']:
                first_ide = info['ides'][0]['name']
                print(f"\n演示修改 {first_ide} 的ID...")
                
                # 询问用户确认 -QW
                confirm = input("是否继续？(y/N): ").strip().lower()
                if confirm == 'y':
                    result = modify_jetbrains_ids(first_ide)
                    
                    if result['success']:
                        print("✅ ID修改成功")
                        if result['device_id_result'].get('success'):
                            print(f"   设备ID: {result['device_id_result']['new_id']}")
                        if result['user_id_result'].get('success'):
                            print(f"   用户ID: {result['user_id_result']['new_id']}")
                    else:
                        print("❌ ID修改失败")
                        for error in result['errors']:
                            print(f"   错误: {error}")
                else:
                    print("操作已取消")
        else:
            print(f"⚠️ {info['message']}")
            
    except Exception as e:
        print(f"❌ 示例执行失败: {str(e)}")


def example_email_verification():
    """示例：邮箱验证码 -QW"""
    print("\n" + "=" * 50)
    print("📧 示例：邮箱验证码")
    print("=" * 50)
    
    try:
        from .get_email_code import EmailVerificationHandler
        
        # 示例配置 -QW
        config = {
            'imap': {
                'server': 'imap.gmail.com',
                'port': 993,
                'username': 'your_email@gmail.com',
                'password': 'your_app_password'
            },
            'delete_after_read': False
        }
        
        print("创建邮箱验证码处理器...")
        handler = EmailVerificationHandler(config)
        
        print("测试邮箱类型检测:")
        test_emails = [
            'test@gmail.com',
            'test@tempmail.plus',
            'test@10minutemail.com'
        ]
        
        for email in test_emails:
            is_temp = handler._is_temp_mail(email)
            print(f"   {email}: {'临时邮箱' if is_temp else '普通邮箱'}")
        
        print(f"\nIMAP配置状态: {'已配置' if handler._is_imap_configured() else '未配置'}")
        print("注意：实际使用时需要配置真实的IMAP信息")
        
    except Exception as e:
        print(f"❌ 示例执行失败: {str(e)}")


def example_browser_management():
    """示例：浏览器管理 -QW"""
    print("\n" + "=" * 50)
    print("🌐 示例：浏览器管理")
    print("=" * 50)
    
    try:
        from .browser_utils import BrowserManager, get_default_user_agent
        
        print("创建浏览器管理器...")
        manager = BrowserManager()
        
        print("检测自动化库可用性:")
        print(f"   DrissionPage: {'可用' if manager._is_drission_page_available() else '不可用'}")
        print(f"   Selenium: {'可用' if manager._is_selenium_available() else '不可用'}")
        
        print(f"\n默认User-Agent:")
        print(f"   {get_default_user_agent()}")
        
        print("\n注意：实际使用浏览器需要安装相应的自动化库")
        
    except Exception as e:
        print(f"❌ 示例执行失败: {str(e)}")


def run_all_examples():
    """运行所有示例 -QW"""
    print("🎯 运行AugmentPage所有示例")
    print("这将演示各种功能的使用方法\n")
    
    examples = [
        example_basic_ide_detection,
        example_device_code_generation,
        example_path_utilities,
        example_telemetry_modification,
        example_workspace_cleanup,
        example_jetbrains_handling,
        example_email_verification,
        example_browser_management
    ]
    
    for i, example_func in enumerate(examples, 1):
        try:
            print(f"\n[{i}/{len(examples)}] ", end="")
            example_func()
            time.sleep(1)  # 短暂暂停以便阅读
        except KeyboardInterrupt:
            print("\n\n⏹️ 用户中断，示例演示结束")
            break
        except Exception as e:
            print(f"\n❌ 示例 {example_func.__name__} 执行失败: {str(e)}")
    
    print("\n" + "=" * 50)
    print("✅ 所有示例演示完成")
    print("=" * 50)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AugmentPage 使用示例")
    parser.add_argument("--all", action="store_true", help="运行所有示例")
    parser.add_argument("--ide", action="store_true", help="IDE检测示例")
    parser.add_argument("--codes", action="store_true", help="设备代码生成示例")
    parser.add_argument("--paths", action="store_true", help="路径工具示例")
    parser.add_argument("--telemetry", action="store_true", help="遥测修改示例")
    parser.add_argument("--workspace", action="store_true", help="工作区清理示例")
    parser.add_argument("--jetbrains", action="store_true", help="JetBrains处理示例")
    parser.add_argument("--email", action="store_true", help="邮箱验证码示例")
    parser.add_argument("--browser", action="store_true", help="浏览器管理示例")
    
    args = parser.parse_args()
    
    if args.all:
        run_all_examples()
    elif args.ide:
        example_basic_ide_detection()
    elif args.codes:
        example_device_code_generation()
    elif args.paths:
        example_path_utilities()
    elif args.telemetry:
        example_telemetry_modification()
    elif args.workspace:
        example_workspace_cleanup()
    elif args.jetbrains:
        example_jetbrains_handling()
    elif args.email:
        example_email_verification()
    elif args.browser:
        example_browser_management()
    else:
        # 默认运行安全的示例 -QW
        print("🎯 运行默认示例（安全模式）...")
        example_basic_ide_detection()
        example_device_code_generation()
        example_path_utilities()
