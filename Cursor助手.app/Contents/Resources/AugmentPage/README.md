# AugmentPage - 跨平台IDE管理工具

AugmentPage 是一个强大的跨平台IDE管理工具，支持Windows、macOS和Linux系统。它提供了完整的IDE检测、配置管理、机器ID重置等功能。

## 🌟 主要特性

### 🔍 智能IDE检测
- 自动检测VSCode系列IDE（Cursor、VSCode、VSCodium等）
- 自动检测JetBrains系列IDE（IntelliJ IDEA、PyCharm、WebStorm等）
- 跨平台配置路径智能识别

### 🛠️ 配置管理
- 遥测ID修改和重置
- 工作区存储清理
- 数据库清理和优化
- 机器ID生成和管理

### 🌐 自动化工具
- 邮箱验证码自动获取
- 浏览器自动化管理
- Cursor自动登录
- 完整的重置工具

### 🖥️ 跨平台支持
- **Windows**: 完整支持，包含UAC权限管理
- **macOS**: 原生支持，使用macOS专用路径和权限
- **Linux**: 完整支持，兼容各种发行版

## 📦 安装和使用

### 基本使用

```python
# 导入适配器
from AugmentPage.adapter import get_adapter

# 创建适配器实例
adapter = get_adapter()

# 检测系统中的IDE
ides_result = adapter.detect_ides()
print(f"检测到 {ides_result['count']} 个IDE")

# 生成新的设备代码
codes_result = adapter.generate_device_codes()
print(f"生成了 {codes_result['count']} 个设备代码")
```

### 高级使用

```python
# 使用API核心
from AugmentPage.api.core import AugmentPageAPI
api = AugmentPageAPI()

# 修改遥测ID
from AugmentPage.api.handlers.telemetry import modify_telemetry_ids
result = modify_telemetry_ids("Cursor")

# 清理工作区
from AugmentPage.api.handlers.workspace import clean_workspace_storage
result = clean_workspace_storage("Cursor")

# 检测JetBrains IDE
from AugmentPage.api.handlers.jetbrains import get_jetbrains_info
info = get_jetbrains_info()
```

## 🧪 测试套件

运行完整测试：
```bash
python -m AugmentPage.test_suite --full
```

运行快速测试：
```bash
python -m AugmentPage.test_suite --quick
```

运行演示：
```bash
python -m AugmentPage.test_suite --demo
```

## 📁 模块结构

```
AugmentPage/
├── utils/                      # 工具模块
│   ├── paths.py                # 跨平台路径工具
│   ├── device_codes.py         # 设备代码生成
│   └── ide_detector.py         # IDE检测器
├── api/                        # API模块
│   ├── core.py                 # 核心API
│   └── handlers/               # 处理器
│       ├── telemetry.py        # 遥测处理
│       ├── database.py         # 数据库处理
│       ├── workspace.py        # 工作区处理
│       └── jetbrains.py        # JetBrains处理
├── adapter.py                  # 主适配器
├── test_suite.py              # 测试套件
├── simple_ide_detector.py     # 简单IDE检测器
├── simple_cleaner.py          # 简单清理器
├── get_email_code.py          # 邮箱验证码
├── browser_utils.py           # 浏览器管理
├── CursorAutoLogin.py         # 自动登录
├── totally_reset_cursor.py    # 完全重置
└── reset_machine_manual.py    # 手动重置
```

## 🔧 功能详解

### 1. IDE检测
```python
from AugmentPage.utils.ide_detector import detect_ides

result = detect_ides()
for ide in result["ides"]:
    print(f"{ide['icon']} {ide['display_name']} - {ide['ide_type']}")
```

### 2. 设备代码生成
```python
from AugmentPage.utils.device_codes import generate_telemetry_ids

ids = generate_telemetry_ids()
for key, value in ids.items():
    print(f"{key}: {value}")
```

### 3. 路径管理
```python
from AugmentPage.utils.paths import (
    get_storage_path,
    get_workspace_storage_path,
    get_cursor_executable_path
)

storage_path = get_storage_path("Cursor")
workspace_path = get_workspace_storage_path("Cursor")
executable_path = get_cursor_executable_path()
```

### 4. 遥测ID修改
```python
from AugmentPage.api.handlers.telemetry import modify_telemetry_ids

result = modify_telemetry_ids("Cursor")
print(f"旧ID: {result['old_ids']}")
print(f"新ID: {result['new_ids']}")
```

### 5. 工作区清理
```python
from AugmentPage.api.handlers.workspace import clean_workspace_storage

result = clean_workspace_storage("Cursor")
print(f"备份路径: {result['backup_path']}")
print(f"删除文件数: {result['deleted_files_count']}")
```

## 🛡️ 安全特性

- **自动备份**: 所有修改操作前自动创建备份
- **权限管理**: 智能处理文件权限和系统权限
- **错误恢复**: 详细的错误处理和回滚机制
- **日志记录**: 完整的操作日志和调试信息

## 🌍 平台特性

### macOS
- 使用 `~/Library/Application Support/` 作为配置目录
- 支持 `chflags uchg` 文件保护
- 使用 `osascript` 请求管理员权限
- 兼容应用程序包结构

### Windows
- 使用 `%APPDATA%` 作为配置目录
- 支持UAC权限提升
- 使用 `attrib` 命令文件保护
- 处理长路径和只读文件

### Linux
- 使用 `~/.config/` 作为配置目录
- 支持 `sudo` 权限提升
- 使用 `chmod` 文件权限管理
- 兼容各种发行版

## 📊 测试报告

运行测试后会生成详细的测试报告，包括：
- 系统信息
- 模块可用性
- 功能测试结果
- 性能统计
- 错误详情

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 📄 许可证

本项目采用MIT许可证。

---

**注意**: 使用本工具修改IDE配置前，请确保已备份重要数据。本工具会自动创建备份，但建议用户也进行额外备份。
