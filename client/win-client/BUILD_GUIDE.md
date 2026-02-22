# Apollo Agent 构建指南

## 一、项目概述

Apollo Agent 是一个本地桌面客户端，用户双击运行后：
- 自动关闭占用同端口的旧进程
- 启动本地 HTTP 服务（`127.0.0.1:19080`）
- 打开原生桌面窗口（pywebview 内嵌 WebKit/WebView2）
- 网页端通过 CORS 调用本地 Agent 完成 Cursor 配置

macOS 和 Windows 均使用 pywebview 作为原生窗口方案。

---

## 二、需要给 Windows 构建人员的文件

只需要 `client/` 目录下的以下文件：

```
client/
├── agent/
│   ├── main.py              ← 主程序（全部功能代码）
│   └── ui.py                ← 内嵌 HTML 页面（被 main.py 导入为 agent_ui）
├── build/
│   ├── apollo_agent.spec    ← PyInstaller 打包配置（已适配双平台）
│   ├── build.bat            ← Windows 一键构建脚本
│   ├── build.sh             ← macOS 构建脚本
│   ├── strip_comments.py    ← 去注释工具（build.sh 使用）
│   ├── icon.ico             ← Windows 图标
│   └── icon.icns            ← macOS 图标
```

**最简方式：把整个 `client/` 文件夹拷到 Windows 机器即可。**

---

## 三、Windows 构建步骤

### 环境要求

- Python 3.10+（建议 3.11 或 3.12）
- pip

### 一键构建

```cmd
cd client
build\build.bat
```

脚本会自动：
1. 安装 `pyinstaller` 和 `pywebview`
2. 执行 PyInstaller 打包
3. 输出 `dist\ApolloAgent.exe`（单文件，约 30-50MB）

### 手动构建（如果 bat 有问题）

```cmd
cd client
pip install pyinstaller pywebview

REM 把 agent 源码复制到 build 目录（spec 文件期望在同目录找到源码）
copy agent\main.py build\apollo_agent.py
copy agent\ui.py build\agent_ui.py

pyinstaller build\apollo_agent.spec --distpath dist --workpath build\tmp --clean -y
```

产物：`dist\ApolloAgent.exe`

### macOS 构建

```bash
cd client
bash build/build.sh
```

自动完成：去注释 → PyArmor 加密 → PyInstaller 打包 → 生成 DMG

产物：`dist/ApolloAgent.dmg`

---

## 四、关键技术细节

### 原生窗口（双平台统一）

两个平台都使用 `pywebview`：
- macOS：底层是 WebKit（WKWebView）
- Windows：底层是 WebView2（Edge Chromium），回退到 MSHTML

之前 macOS 用 pyobjc 直接调 WKWebView，但 PyArmor 加密后 pyobjc 的 NSObject 子类会报 `tuple index out of range`，所以统一改为 pywebview。

### 端口冲突处理

启动时自动检测并 kill 占用 19080 端口的旧进程：
- macOS/Linux：`lsof -ti :19080` + `kill -9`
- Windows：`netstat -ano` 查找 + `taskkill /F /PID`

### 登录持久化

用户 token 双重存储：
- WebView 的 `localStorage`（前端）
- `~/.apollo/agent_config.json` 的 `usertoken` 字段（后端）

启动时先检查 localStorage，没有则从后端 config 恢复，确保关闭 app 再打开不用重新登录。

### Cursor 代理配置

Agent 只写入 API Key 和 Base URL，不写入模型列表（`modelOverrideEnabled`、`availableDefaultModels2` 等），让用户在 Cursor 中自行添加模型。

---

