# Apollo

Cursor / Kiro 账号管理网关。基于 [kiro-gateway](https://github.com/jwadow/kiro-gateway)（AGPL-3.0）扩展，提供多租户用户管理、Token 池轮转、代理商体系等功能。

## 架构

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  admin 面板  │  │  agent 面板  │  │  user 面板   │
│  (React)    │  │  (React)    │  │  (React)    │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        │ HTTPS
                ┌───────▼───────┐
                │ Apollo Gateway │  ← FastAPI (Python)
                │   /admin/*    │
                │   /agent/*    │
                │   /user/*     │
                │   /v1/*       │  ← OpenAI / Anthropic 兼容
                └───────┬───────┘
                        │
              ┌─────────▼─────────┐
              │   Kiro API        │
              │ (Amazon Q / AWS)  │
              └───────────────────┘

桌面客户端:
  ApolloAgent     — 用户端（PyQt5，换号/配置代理）
  ApolloExtractor — 凭证提取器（PyQt5，提取本机 Kiro/Cursor 凭证上传）
```

## 目录结构

| 目录 | 说明 | 技术栈 |
|------|------|--------|
| `server/` | API 网关后端 | Python 3.10+, FastAPI, asyncpg, PostgreSQL |
| `admin/` | 管理员面板 | React 19, TypeScript, Zustand, Vite |
| `agent/` | 代理商面板 | React 19, TypeScript, Zustand, Vite |
| `user/` | 用户面板 | React 19, TypeScript, Zustand, Vite |
| `client/` | 桌面客户端 | Python, PyQt5, PyInstaller |
| `docs/` | 项目文档 | Markdown |
| `tests/` | 测试数据 | JSON fixtures |

## 快速开始

### 1. 后端

```bash
cd server
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 配置环境变量（参考模板）
cp .env.example .env
# 编辑 .env，至少填写 DATABASE_URL

# 初始化数据库
psql -d apollo -f db/schema.sql

# 启动
python app.py
# 或指定端口
python app.py --port 9000
```

### 2. 前端（admin / agent / user 任选）

```bash
cd admin  # 或 agent / user
npm install
npm run dev
```

### 3. 桌面客户端

参见 [client/README.md](client/README.md)。

## 下载

前往 [Releases](https://github.com/ApolloInn/ApolloInn/releases) 下载打包好的桌面客户端：

- **ApolloAgent**: Mac (.zip) / Windows (.exe)
- **ApolloExtractor**: Mac (.zip) / Windows (.exe)

## 文档

- [架构设计](docs/architecture.md)
- [API 接口](docs/api.md)
- [部署手册](docs/deployment.md)
- [服务器清单](docs/servers.md)
