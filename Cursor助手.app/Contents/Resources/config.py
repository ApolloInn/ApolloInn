#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
应用程序配置文件
包含标签页开关、历史账号显示限制等配置项
-QW
"""

# ====================================================================
# 应用程序版本信息
# ====================================================================

# 应用程序版本号
# 格式: 主版本.次版本.修订版本
APP_VERSION = "8.1.2"

# ====================================================================
# 标签页开关配置
# ====================================================================

# Cursor标签页 (原有的Cursor登录助手功能)
# 1=开启, 0=关闭
CURSOR_TAB_ENABLED = 1

# Augment标签页 (新增的Augment功能)  
# 1=开启, 0=关闭
AUGMENT_TAB_ENABLED = 0

# cursor账号标签页 (cursor账号管理功能)
# 1=开启, 0=关闭
# 注意: 已关闭，被历史账号标签页替代
CURSOR_ACCOUNT_TAB_ENABLED = 0

# 历史账号标签页 (Pro历史账号管理功能)
# 1=开启, 0=关闭
# 从sc_email_token_30表获取历史账号，status=888为pro未使用，status=999为已使用
HISTORY_ACCOUNT_TAB_ENABLED = 1

# Windsurf标签页 (Windsurf功能)
# 1=开启, 0=关闭
# 注意: 仅Auto账号类型显示，Pro账号类型自动隐藏
WINDSURF_TAB_ENABLED = 0

# ====================================================================
# 历史账号显示配置
# ====================================================================

# 历史账号下拉列表显示数量限制
# 范围: 1-100
# 默认: 12
# 说明: 控制cursor账号标签页中历史账号下拉框显示的最大账号数量
#       设置过大可能影响界面性能，建议保持在20以内
HISTORY_ACCOUNT_DISPLAY_LIMIT = 20

# ====================================================================
# 验证码获取配置
# ====================================================================

# 验证码获取前的准备等待时间 (秒)
# 范围: 10-60
# 默认: 30
# 说明: 用户确认已发送验证码后，等待多少秒再开始获取验证码
#       给用户足够时间确保验证码已发送，避免过早获取导致失败
VERIFICATION_CODE_PREPARE_COUNTDOWN = 20

# 验证码显示自动清空时间 (秒)
# 范围: 15-120
# 默认: 30
# 说明: 验证码获取成功后，多少秒后自动清空显示框中的验证码
#       提高安全性，防止验证码长时间显示在界面上
VERIFICATION_CODE_AUTO_CLEAR_TIME = 30

# ====================================================================
# 其他配置 (预留扩展)
# ====================================================================

# API请求超时时间 (秒)
API_TIMEOUT = 15

# 自动刷新间隔 (秒)
AUTO_REFRESH_INTERVAL = 300

# 日志级别 
# DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = "INFO"

# ====================================================================
# 配置验证函数
# ====================================================================

def validate_config():
    """验证配置参数的有效性"""
    errors = []
    
    # 验证版本号格式
    import re
    if not isinstance(APP_VERSION, str):
        errors.append("APP_VERSION 必须是字符串")
    elif not re.match(r'^\d+\.\d+\.\d+$', APP_VERSION):
        errors.append("APP_VERSION 格式必须是 x.y.z (如: 8.0.3)")
    
    # 验证标签页开关
    for var_name, var_value in [
        ("CURSOR_TAB_ENABLED", CURSOR_TAB_ENABLED),
        ("AUGMENT_TAB_ENABLED", AUGMENT_TAB_ENABLED), 
        ("CURSOR_ACCOUNT_TAB_ENABLED", CURSOR_ACCOUNT_TAB_ENABLED),
        ("HISTORY_ACCOUNT_TAB_ENABLED", HISTORY_ACCOUNT_TAB_ENABLED),
        ("WINDSURF_TAB_ENABLED", WINDSURF_TAB_ENABLED)
    ]:
        if var_value not in [0, 1]:
            errors.append(f"{var_name} 必须是 0 或 1")
    
    # 验证历史账号显示限制
    if not isinstance(HISTORY_ACCOUNT_DISPLAY_LIMIT, int):
        errors.append("HISTORY_ACCOUNT_DISPLAY_LIMIT 必须是整数")
    elif not (1 <= HISTORY_ACCOUNT_DISPLAY_LIMIT <= 100):
        errors.append("HISTORY_ACCOUNT_DISPLAY_LIMIT 必须在 1-100 之间")
    
    # 验证验证码准备倒计时
    if not isinstance(VERIFICATION_CODE_PREPARE_COUNTDOWN, int):
        errors.append("VERIFICATION_CODE_PREPARE_COUNTDOWN 必须是整数")
    elif not (10 <= VERIFICATION_CODE_PREPARE_COUNTDOWN <= 60):
        errors.append("VERIFICATION_CODE_PREPARE_COUNTDOWN 必须在 10-60 之间")
    
    # 验证验证码自动清空时间
    if not isinstance(VERIFICATION_CODE_AUTO_CLEAR_TIME, int):
        errors.append("VERIFICATION_CODE_AUTO_CLEAR_TIME 必须是整数")
    elif not (15 <= VERIFICATION_CODE_AUTO_CLEAR_TIME <= 120):
        errors.append("VERIFICATION_CODE_AUTO_CLEAR_TIME 必须在 15-120 之间")
    
    # 验证API超时时间
    if not isinstance(API_TIMEOUT, (int, float)) or API_TIMEOUT <= 0:
        errors.append("API_TIMEOUT 必须是正数")
    
    return errors

def get_config_dict():
    """获取配置字典格式（用于兼容旧代码）"""
    return {
        'app_version': APP_VERSION,
        'cursor': CURSOR_TAB_ENABLED,
        'augment': AUGMENT_TAB_ENABLED,
        'cursor_account': CURSOR_ACCOUNT_TAB_ENABLED,
        'history_account': HISTORY_ACCOUNT_TAB_ENABLED,
        'windsurf': WINDSURF_TAB_ENABLED,
        'history_account_display_limit': HISTORY_ACCOUNT_DISPLAY_LIMIT,
        'verification_code_prepare_countdown': VERIFICATION_CODE_PREPARE_COUNTDOWN,
        'verification_code_auto_clear_time': VERIFICATION_CODE_AUTO_CLEAR_TIME
    }

# ====================================================================
# 配置说明
# ====================================================================

"""
配置文件使用说明:

1. 修改配置后需要重启应用程序才能生效
2. 版本号格式: x.y.z (主版本.次版本.修订版本)
3. 标签页开关: 1=开启, 0=关闭
4. 历史账号显示限制建议设置为 5-20 之间
5. 验证码准备倒计时建议设置为 20-40 秒之间
6. API超时时间不建议设置过小，可能导致请求失败
7. 如果配置出现问题，可以删除此文件让程序使用默认配置

常用配置组合:
- 只使用Cursor功能: CURSOR_TAB_ENABLED=1, 其他=0
- 完整功能: 全部设为1
- 测试模式: AUGMENT_TAB_ENABLED=1, CURSOR_ACCOUNT_TAB_ENABLED=1

版本号说明:
- 主版本号变更: 重大功能更新或架构变更
- 次版本号变更: 新功能添加
- 修订版本号变更: 错误修复和小改进
"""