## 五、HTTP API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/` `/ui` | GET | 返回内嵌 HTML 页面 |
| `/ping` | GET | 心跳检测 |
| `/status` | GET | 状态（系统、数据库、激活状态、当前账号） |
| `/get-token` | GET | 获取本地存储的 usertoken |
| `/save-token` | POST | 保存/清除 usertoken 到本地 config |
| `/switch` | POST | 静态切换（传入凭证） |
| `/smart-switch` | POST | 智能换号（自动获取新鲜 token） |
| `/byok-setup` | POST | 一键配置（Pro 账号 + 代理） |
| `/extract-cursor` | POST | 提取本机 Cursor 凭证上传到服务器 |
| `/patch-cursor` | POST | 补丁 Cursor 二进制 |
| `/revert-patch` | POST | 还原 Cursor 补丁 |
| `/license-activate` | POST | 激活码激活 |

---

## 六、构建后验证清单

1. **双击启动** — 弹出独立原生窗口（不是浏览器）
2. **窗口 UI** — 显示 Apollo Agent 登录页面
3. **登录** — 输入 apollo-xxx token 后进入 Dashboard
4. **关闭重开** — 关闭 app 再打开，应自动登录（不用重新输入 token）
5. **重复启动** — 连续双击两次，不报端口占用错误
6. **Agent 状态** — 网页端用户面板显示 "Agent 在线"
7. **一键配置** — 点击"一键配置"能完成完整流程
8. **窗口关闭** — 关闭窗口后进程完全退出

---

## 七、发布

### GitHub 仓库信息

- 仓库：`https://github.com/ApolloInn/ApolloInn`
- 用途：仅用于存放客户端 Release 安装包，不存放源码
- GitHub 账号：`ApolloInn`

### 安装 GitHub CLI（如果没有）

```bash
# macOS
brew install gh

# Windows
winget install GitHub.cli
```

### 登录 GitHub CLI

```bash
gh auth login
# 选择 GitHub.com → HTTPS → 用浏览器登录
```

### 上传 macOS 版本

```bash
# 首次创建 release（只需一次）
gh release create v1.0.0 --repo ApolloInn/ApolloInn --title "ApolloAgent v1.0.0" --notes "Apollo Agent macOS 版"

# 上传/更新 DMG（--clobber 覆盖已有同名文件）
gh release upload v1.0.0 client/dist/ApolloAgent.dmg --repo ApolloInn/ApolloInn --clobber
```

下载链接：`https://github.com/ApolloInn/ApolloInn/releases/download/v1.0.0/ApolloAgent.dmg`

### 上传 Windows 版本

```bash
# 首次创建 release（只需一次）
gh release create v2.0.0-win --repo ApolloInn/ApolloInn --title "Apollo Agent v2.0.0 Windows" --notes "Apollo Agent Windows 版"

# 上传/更新 EXE
gh release upload v2.0.0-win client/dist/ApolloAgent.exe --repo ApolloInn/ApolloInn --clobber
```

下载链接：`https://github.com/ApolloInn/ApolloInn/releases/download/v2.0.0-win/ApolloAgent.exe`

### 用户面板中的下载链接

用户面板（`user/src/views/Dashboard.tsx`）中已配置好下载按钮，指向以上链接：

```
macOS: https://github.com/ApolloInn/ApolloInn/releases/download/v1.0.0/ApolloAgent.dmg
Windows: https://github.com/ApolloInn/ApolloInn/releases/download/v2.0.0-win/ApolloAgent.exe
```

上传后用户端自动生效，无需改代码。

---

## 八、常见问题

**Q: Windows 打包后双击没反应？**
A: 可能缺少 WebView2 Runtime。Windows 10 1803+ 和 Windows 11 自带，旧系统需要安装：https://developer.microsoft.com/en-us/microsoft-edge/webview2/

**Q: macOS 提示"无法打开，因为无法验证开发者"？**
A: 右键点击 app → 打开，或者在系统偏好设置 → 安全性中允许。

**Q: 打包后体积太大？**
A: pywebview 带了较多依赖（约 40-50MB）。可以用 UPX 压缩，spec 文件已配置 `upx=True`。

**Q: Windows 上 pywebview 回退到 MSHTML（IE 内核）？**
A: 安装 WebView2 Runtime 即可使用 Edge Chromium 内核。
