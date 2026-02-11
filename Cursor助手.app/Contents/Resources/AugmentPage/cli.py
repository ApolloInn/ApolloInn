#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AugmentPage 命令行界面
提供完整的命令行操作界面
支持跨平台（Windows、macOS、Linux）
-QW
"""

import sys
import os
import argparse
import json
import time
from typing import Dict, Any, List
from pathlib import Path


class AugmentPageCLI:
    """AugmentPage 命令行界面 -QW"""
    
    def __init__(self):
        self.adapter = None
        self._init_adapter()
    
    def _init_adapter(self):
        """初始化适配器 -QW"""
        try:
            from .adapter import get_adapter
            self.adapter = get_adapter()
            print("✅ AugmentPage 适配器初始化成功")
        except Exception as e:
            print(f"❌ 适配器初始化失败: {str(e)}")
            sys.exit(1)
    
    def cmd_status(self, args):
        """显示系统状态 -QW"""
        print("🔍 获取系统状态...")
        
        try:
            # 获取系统信息 -QW
            system_info = self.adapter.get_system_info()
            print(f"\n🖥️  系统信息:")
            print(f"   系统: {system_info['system']}")
            print(f"   平台: {system_info['platform']}")
            print(f"   架构: {system_info['machine']}")
            print(f"   Python: {system_info['python_version']}")
            
            # 测试模块 -QW
            modules = self.adapter.test_modules()
            available = sum(1 for status in modules.values() if status)
            print(f"\n📦 模块状态: {available}/{len(modules)} 可用")
            
            if args.verbose:
                for module, status in modules.items():
                    icon = "✅" if status else "❌"
                    print(f"   {icon} {module}")
            
        except Exception as e:
            print(f"❌ 获取系统状态失败: {str(e)}")
    
    def cmd_detect(self, args):
        """检测IDE -QW"""
        print("🔍 检测系统中的IDE...")
        
        try:
            result = self.adapter.detect_ides()
            
            if result["success"]:
                print(f"✅ 检测成功，找到 {result['count']} 个IDE:")
                
                for ide in result["ides"]:
                    print(f"\n{ide['icon']} {ide['display_name']}")
                    print(f"   类型: {ide['ide_type']}")
                    if args.verbose and ide.get('config_path'):
                        print(f"   路径: {ide['config_path']}")
                
                # 保存结果到文件 -QW
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"\n💾 结果已保存到: {args.output}")
            else:
                print(f"❌ 检测失败: {result.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"❌ IDE检测失败: {str(e)}")
    
    def cmd_generate(self, args):
        """生成设备代码 -QW"""
        print("🔢 生成设备代码...")
        
        try:
            result = self.adapter.generate_device_codes()
            
            if result["success"]:
                print(f"✅ 生成成功，共 {result['count']} 个代码:")
                
                for key, value in result["ids"].items():
                    if args.verbose:
                        print(f"   {key}: {value}")
                    else:
                        print(f"   {key}: {value[:8]}...")
                
                # 保存结果到文件 -QW
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result["ids"], f, indent=2, ensure_ascii=False)
                    print(f"\n💾 代码已保存到: {args.output}")
            else:
                print(f"❌ 生成失败: {result.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 设备代码生成失败: {str(e)}")
    
    def cmd_modify(self, args):
        """修改遥测ID -QW"""
        ide_name = args.ide
        print(f"📡 修改 {ide_name} 遥测ID...")
        
        # 安全确认 -QW
        if not args.force:
            print(f"⚠️  警告: 这将修改 {ide_name} 的配置文件")
            print("   操作前会自动创建备份")
            confirm = input("是否继续? (y/N): ").strip().lower()
            if confirm != 'y':
                print("操作已取消")
                return
        
        try:
            result = self.adapter.modify_telemetry_only(ide_name)
            
            if result["success"]:
                print("✅ 遥测ID修改成功")
                if args.verbose and "data" in result:
                    data = result["data"]
                    if "new_ids" in data:
                        print("新生成的ID:")
                        for key, value in data["new_ids"].items():
                            print(f"   {key}: {value}")
            else:
                print(f"❌ 修改失败: {result.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 遥测ID修改失败: {str(e)}")
    
    def cmd_clean(self, args):
        """清理工作区 -QW"""
        ide_name = args.ide
        print(f"🗂️ 清理 {ide_name} 工作区...")
        
        # 安全确认 -QW
        if not args.force:
            print(f"⚠️  警告: 这将删除 {ide_name} 工作区中的所有文件")
            print("   操作前会自动创建备份")
            confirm = input("是否继续? (y/N): ").strip().lower()
            if confirm != 'y':
                print("操作已取消")
                return
        
        try:
            result = self.adapter.clean_workspace_only(ide_name)
            
            if result["success"]:
                print("✅ 工作区清理成功")
                if args.verbose and "data" in result:
                    data = result["data"]
                    if "backup_path" in data:
                        print(f"备份路径: {data['backup_path']}")
                    if "deleted_files_count" in data:
                        print(f"删除文件数: {data['deleted_files_count']}")
            else:
                print(f"❌ 清理失败: {result.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 工作区清理失败: {str(e)}")
    
    def cmd_cleanup(self, args):
        """完整清理 -QW"""
        ide_name = args.ide
        print(f"🧹 完整清理 {ide_name}...")
        
        # 安全确认 -QW
        if not args.force:
            print(f"⚠️  警告: 这将执行 {ide_name} 的完整清理操作")
            print("   包括: 遥测ID重置、工作区清理、数据库清理")
            print("   操作前会自动创建备份")
            confirm = input("是否继续? (y/N): ").strip().lower()
            if confirm != 'y':
                print("操作已取消")
                return
        
        try:
            result = self.adapter.cleanup_ide_data(ide_name)
            
            if result["success"]:
                print("✅ 完整清理成功")
                if args.verbose:
                    print("清理详情:")
                    for key, value in result.items():
                        if key not in ["success", "message"]:
                            print(f"   {key}: {value}")
            else:
                print(f"❌ 清理失败: {result.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 完整清理失败: {str(e)}")
    
    def cmd_paths(self, args):
        """显示路径信息 -QW"""
        ide_name = args.ide
        print(f"📁 获取 {ide_name} 路径信息...")
        
        try:
            result = self.adapter.get_ide_paths(ide_name)
            
            if result["success"]:
                print(f"✅ {ide_name} 路径信息:")
                for key, info in result["paths"].items():
                    status = "存在" if info["exists"] else "不存在"
                    print(f"   {key}: {status}")
                    if args.verbose:
                        print(f"      路径: {info['path']}")
            else:
                print(f"❌ 获取失败: {result.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 路径信息获取失败: {str(e)}")
    
    def cmd_test(self, args):
        """运行测试 -QW"""
        print("🧪 运行AugmentPage测试...")
        
        try:
            if args.quick:
                from .test_suite import run_quick_test
                success = run_quick_test()
                print(f"\n{'✅' if success else '❌'} 快速测试{'通过' if success else '失败'}")
            else:
                from .test_suite import run_full_test
                report = run_full_test()
                success_rate = report["summary"]["success_rate"]
                print(f"\n📊 完整测试完成，成功率: {success_rate:.1f}%")
                
        except Exception as e:
            print(f"❌ 测试运行失败: {str(e)}")
    
    def cmd_demo(self, args):
        """运行演示 -QW"""
        print("📚 运行AugmentPage演示...")
        
        try:
            if args.advanced:
                from .examples import demo_advanced_usage
                demo_advanced_usage()
            else:
                from .examples import demo_basic_usage
                demo_basic_usage()
                
        except Exception as e:
            print(f"❌ 演示运行失败: {str(e)}")
    
    def run(self):
        """运行CLI -QW"""
        parser = argparse.ArgumentParser(
            description="AugmentPage - 跨平台IDE管理工具",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
  %(prog)s status                    # 显示系统状态
  %(prog)s detect -v                 # 检测IDE（详细模式）
  %(prog)s generate -o codes.json    # 生成设备代码并保存
  %(prog)s modify Cursor             # 修改Cursor遥测ID
  %(prog)s clean Cursor              # 清理Cursor工作区
  %(prog)s cleanup Cursor --force    # 完整清理Cursor（强制）
  %(prog)s test --quick              # 运行快速测试
  %(prog)s demo --advanced           # 运行高级演示
            """
        )
        
        # 全局选项 -QW
        parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
        parser.add_argument("--version", action="version", version="AugmentPage 2.0.0")
        
        # 子命令 -QW
        subparsers = parser.add_subparsers(dest="command", help="可用命令")
        
        # status命令 -QW
        status_parser = subparsers.add_parser("status", help="显示系统状态")
        status_parser.set_defaults(func=self.cmd_status)
        
        # detect命令 -QW
        detect_parser = subparsers.add_parser("detect", help="检测IDE")
        detect_parser.add_argument("-o", "--output", help="保存结果到文件")
        detect_parser.set_defaults(func=self.cmd_detect)
        
        # generate命令 -QW
        generate_parser = subparsers.add_parser("generate", help="生成设备代码")
        generate_parser.add_argument("-o", "--output", help="保存代码到文件")
        generate_parser.set_defaults(func=self.cmd_generate)
        
        # modify命令 -QW
        modify_parser = subparsers.add_parser("modify", help="修改遥测ID")
        modify_parser.add_argument("ide", help="IDE名称 (如: Cursor, VSCode)")
        modify_parser.add_argument("--force", action="store_true", help="强制执行，跳过确认")
        modify_parser.set_defaults(func=self.cmd_modify)
        
        # clean命令 -QW
        clean_parser = subparsers.add_parser("clean", help="清理工作区")
        clean_parser.add_argument("ide", help="IDE名称 (如: Cursor, VSCode)")
        clean_parser.add_argument("--force", action="store_true", help="强制执行，跳过确认")
        clean_parser.set_defaults(func=self.cmd_clean)
        
        # cleanup命令 -QW
        cleanup_parser = subparsers.add_parser("cleanup", help="完整清理")
        cleanup_parser.add_argument("ide", help="IDE名称 (如: Cursor, VSCode)")
        cleanup_parser.add_argument("--force", action="store_true", help="强制执行，跳过确认")
        cleanup_parser.set_defaults(func=self.cmd_cleanup)
        
        # paths命令 -QW
        paths_parser = subparsers.add_parser("paths", help="显示路径信息")
        paths_parser.add_argument("ide", help="IDE名称 (如: Cursor, VSCode)")
        paths_parser.set_defaults(func=self.cmd_paths)
        
        # test命令 -QW
        test_parser = subparsers.add_parser("test", help="运行测试")
        test_parser.add_argument("--quick", action="store_true", help="运行快速测试")
        test_parser.set_defaults(func=self.cmd_test)
        
        # demo命令 -QW
        demo_parser = subparsers.add_parser("demo", help="运行演示")
        demo_parser.add_argument("--advanced", action="store_true", help="运行高级演示")
        demo_parser.set_defaults(func=self.cmd_demo)
        
        # 解析参数 -QW
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
        
        # 执行命令 -QW
        try:
            args.func(args)
        except KeyboardInterrupt:
            print("\n⏹️ 操作被用户中断")
        except Exception as e:
            print(f"\n❌ 命令执行失败: {str(e)}")
            if args.verbose:
                import traceback
                traceback.print_exc()


def main():
    """CLI入口点 -QW"""
    cli = AugmentPageCLI()
    cli.run()


if __name__ == "__main__":
    main()
