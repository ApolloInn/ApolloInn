#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
邮箱验证码获取工具
支持IMAP和临时邮箱两种方式自动获取验证码
支持跨平台（Windows、macOS、Linux）
-QW
"""

import logging
import time
import re
import email
import imaplib
import requests
from typing import Optional, Dict, Any, Tuple


class EmailVerificationHandler:
    """邮箱验证码处理器 -QW"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化邮箱验证码处理器
        
        Args:
            config: 配置字典，包含IMAP和临时邮箱配置
        """
        self.config = config or {}
        self.session = requests.Session()
        
        # 设置请求头 -QW
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        print("[邮箱验证码] 初始化完成")
    
    def get_verification_code(self, email_address: str, timeout: int = 60) -> Optional[str]:
        """
        获取验证码的主要方法
        
        Args:
            email_address: 邮箱地址
            timeout: 超时时间（秒）
            
        Returns:
            Optional[str]: 验证码，如果获取失败返回None
        """
        print(f"[邮箱验证码] 开始获取验证码，邮箱: {email_address}")
        
        try:
            # 判断使用哪种方式获取验证码 -QW
            if self._is_imap_configured():
                print("[邮箱验证码] 使用IMAP方式获取验证码")
                return self._get_mail_code_by_imap(email_address, timeout)
            elif self._is_temp_mail(email_address):
                print("[邮箱验证码] 使用临时邮箱方式获取验证码")
                return self._get_temp_mail_code(email_address, timeout)
            else:
                print("[邮箱验证码] ⚠️ 不支持的邮箱类型，请手动输入验证码")
                return self._get_manual_input_code()
                
        except Exception as e:
            print(f"[邮箱验证码] ❌ 获取验证码失败: {str(e)}")
            return None
    
    def _is_imap_configured(self) -> bool:
        """检查是否配置了IMAP -QW"""
        imap_config = self.config.get('imap', {})
        required_fields = ['server', 'port', 'username', 'password']
        return all(imap_config.get(field) for field in required_fields)
    
    def _is_temp_mail(self, email_address: str) -> bool:
        """检查是否为临时邮箱 -QW"""
        temp_mail_domains = [
            'tempmail.plus',
            '10minutemail.com',
            'guerrillamail.com',
            'mailinator.com',
            'temp-mail.org'
        ]
        
        domain = email_address.split('@')[-1].lower()
        return domain in temp_mail_domains
    
    def _get_mail_code_by_imap(self, email_address: str, timeout: int) -> Optional[str]:
        """使用IMAP获取验证码 -QW"""
        imap_config = self.config.get('imap', {})
        
        start_time = time.time()
        retry_count = 0
        max_retries = timeout // 3  # 每3秒重试一次
        
        while retry_count < max_retries:
            try:
                if retry_count > 0:
                    time.sleep(3)
                
                print(f"[邮箱验证码] IMAP尝试 {retry_count + 1}/{max_retries}")
                
                # 连接到IMAP服务器 -QW
                mail = imaplib.IMAP4_SSL(
                    imap_config['server'], 
                    imap_config.get('port', 993)
                )
                mail.login(imap_config['username'], imap_config['password'])
                mail.select(imap_config.get('folder', 'INBOX'))
                
                # 搜索来自Cursor的邮件 -QW
                search_criteria = f'FROM "no-reply@cursor.sh" TO "{email_address}"'
                status, messages = mail.search(None, search_criteria)
                
                if status != 'OK':
                    mail.logout()
                    retry_count += 1
                    continue
                
                mail_ids = messages[0].split()
                if not mail_ids:
                    mail.logout()
                    retry_count += 1
                    continue
                
                # 获取最新邮件 -QW
                latest_mail_id = mail_ids[-1]
                status, msg_data = mail.fetch(latest_mail_id, '(RFC822)')
                
                if status != 'OK':
                    mail.logout()
                    retry_count += 1
                    continue
                
                # 解析邮件内容 -QW
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)
                
                # 提取邮件正文 -QW
                body = self._extract_email_body(email_message)
                if body:
                    # 查找6位数字验证码 -QW
                    code_match = re.search(r"\b\d{6}\b", body)
                    if code_match:
                        code = code_match.group()
                        
                        # 删除邮件（可选） -QW
                        if self.config.get('delete_after_read', False):
                            mail.store(latest_mail_id, '+FLAGS', '\\Deleted')
                            mail.expunge()
                        
                        mail.logout()
                        print(f"[邮箱验证码] ✅ IMAP获取验证码成功: {code}")
                        return code
                
                mail.logout()
                retry_count += 1
                
            except Exception as e:
                print(f"[邮箱验证码] ⚠️ IMAP尝试失败: {str(e)}")
                retry_count += 1
                
                if time.time() - start_time > timeout:
                    break
        
        print("[邮箱验证码] ❌ IMAP获取验证码超时")
        return None
    
    def _get_temp_mail_code(self, email_address: str, timeout: int) -> Optional[str]:
        """使用临时邮箱API获取验证码 -QW"""
        if 'tempmail.plus' not in email_address:
            print("[邮箱验证码] ⚠️ 目前只支持tempmail.plus临时邮箱")
            return None
        
        # 解析邮箱地址 -QW
        username, domain = email_address.split('@')
        
        start_time = time.time()
        retry_count = 0
        max_retries = timeout // 2  # 每2秒重试一次
        
        while retry_count < max_retries:
            try:
                if retry_count > 0:
                    time.sleep(2)
                
                print(f"[邮箱验证码] 临时邮箱尝试 {retry_count + 1}/{max_retries}")
                
                # 获取邮件列表 -QW
                mail_list_url = f"https://tempmail.plus/api/mails"
                params = {
                    'email': email_address,
                    'limit': 10
                }
                
                response = self.session.get(mail_list_url, params=params, timeout=10)
                response.raise_for_status()
                
                mail_list_data = response.json()
                
                if not mail_list_data.get("result"):
                    retry_count += 1
                    continue
                
                # 查找来自Cursor的邮件 -QW
                mails = mail_list_data.get("mails", [])
                cursor_mail = None
                
                for mail_item in mails:
                    if "cursor.sh" in mail_item.get("from", "").lower():
                        cursor_mail = mail_item
                        break
                
                if not cursor_mail:
                    retry_count += 1
                    continue
                
                # 获取邮件详情 -QW
                mail_id = cursor_mail.get("id")
                if not mail_id:
                    retry_count += 1
                    continue
                
                mail_detail_url = f"https://tempmail.plus/api/mails/{mail_id}"
                detail_response = self.session.get(mail_detail_url, params={'email': email_address}, timeout=10)
                detail_response.raise_for_status()
                
                mail_detail_data = detail_response.json()
                
                if not mail_detail_data.get("result"):
                    retry_count += 1
                    continue
                
                # 从邮件文本中提取验证码 -QW
                mail_text = mail_detail_data.get("text", "")
                code_match = re.search(r"(?<![a-zA-Z@.])\b\d{6}\b", mail_text)
                
                if code_match:
                    code = code_match.group()
                    
                    # 清理邮件（可选） -QW
                    if self.config.get('delete_after_read', False):
                        self._cleanup_temp_mail(email_address, mail_id)
                    
                    print(f"[邮箱验证码] ✅ 临时邮箱获取验证码成功: {code}")
                    return code
                
                retry_count += 1
                
            except Exception as e:
                print(f"[邮箱验证码] ⚠️ 临时邮箱尝试失败: {str(e)}")
                retry_count += 1
                
                if time.time() - start_time > timeout:
                    break
        
        print("[邮箱验证码] ❌ 临时邮箱获取验证码超时")
        return None
    
    def _get_manual_input_code(self) -> Optional[str]:
        """手动输入验证码 -QW"""
        try:
            print("\n" + "="*50)
            print("📧 请手动获取验证码")
            print("="*50)
            print("1. 请检查您的邮箱")
            print("2. 查找来自 no-reply@cursor.sh 的邮件")
            print("3. 复制邮件中的6位数字验证码")
            print("="*50)
            
            while True:
                code = input("请输入6位验证码（输入'q'退出）: ").strip()
                
                if code.lower() == 'q':
                    return None
                
                if re.match(r'^\d{6}$', code):
                    print(f"[邮箱验证码] ✅ 手动输入验证码: {code}")
                    return code
                else:
                    print("❌ 请输入6位数字验证码")
                    
        except KeyboardInterrupt:
            print("\n[邮箱验证码] 用户取消输入")
            return None

    def _extract_email_body(self, email_message) -> str:
        """提取邮件正文 -QW"""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            body = part.get_payload(decode=True).decode(charset, errors='ignore')
                            return body
                        except Exception as e:
                            print(f"[邮箱验证码] ⚠️ 解码邮件正文失败: {e}")
            else:
                content_type = email_message.get_content_type()
                if content_type == "text/plain":
                    charset = email_message.get_content_charset() or 'utf-8'
                    try:
                        body = email_message.get_payload(decode=True).decode(charset, errors='ignore')
                        return body
                    except Exception as e:
                        print(f"[邮箱验证码] ⚠️ 解码邮件正文失败: {e}")
        except Exception as e:
            print(f"[邮箱验证码] ⚠️ 提取邮件正文失败: {e}")

        return ""

    def _cleanup_temp_mail(self, email_address: str, mail_id: str) -> bool:
        """清理临时邮件 -QW"""
        try:
            delete_url = "https://tempmail.plus/api/mails/"
            payload = {
                "email": email_address,
                "first_id": mail_id,
            }

            # 最多尝试3次 -QW
            for attempt in range(3):
                response = self.session.delete(delete_url, data=payload, timeout=10)
                try:
                    result = response.json().get("result")
                    if result is True:
                        print(f"[邮箱验证码] ✅ 临时邮件清理成功")
                        return True
                except:
                    pass

                if attempt < 2:  # 不是最后一次尝试
                    time.sleep(1)

            print(f"[邮箱验证码] ⚠️ 临时邮件清理失败")
            return False

        except Exception as e:
            print(f"[邮箱验证码] ⚠️ 临时邮件清理异常: {str(e)}")
            return False


def create_email_handler(config: Optional[Dict[str, Any]] = None) -> EmailVerificationHandler:
    """创建邮箱验证码处理器的便捷函数 -QW"""
    return EmailVerificationHandler(config)


def get_cursor_verification_code(email_address: str, config: Optional[Dict[str, Any]] = None, timeout: int = 60) -> Optional[str]:
    """
    获取Cursor验证码的便捷函数 -QW

    Args:
        email_address: 邮箱地址
        config: 配置字典
        timeout: 超时时间（秒）

    Returns:
        Optional[str]: 验证码，如果获取失败返回None
    """
    handler = EmailVerificationHandler(config)
    return handler.get_verification_code(email_address, timeout)


def test_email_handler():
    """测试邮箱验证码处理器 -QW"""
    print("=== 邮箱验证码处理器测试 ===")

    # 示例配置 -QW
    test_config = {
        'imap': {
            'server': 'imap.gmail.com',
            'port': 993,
            'username': 'your_email@gmail.com',
            'password': 'your_app_password',
            'folder': 'INBOX'
        },
        'delete_after_read': False
    }

    handler = EmailVerificationHandler(test_config)

    # 测试邮箱类型检测 -QW
    test_emails = [
        'test@gmail.com',
        'test@tempmail.plus',
        'test@10minutemail.com'
    ]

    for email_addr in test_emails:
        print(f"\n测试邮箱: {email_addr}")
        print(f"  是否为临时邮箱: {handler._is_temp_mail(email_addr)}")

    print(f"\nIMAP配置状态: {handler._is_imap_configured()}")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    # 运行测试 -QW
    test_email_handler()

    # 示例使用 -QW
    print("\n=== 示例使用 ===")

    # 配置示例 -QW
    config = {
        'imap': {
            'server': 'imap.gmail.com',
            'port': 993,
            'username': 'your_email@gmail.com',
            'password': 'your_app_password'
        },
        'delete_after_read': False
    }

    # 获取验证码 -QW
    email_address = input("请输入邮箱地址: ").strip()
    if email_address:
        code = get_cursor_verification_code(email_address, config, timeout=60)
        if code:
            print(f"✅ 获取到验证码: {code}")
        else:
            print("❌ 未能获取到验证码")
    else:
        print("未输入邮箱地址")
