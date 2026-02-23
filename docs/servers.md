# 服务器清单

## 密钥位置

所有 SSH 密钥存放在项目根目录（`~/Desktop/apollo/`）：

| 密钥文件 | 用途 |
|---------|------|
| `apollo-key.pem` | API 服务器（美东 Ohio） |
| `apollo-jp.pem` | API 服务器（日本）+ 代理服务器（日本） |
| `apollo-prod-oregon.pem` | API 服务器（美西 Oregon） |
| `apollo-proxy-oregon.pem` | 代理服务器（美西 Oregon） |

## 快速登录

```bash
# API 服务器
ssh -i apollo-key.pem ubuntu@18.223.114.145          # 美东 Ohio
ssh -i apollo-jp.pem ubuntu@52.195.205.77             # 日本 Tokyo
ssh -i apollo-prod-oregon.pem ubuntu@34.222.159.160   # 美西 Oregon

# 代理服务器
ssh -i apollo-proxy-oregon.pem ubuntu@44.248.224.204  # 代理 美西
ssh -i apollo-jp.pem ubuntu@43.206.212.53             # 代理 日本
ssh root@207.148.73.138                               # 代理 新加坡（密码登录）
```

---

## 1a. 生产服务器（美东 Ohio）— 主力

| 项目 | 值 |
|------|-----|
| IP | `18.223.114.145` |
| 域名 | `api.apolloinn.site` |
| 平台 | AWS EC2 |
| 系统 | Ubuntu |
| 密钥 | `apollo-key.pem` |
| 登录 | `ssh -i apollo-key.pem ubuntu@18.223.114.145` |
| 服务 | Apollo Gateway（uvicorn + 2 workers）、PostgreSQL、nginx |
| 端口 | 8000（API）、80/443（nginx） |

## 1b. 生产服务器（美西 Oregon）— 其次

| 项目 | 值 |
|------|-----|
| IP | `34.222.159.160` |
| 域名 | `api2.apolloinn.site` |
| 平台 | AWS EC2 |
| 系统 | Ubuntu |
| 密钥 | `apollo-prod-oregon.pem` |
| 登录 | `ssh -i apollo-prod-oregon.pem ubuntu@34.222.159.160` |
| 服务 | Apollo Gateway（uvicorn + 2 workers）、nginx |
| 数据库 | 连接 Ohio 主库（18.223.114.145） |
| 端口 | 8000（API）、80/443（nginx） |

## 1c. 生产服务器（日本 Tokyo）— 备用

| 项目 | 值 |
|------|-----|
| IP | `52.195.205.77` |
| 域名 | `api3.apolloinn.site` / `api-jp.apolloinn.site` |
| 平台 | AWS EC2 (t3.small, 2C/2GB) |
| 系统 | Ubuntu 24.04 |
| 密钥 | `apollo-jp.pem` |
| 登录 | `ssh -i apollo-jp.pem ubuntu@52.195.205.77` |
| 服务 | Apollo Gateway（uvicorn + 2 workers）、PostgreSQL 16、nginx |
| 数据库 | 连接 Ohio 主库（18.223.114.145） |
| 端口 | 8000（API）、80/443（nginx） |

## 2. 代理服务器 - 美国（Oregon）

| 项目 | 值 |
|------|-----|
| IP | `44.248.224.204` |
| 域名 | `proxy-us.apolloinn.site` |
| 平台 | AWS EC2 (t3.micro) |
| 系统 | Ubuntu 24.04 |
| 登录 | `ssh -i apollo-proxy-oregon.pem ubuntu@44.248.224.204` |
| 密钥 | `apollo-proxy-oregon.pem`（项目根目录） |
| 服务 | Xray + nginx（VLESS/VMess + WebSocket + CF CDN） |
| 订阅 | `https://proxy-us.apolloinn.site/sub` |

## 3. 测试 / 代理服务器 - 新加坡

| 项目 | 值 |
|------|-----|
| IP | `207.148.73.138` |
| 域名 | `proxy-sg.apolloinn.site` / `test.apolloinn.site` |
| 平台 | Vultr |
| 系统 | Ubuntu 24.04 |
| 登录 | `ssh root@207.148.73.138`（密码：`9?VjzdYiRLj4[47+`） |
| 服务 | Xray + nginx（代理）、Apollo Gateway 测试实例、PostgreSQL |
| 订阅 | `https://proxy-sg.apolloinn.site/sub` |

## 4. 代理服务器（日本东京）

| 项目 | 值 |
|------|-----|
| IP | `43.206.212.53` |
| 域名 | `proxy-jp.apolloinn.site` |
| 平台 | AWS EC2 |
| 系统 | Ubuntu 24.04 |
| 登录 | `ssh -i apollo-jp.pem ubuntu@43.206.212.53` |
| 密钥 | `apollo-jp.pem`（与 API 日本服务器共用） |
| 服务 | Xray + nginx |
| 订阅 | `https://proxy-jp.apolloinn.site/sub` |

## Cloudflare DNS

| 记录 | 类型 | 值 | 代理 |
|------|------|-----|------|
| `api.apolloinn.site` | A | `18.223.114.145` | ✅ |
| `api2.apolloinn.site` | A | `34.222.159.160` | ✅ |
| `api3.apolloinn.site` | A | `52.195.205.77` | ✅ |
| `api-jp.apolloinn.site` | A | `52.195.205.77` | ❌（直连） |
| `proxy-us.apolloinn.site` | A | `44.248.224.204` | ✅ |
| `proxy-jp.apolloinn.site` | A | `43.206.212.53` | ✅ |
| `proxy-sg.apolloinn.site` | A | `207.148.73.138` | ✅ |
| `test.apolloinn.site` | A | `207.148.73.138` | ✅ |

## 数据库

| 环境 | 类型 | 地址 | 用途 |
|------|------|------|------|
| 生产（美东） | PostgreSQL（本地） | `localhost:5432/apollo`（18.223.114.145） | 主数据库，api2/api3 也连此库 |
| 测试 | PostgreSQL（本地） | `localhost:5432/apollo`（207.148.73.138） | 测试数据库 |
| 备份 | Supabase | 云端 | 仅备份，不作为主库使用 |

## UUID（代理共用）

```
e121a1a4-03a2-446a-8f5f-a1bbe38c63ec
```
