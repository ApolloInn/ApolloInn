# Client — 客户端工具

用户侧的桌面应用和配置脚本。

## 目录结构

```
client/
├── agent/              ApolloAgent 桌面端（Python GUI）
│   ├── main.py         主程序入口
│   ├── ui.py           GUI 界面（tkinter）
│   ├── cursor_auth.py  Cursor 认证逻辑
│   └── cursor_utils.py Cursor 工具函数
├── extractor/          ApolloExtractor（Cursor 凭证提取工具）
│   ├── apollo_extractor.py  主程序
│   ├── build.sh             macOS 打包脚本
│   └── build.bat            Windows 打包脚本
├── setup/              自动配置脚本
│   ├── full_setup.py        完整安装流程
│   ├── patch_cursor.py      Cursor 客户端补丁
│   ├── auto_setup.js        自动配置（浏览器端）
│   ├── setup_page.js        配置页面
│   └── upload_creds.py      上传凭证到服务器
├── build/              打包配置
│   ├── build.sh             macOS PyInstaller 打包
│   ├── build.bat            Windows 打包
│   └── apollo_agent.spec    PyInstaller spec 文件
└── win-client/         Windows 专用版本
```

## ApolloAgent

桌面端 GUI 应用，用户安装后自动配置 Cursor 连接到 Apollo Gateway。

```bash
# 开发运行
cd agent
python main.py

# 打包 macOS
cd build && bash build.sh

# 打包 Windows
cd build && build.bat
```

## ApolloExtractor

从本地 Cursor 安装中提取认证凭证。

```bash
cd extractor
python apollo_extractor.py
```

## 修改指南

- 修改 Agent GUI → `agent/ui.py`
- 修改 Cursor 认证流程 → `agent/cursor_auth.py`
- 修改自动配置逻辑 → `setup/full_setup.py`
- 修改打包配置 → `build/apollo_agent.spec`
