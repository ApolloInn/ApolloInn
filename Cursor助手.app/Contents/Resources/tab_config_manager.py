#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
标签页配置管理器
用于管理三个标签页的开关状态和其他配置项
支持Python配置文件和命令行操作
-QW
"""

import os
import sys
import importlib.util


class TabConfigManager:
    """标签页配置管理器类 -QW"""
    
    def __init__(self, config_file="config.py"):
        self.config_file = config_file
        self.default_config = {
            'cursor': 1,      # Cursor标签页（默认开启）
            'augment': 0,     # Augment标签页（默认关闭）
            'cursor_account': 0,  # cursor账号标签页（已关闭）
            'history_account': 1,  # 历史账号标签页（默认开启）
            'history_account_display_limit': 12  # 历史账号显示数量限制（默认12个）
        }
    
    def load_config(self):
        """加载Python配置文件 -QW"""
        try:
            if os.path.exists(self.config_file):
                # 动态导入配置模块
                spec = importlib.util.spec_from_file_location("config", self.config_file)
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                
                # 验证配置
                if hasattr(config_module, 'validate_config'):
                    errors = config_module.validate_config()
                    if errors:
                        print(f"⚠️ 配置验证失败: {'; '.join(errors)}")
                        print("使用默认配置")
                        return self.default_config
                
                # 获取配置字典
                if hasattr(config_module, 'get_config_dict'):
                    config = config_module.get_config_dict()
                else:
                    # 手动构建配置字典
                    config = {
                        'cursor': getattr(config_module, 'CURSOR_TAB_ENABLED', 1),
                        'augment': getattr(config_module, 'AUGMENT_TAB_ENABLED', 0),
                        'cursor_account': getattr(config_module, 'CURSOR_ACCOUNT_TAB_ENABLED', 0),
                        'history_account': getattr(config_module, 'HISTORY_ACCOUNT_TAB_ENABLED', 1),
                        'history_account_display_limit': getattr(config_module, 'HISTORY_ACCOUNT_DISPLAY_LIMIT', 12)
                    }
                
                print(f"✅ Python配置加载成功: {config}")
                return config
            else:
                print("⚠️ 配置文件不存在，使用默认配置")
                self._create_default_config_file()
                return self.default_config
        except Exception as e:
            print(f"❌ 配置加载失败: {e}")
            return self.default_config
    
    def _create_default_config_file(self):
        """创建默认配置文件 -QW"""
        # 如果config.py不存在，复制默认的config.py
        if not os.path.exists(self.config_file):
            # 这里可以创建配置文件，但为了简单，我们让用户手动创建
            print(f"请确保 {self.config_file} 文件存在")
    
    def save_config(self, config):
        """保存配置到Python文件 -QW"""
        try:
            # 读取现有配置文件内容
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 更新配置值
                import re
                
                # 更新各个配置项
                config_mappings = {
                    'cursor': 'CURSOR_TAB_ENABLED',
                    'augment': 'AUGMENT_TAB_ENABLED', 
                    'cursor_account': 'CURSOR_ACCOUNT_TAB_ENABLED',
                    'history_account': 'HISTORY_ACCOUNT_TAB_ENABLED',
                    'history_account_display_limit': 'HISTORY_ACCOUNT_DISPLAY_LIMIT'
                }
                
                for key, var_name in config_mappings.items():
                    if key in config:
                        pattern = f'({var_name}\\s*=\\s*)\\d+'
                        replacement = f'\\g<1>{config[key]}'
                        content = re.sub(pattern, replacement, content)
                
                # 写回文件
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ Python配置保存成功: {config}")
                return True
            else:
                print(f"❌ 配置文件 {self.config_file} 不存在")
                return False
        except Exception as e:
            print(f"❌ 配置保存失败: {e}")
            return False
    
    def set_tab_switch(self, tab_name, enabled):
        """设置标签页开关 -QW"""
        config = self.load_config()
        
        if tab_name not in config:
            print(f"❌ 未知的标签页名称: {tab_name}")
            print(f"可用的标签页: {list(config.keys())}")
            return False
        
        config[tab_name] = int(enabled)
        return self.save_config(config)
    
    def get_tab_switches(self):
        """获取所有标签页开关状态 -QW"""
        return self.load_config()
    
    def get_history_account_display_limit(self):
        """获取历史账号显示数量限制 -QW"""
        config = self.load_config()
        return config.get('history_account_display_limit', 10)  # 默认10个
    
    def set_history_account_display_limit(self, limit):
        """设置历史账号显示数量限制 -QW"""
        config = self.load_config()
        config['history_account_display_limit'] = int(limit)
        return self.save_config(config)
    
    def show_status(self):
        """显示当前状态 -QW"""
        config = self.load_config()
        print("\n📊 当前配置状态:")
        print("=" * 40)
        
        # 显示标签页开关状态
        tab_names = {
            'cursor': 'Cursor标签页',
            'augment': 'Augment标签页', 
            'cursor_account': 'cursor账号标签页',
            'history_account': '历史账号标签页'
        }
        
        print("🔖 标签页开关:")
        for key, value in config.items():
            if key in tab_names:
                status = "🟢 开启" if value else "🔴 关闭"
                name = tab_names[key]
                print(f"  {name}: {status}")
        
        # 显示其他配置项
        print("\n⚙️ 其他配置:")
        history_limit = config.get('history_account_display_limit', 10)
        print(f"  历史账号显示限制: {history_limit} 个")
        
        print("=" * 40)
    
    def reset_to_default(self):
        """重置为默认配置 -QW"""
        print("🔄 重置为默认配置...")
        return self.save_config(self.default_config)


def main():
    """命令行主函数 -QW"""
    manager = TabConfigManager()
    
    if len(sys.argv) == 1:
        # 无参数，显示帮助和当前状态
        print("🎯 标签页配置管理器 (Python配置版)")
        print("\n配置文件: config.py (支持注释和说明)")
        print("\n使用方法:")
        print("  python tab_config_manager.py status                     # 查看状态")
        print("  python tab_config_manager.py set <tab_name> <0|1>      # 设置开关")
        print("  python tab_config_manager.py limit <number>            # 设置历史账号显示限制")
        print("  python tab_config_manager.py reset                     # 重置配置")
        print("\n标签页名称:")
        print("  cursor         # Cursor标签页")
        print("  augment        # Augment标签页")
        print("  cursor_account # cursor账号标签页（已关闭）")
        print("  history_account # 历史账号标签页")
        print("\n示例:")
        print("  python tab_config_manager.py set augment 1             # 开启Augment标签页")
        print("  python tab_config_manager.py set cursor_account 1      # 开启cursor账号标签页")
        print("  python tab_config_manager.py set augment 0             # 关闭Augment标签页")
        print("  python tab_config_manager.py limit 15                  # 设置历史账号限制为15个")
        print("\n注意: 也可以直接编辑 config.py 文件进行配置")
        
        manager.show_status()
        
    elif sys.argv[1] == "status":
        # 显示状态
        manager.show_status()
        
    elif sys.argv[1] == "set" and len(sys.argv) == 4:
        # 设置开关
        tab_name = sys.argv[2]
        enabled = sys.argv[3]
        
        if enabled not in ['0', '1']:
            print("❌ 开关值必须是 0（关闭）或 1（开启）")
            sys.exit(1)
        
        if manager.set_tab_switch(tab_name, enabled):
            manager.show_status()
            
    elif sys.argv[1] == "limit" and len(sys.argv) == 3:
        # 设置历史账号显示限制
        try:
            limit = int(sys.argv[2])
            if limit < 1 or limit > 100:
                print("❌ 限制数量必须在 1-100 之间")
                sys.exit(1)
            
            if manager.set_history_account_display_limit(limit):
                print(f"✅ 历史账号显示限制已设置为 {limit} 个")
                manager.show_status()
        except ValueError:
            print("❌ 限制数量必须是数字")
            sys.exit(1)
        
    elif sys.argv[1] == "reset":
        # 重置配置
        if manager.reset_to_default():
            manager.show_status()
        
    else:
        print("❌ 无效的命令参数")
        print("使用 'python tab_config_manager.py' 查看帮助")
        sys.exit(1)


if __name__ == "__main__":
    main()