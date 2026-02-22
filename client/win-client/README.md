# Apollo Client

用户侧客户端工具集，包含本地桌面 Agent 和 Cursor 配置脚本。

## 目录结构

```text
client/
├── agent/           # Apollo Local Agent — 本机运行的轻量服务
│   ├── main.py      # 主程序，监听 127.0.0.1:19080
│   ├── ui.py        # 内嵌 HTML 页面
│   ├── cursor_auth.py
│   └── cursor_utils.py
├── setup/           # Cursor 配置/补丁脚本
│   ├── full_setup.py       # 完整自动配置
│   ├── patch_cursor.py     # Cursor 二进制补丁
│   ├── upload_creds.py     # 上传凭证到服务端
│   ├── auto_setup.js       # 浏览器端自动配置
│   └── setup_page.js       # 配置页面逻辑
├── build/           # 打包构建（PyInstaller）
│   ├── build.sh     # macOS 构建
│   ├── build.bat    # Windows 构建
│   └── ...
├── dist/            # 构建产物（.app / .dmg / .exe）
└── BUILD_GUIDE.md   # 构建指南（含 Windows 交叉编译说明）
```

## Apollo Local Agent

用户双击运行后：

- 启动本地 HTTP 服务（`127.0.0.1:19080`）
- 打开原生桌面窗口（WebView 加载本地 UI）
- 网页端用户面板通过 CORS 调用本地 Agent 完成 Cursor 账号切换

```bash
# 开发运行
cd agent
python main.py
```

## 构建

详见 [BUILD_GUIDE.md](BUILD_GUIDE.md)。
