# 架构设计

## 系统概览

Apollo Gateway 是一个 AI API 代理网关，位于客户端（Cursor IDE、Claude Code CLI、Kiro IDE）和 Kiro API（Amazon Q Developer）之间，提供多租户管理、凭证池轮转、格式转换等功能。

## 核心模块

### 1. Token Pool（凭证池）

`services/token_pool.py` — 数据层 + 内存缓存

- 管理多个 Kiro 凭证，支持 round-robin 轮转
- 403/402 自动 failover 到下一个可用凭证
- 内存缓存 + PostgreSQL 持久化
- 支持按用户绑定指定凭证

### 2. Auth Bridge（认证桥接）

`services/auth_bridge.py` — 每个凭证独立的认证管理器

- 为每个 token 维护独立的 `KiroAuthManager` 实例
- 支持两种认证方式：
  - **Kiro Desktop Auth**: refresh_token + profile_arn
  - **AWS SSO OIDC**: client_id + client_secret（kiro-cli）
- 自动刷新过期 access_token

### 3. Model Resolver（模型解析）

`core/model_resolver.py` — 4 层模型名称解析

```
用户请求模型名 → alias 别名 → combo 组合 → normalize 标准化 → cache 缓存查找 → passthrough
```

- **alias**: 自定义别名（如 `auto-kiro` → `auto`）
- **combo**: 组合模型（如 `kiro-opus` → 随机选 opus 系列）
- **normalize**: 处理各种 Claude 命名变体
- **cache**: 从 Kiro API 获取的模型元数据

### 4. 格式转换

| 模块 | 方向 |
|------|------|
| `converters_openai.py` | OpenAI 请求 → Kiro payload |
| `converters_anthropic.py` | Anthropic 请求 → Kiro payload |
| `streaming_openai.py` | Kiro SSE → OpenAI SSE |
| `streaming_anthropic.py` | Kiro SSE → Anthropic SSE |

### 5. 智能优化

- **Context Compression** (`context_compression.py`): 输入接近上下文窗口时智能压缩，防止输出被截断
- **Truncation Recovery** (`truncation_recovery.py`): 检测到截断时注入合成消息帮助模型恢复
- **Anti-Lazy Stop**: 检测可疑的短回复，将 `stop` 改为 `length` 触发 Cursor 自动续写
- **Fake Reasoning** (`thinking_parser.py`): 注入 `<thinking_mode>` 标签，解析 `<thinking>` 块转为 OpenAI `reasoning_content`

## 路由架构

| 路径 | 认证方式 | 用途 |
|------|---------|------|
| `GET /health` | 无 | 健康检查 |
| `POST /v1/chat/completions` | Bearer usertoken/apikey | Cursor 优化的 OpenAI 代理 |
| `POST /nothink/v1/chat/completions` | Bearer usertoken/apikey | 同上，不注入思维链 |
| `POST /standard/v1/chat/completions` | Bearer usertoken/apikey | 纯净 OpenAI 代理 |
| `POST /v1/messages` | x-api-key | Anthropic Messages API |
| `GET /v1/models` | Bearer usertoken/apikey | 模型列表 |
| `/admin/*` | X-Admin-Key | 管理员 CRUD |
| `/user/*` | Bearer usertoken | 用户自助 |
| `/agent/*` | X-Agent-Key | 代理商管理 |

## 数据库

PostgreSQL，10 张表：

```
admin_config          — 全局配置（KV）
tokens                — Kiro 凭证池
users                 — 用户
user_apikeys          — 用户 API Key
usage_records         — 用量记录（逐条）
model_mappings        — 模型映射（combo + alias）
cursor_tokens         — Cursor Pro 凭证池
promax_keys           — Cursor Promax 激活码
agents                — 二级代理商
token_transactions    — 额度流水（充值/扣减/退还）
```

详见 `server/db/schema.sql`。

## 多角色体系

```
Admin（管理员）
  ├── 管理所有凭证、用户、代理商
  ├── 充值额度、设置配额
  └── 提取/上传 Kiro & Cursor 凭证

Agent（代理商）
  ├── 管理名下用户（创建/停用/充值）
  ├── 从 Admin 分配的额度池中给用户充值
  └── 有独立的 max_users 和 token_pool 限制

User（用户）
  ├── 查看自己的用量和余额
  ├── 管理 API Key
  ├── 换号（从 Cursor 账号池取号）
  └── 通过 /v1/* 接口使用 AI 模型
```
