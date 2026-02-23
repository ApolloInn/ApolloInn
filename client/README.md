# Apollo 桌面客户端

## 组件

| 应用 | 说明 |
|------|------|
| ApolloAgent | 用户端 — 换号、配置 Cursor 反向代理 |
| ApolloExtractor | 凭证提取器 — 提取本机 Kiro/Cursor 凭证并上传到服务端 |

## 依赖

- Python 3.10+
- PyQt5（GUI）
- httpx（HTTP 请求）
- PyInstaller（打包）
- PyArmor（代码混淆）

## 开发

```bash
pip install pyqt5 httpx
python agent/agent_ui.py
```

## 构建

Mac:
```bash
cd build
bash build.sh
```

Windows:
```bash
cd build
build.bat
```

构建产物输出到 `client/agent/obf/dist/` 和 `client/extractor/obf/dist/`。

详见 [build/RELEASE.md](build/RELEASE.md) 了解发版流程。
