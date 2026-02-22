# Apollo Gateway

AI 编程助手网关服务，将 Kiro/Cursor API 封装为 OpenAI 和 Anthropic 兼容接口，支持多用户、Token 池、二级代理商等功能。

## 项目结构

```
apollo/
├── server/      后端 API 服务（FastAPI + PostgreSQL）
├── admin/       管理面板前端（React）
├── user/        用户面板前端（React）
├── agent/       代理商面板前端（React，独立仓库）
├── client/      客户端工具（Agent 桌面端、Extractor、Setup 脚本）
├── scripts/     运维和分析脚本
├── tests/       测试
└── docs/        文档
```

## 快速开始

### 1. 数据库

```bash
# 创建 PostgreSQL 数据库
createdb apollo
psql apollo < server/db/schema.sql
```

### 2. 后端

```bash
cd server
cp .env.example .env
# 编辑 .env，填入 DATABASE_URL
pip install -r requirements.txt
python app.py
```

服务启动后：
- API: `http://localhost:8000`
- 管理接口: `http://localhost:8000/admin`
- 健康检查: `http://localhost:8000/health`

### 3. 前端

```bash
# 管理面板
cd admin && npm install && npm run dev

# 用户面板
cd user && npm install && npm run dev
```

## API 兼容性

| 端点 | 协议 | 说明 |
|------|------|------|
| `/v1/chat/completions` | OpenAI | 聊天补全（流式/非流式） |
| `/v1/messages` | Anthropic | Messages API |
| `/v1/models` | OpenAI | 模型列表 |

## 服务器架构

| 服务器 | 区域 | IP | 域名 | 用途 |
|--------|------|----|------|------|
| 🇺🇸 Ohio | us-east-2 | 18.223.114.145 | `api.apolloinn.site` | API 主站 + PostgreSQL 主库 |
| 🇺🇸 Oregon | us-west-2 | 34.222.159.160 | `api2.apolloinn.site` | API 备站 |
| 🇯🇵 Tokyo | ap-northeast-1 | 52.195.205.77 | `api3.apolloinn.site` | API 亚洲节点 |
| 🇺🇸 Oregon (Proxy) | us-west-2 | 44.248.224.204 | `proxy-us.apolloinn.site` | 代理节点 |
| 🇯🇵 Tokyo (Proxy) | ap-northeast-1 | 43.206.212.53 | `proxy-jp.apolloinn.site` | 代理节点 |

- 数据库：Ohio 为主库，Oregon / Tokyo API 远程连接 Ohio
- 前端：Vercel 托管（admin / user / agent 面板）
- CDN：Cloudflare（代理节点 + API 域名）

## 部署

生产环境使用 systemd + nginx + PostgreSQL：

```bash
# 上传 server/ 到服务器 /opt/apollo/
scp -r server/* user@server:/opt/apollo/

# systemd 服务
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2
```

前端构建后部署到 Vercel 或 nginx 静态托管。
