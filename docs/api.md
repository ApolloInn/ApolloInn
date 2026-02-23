# API 接口文档

所有接口基础地址：`https://api.apolloinn.site`

---

## 公共接口

### 健康检查

```
GET /health
→ {"status": "ok", "service": "apollo-gateway"}
```

---

## AI 代理接口

### OpenAI 兼容（Cursor 优化）

```
POST /v1/chat/completions
Authorization: Bearer <usertoken 或 apikey>
```

Cursor IDE 直连使用。包含 anti-lazy stop、heartbeat、fake reasoning 等优化。

### OpenAI 兼容（纯净）

```
POST /standard/v1/chat/completions
Authorization: Bearer <usertoken 或 apikey>
```

无 Cursor 特定 hack 的标准 OpenAI 代理。

### OpenAI 兼容（无思维链）

```
POST /nothink/v1/chat/completions
Authorization: Bearer <usertoken 或 apikey>
```

同 Cursor 优化版，但不注入 thinking 标签。

### Anthropic Messages API

```
POST /v1/messages
x-api-key: <apikey>
```

Claude Code CLI 等 Anthropic SDK 客户端直连。

### 模型列表

```
GET /v1/models
Authorization: Bearer <usertoken 或 apikey>
→ {"data": [{"id": "claude-sonnet-4.6", ...}, ...]}
```

---

## 用户接口（/user）

认证方式：`Authorization: Bearer <usertoken>`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/user/info` | 系统信息 + 计费说明 + 代理配置指南 |
| GET | `/user/me` | 当前用户信息（余额、用量等） |
| GET | `/user/apikeys` | 列出 API Key |
| POST | `/user/apikeys` | 创建 API Key |
| DELETE | `/user/apikeys` | 吊销 API Key `{"apikey": "xxx"}` |
| GET | `/user/usage` | 用量统计 |
| GET | `/user/combos` | 可用模型组合 |
| GET | `/user/cursor-activation` | 获取 Cursor 激活码 |
| POST | `/user/switch` | 换号（从 Cursor 账号池取号） |

---

## 代理商接口（/agent）

认证方式：`X-Agent-Key: <agent_key>`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/agent/me` | 代理商信息（额度池、用户数等） |
| GET | `/agent/users` | 名下用户列表 |
| POST | `/agent/users` | 创建用户 `{"name": "xxx"}` |
| DELETE | `/agent/users/{id}` | 删除用户 |
| PUT | `/agent/users/{id}/status` | 设置状态 `{"status": "active\|suspended"}` |
| POST | `/agent/users/{id}/grant` | 充值额度 `{"amount": 10000}` |
| GET | `/agent/users/{id}/usage` | 用户用量 |
| GET | `/agent/users/{id}/token` | 获取用户 usertoken |
| GET | `/agent/users/{id}/apikeys` | 用户 API Key 列表 |
| POST | `/agent/users/{id}/apikeys` | 创建 API Key |
| DELETE | `/agent/users/{id}/apikeys` | 吊销 API Key |
| PUT | `/agent/users/{id}/quota` | 设置配额 |
| POST | `/agent/users/{id}/reset-switch` | 重置换号次数 |

---

## 管理员接口（/admin）

认证方式：`X-Admin-Key: <admin_key>`

### 凭证管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/tokens` | 凭证列表 |
| POST | `/admin/tokens` | 添加凭证 |
| DELETE | `/admin/tokens/{id}` | 删除凭证 |
| POST | `/admin/tokens/{id}/test` | 测试凭证有效性 |
| GET | `/admin/tokens/usage/all` | 所有凭证用量 |
| GET | `/admin/tokens/{id}/usage` | 单个凭证用量 |

### 用户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/users` | 用户列表 |
| POST | `/admin/users` | 创建用户 `{"name": "xxx"}` |
| DELETE | `/admin/users/{id}` | 删除用户 |
| PUT | `/admin/users/{id}/status` | 设置状态 |
| PUT | `/admin/users/{id}/token` | 分配凭证 `{"token_id": "xxx"}` |
| GET | `/admin/users/{id}/token` | 获取 usertoken |
| PUT | `/admin/users/{id}/quota` | 设置配额 |
| POST | `/admin/users/{id}/grant` | 充值额度 |
| POST | `/admin/users/{id}/reset-switch-count` | 重置换号次数 |

### 用户 API Key

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/users/{id}/apikeys` | 列出 |
| POST | `/admin/users/{id}/apikeys` | 创建 |
| DELETE | `/admin/users/{id}/apikeys` | 吊销 `{"apikey": "xxx"}` |

### 用量监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/usage` | 全局用量 |
| GET | `/admin/usage/{user_id}` | 用户用量 |
| GET | `/admin/usage/{user_id}/recent` | 最近记录 `?limit=20` |
| POST | `/admin/usage/{user_id}/reset` | 重置用量 |
| GET | `/admin/status` | 系统状态概览 |

### Combo 模型映射

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/combos` | 列出 |
| POST | `/admin/combos` | 创建/更新 `{"name": "xxx", "models": [...]}` |
| DELETE | `/admin/combos/{name}` | 删除 |

### 凭证提取

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/extract/cursor` | 提取本机 Cursor 凭证 |
| POST | `/admin/extract/kiro` | 提取本机 Kiro 凭证 |
| POST | `/admin/extract/upload` | 提取器客户端上传（无需 admin key） |

### Cursor 账号池

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/cursor-accounts` | 列出 |
| POST | `/admin/cursor-accounts` | 添加 |
| DELETE | `/admin/cursor-accounts/{id}` | 删除 |
| POST | `/admin/cursor-accounts/{id}/refresh` | 刷新 token |

### Promax 激活码

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/promax-keys` | 列出 |
| POST | `/admin/promax-keys` | 添加 `{"api_key": "xxx"}` |
| DELETE | `/admin/promax-keys/{id}` | 删除 |
| PUT | `/admin/promax-keys/{id}/assign` | 分配给用户 |

### 代理商管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/agents` | 列出 |
| POST | `/admin/agents` | 创建 `{"name": "xxx"}` |
| DELETE | `/admin/agents/{id}` | 删除 |
| GET | `/admin/agents/{id}` | 详情（含名下用户） |
| PUT | `/admin/agents/{id}/status` | 设置状态 |
| POST | `/admin/agents/{id}/grant` | 充值额度池 |
| PUT | `/admin/agents/{id}/quota` | 设置配额 |
