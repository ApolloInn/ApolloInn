"""
AugmentPage 设备代码生成工具
提供机器ID和设备ID的生成功能
支持跨平台（Windows、macOS、Linux）
-QW
"""

import uuid
import secrets
import hashlib
import platform
import time


def generate_machine_id() -> str:
    """
    生成随机的64位十六进制字符串作为机器ID -QW
    类似于在bash中使用/dev/urandom，但使用Python的加密函数

    Returns:
        str: 64位十六进制字符串
    """
    # 生成32个随机字节（将变成64个十六进制字符） -QW
    random_bytes = secrets.token_bytes(32)
    # 转换为十六进制字符串 -QW
    machine_id = random_bytes.hex()
    print(f"[设备代码] 生成机器ID: {machine_id[:8]}...{machine_id[-8:]}")
    return machine_id


def generate_device_id() -> str:
    """
    生成随机的UUID v4作为设备ID -QW

    Returns:
        str: 小写的UUID v4字符串，格式为: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        其中x是任意十六进制数字，y是8、9、A或B中的一个
    """
    # 生成随机的UUID v4 -QW
    device_id = str(uuid.uuid4()).lower()
    print(f"[设备代码] 生成设备ID: {device_id}")
    return device_id


def generate_mac_machine_id() -> str:
    """
    生成macOS风格的机器ID（128位十六进制） -QW
    
    Returns:
        str: 128位十六进制字符串
    """
    # 生成64个随机字节（将变成128个十六进制字符） -QW
    random_bytes = secrets.token_bytes(64)
    mac_machine_id = random_bytes.hex()
    print(f"[设备代码] 生成Mac机器ID: {mac_machine_id[:8]}...{mac_machine_id[-8:]}")
    return mac_machine_id


def generate_sqm_id() -> str:
    """
    生成SQM ID（大写UUID格式，带花括号） -QW
    
    Returns:
        str: 格式为 {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX} 的字符串
    """
    sqm_id = "{" + str(uuid.uuid4()).upper() + "}"
    print(f"[设备代码] 生成SQM ID: {sqm_id}")
    return sqm_id


def generate_telemetry_ids() -> dict:
    """
    生成完整的遥测ID集合 -QW
    
    Returns:
        dict: 包含所有遥测ID的字典
    """
    print("[设备代码] 🔄 生成完整的遥测ID集合...")
    
    ids = {
        "telemetry.devDeviceId": generate_device_id(),
        "telemetry.machineId": generate_machine_id(),
        "telemetry.macMachineId": generate_mac_machine_id(),
        "telemetry.sqmId": generate_sqm_id(),
        "storage.serviceMachineId": generate_device_id(),
    }
    
    print(f"[设备代码] ✅ 生成了 {len(ids)} 个遥测ID")
    return ids


def generate_hardware_fingerprint() -> str:
    """
    生成基于硬件信息的指纹（用于更真实的机器ID） -QW
    
    Returns:
        str: 硬件指纹字符串
    """
    try:
        # 收集系统信息 -QW
        system_info = [
            platform.system(),
            platform.machine(),
            platform.processor(),
            str(time.time_ns() % 1000000),  # 时间戳的微秒部分
        ]
        
        # 添加随机盐 -QW
        salt = secrets.token_hex(16)
        system_info.append(salt)
        
        # 生成哈希 -QW
        combined = "|".join(system_info)
        fingerprint = hashlib.sha256(combined.encode()).hexdigest()
        
        print(f"[设备代码] 生成硬件指纹: {fingerprint[:8]}...{fingerprint[-8:]}")
        return fingerprint
        
    except Exception as e:
        print(f"[设备代码] ⚠️ 硬件指纹生成失败，使用随机值: {str(e)}")
        return generate_machine_id()


def generate_realistic_machine_id() -> str:
    """
    生成更真实的机器ID（结合硬件信息和随机性） -QW
    
    Returns:
        str: 真实感的机器ID
    """
    # 获取硬件指纹 -QW
    hardware_fp = generate_hardware_fingerprint()
    
    # 取前32个字符作为基础 -QW
    base = hardware_fp[:32]
    
    # 添加随机后缀 -QW
    random_suffix = secrets.token_hex(16)
    
    # 组合成64位十六进制 -QW
    realistic_id = base + random_suffix
    
    print(f"[设备代码] 生成真实感机器ID: {realistic_id[:8]}...{realistic_id[-8:]}")
    return realistic_id


def validate_machine_id(machine_id: str) -> bool:
    """
    验证机器ID格式是否正确 -QW
    
    Args:
        machine_id: 要验证的机器ID
        
    Returns:
        bool: 格式是否正确
    """
    if not machine_id:
        return False
    
    # 检查长度（64个十六进制字符） -QW
    if len(machine_id) != 64:
        return False
    
    # 检查是否全为十六进制字符 -QW
    try:
        int(machine_id, 16)
        return True
    except ValueError:
        return False


def validate_device_id(device_id: str) -> bool:
    """
    验证设备ID格式是否正确 -QW
    
    Args:
        device_id: 要验证的设备ID
        
    Returns:
        bool: 格式是否正确
    """
    if not device_id:
        return False
    
    try:
        # 尝试解析为UUID -QW
        uuid.UUID(device_id)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    # 测试设备代码生成功能 -QW
    print("=== AugmentPage 设备代码生成测试 ===")
    
    print("\n1. 基础ID生成:")
    machine_id = generate_machine_id()
    device_id = generate_device_id()
    print(f"机器ID: {machine_id}")
    print(f"设备ID: {device_id}")
    
    print("\n2. 扩展ID生成:")
    mac_machine_id = generate_mac_machine_id()
    sqm_id = generate_sqm_id()
    print(f"Mac机器ID: {mac_machine_id}")
    print(f"SQM ID: {sqm_id}")
    
    print("\n3. 完整遥测ID集合:")
    telemetry_ids = generate_telemetry_ids()
    for key, value in telemetry_ids.items():
        print(f"  {key}: {value}")
    
    print("\n4. 真实感机器ID:")
    realistic_id = generate_realistic_machine_id()
    print(f"真实感机器ID: {realistic_id}")
    
    print("\n5. ID验证:")
    print(f"机器ID验证: {validate_machine_id(machine_id)}")
    print(f"设备ID验证: {validate_device_id(device_id)}")
    print(f"无效机器ID验证: {validate_machine_id('invalid')}")
    print(f"无效设备ID验证: {validate_device_id('invalid')}")
    
    print("\n=== 测试完成 ===")
