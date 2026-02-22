# 服务器清单

## 1a. 生产服务器（日本 Tokyo）— 主力

| 项目 | 值 |
|------|-----|
| IP | `52.195.205.77` |
| 域名 | `api-jp.apolloinn.site` |
| 平台 | AWS EC2 (t3.small, 2C/2GB) |
| 系统 | Ubuntu 24.04 |
| 登录 | `ssh -i apollo-jp.pem ubuntu@52.195.205.77` |
| 服务 | Apollo Gateway（uvicorn + 2 workers）、PostgreSQL 16、nginx |
| 端口 | 8000（API）、80/443（nginx） |

## 1b. 生产服务器（美国 Ohio）— 备用

| 项目 | 值 |
|------|-----|
| IP | `18.223.114.145` |
| 域名 | `api.apolloinn.site` |
| 平台 | AWS EC2 |
| 系统 | Ubuntu |
| 登录 | `ssh -i apollo-key.pem ubuntu@18.223.114.145` |
| 服务 | Apollo Gateway（API 中转）、PostgreSQL、nginx |
| 端口 | 8000（API）、80/443（nginx） |

## 2. 代理服务器 - 美国（Oregon）

| 项目 | 值 |
|------|-----|
| IP | `44.248.224.204` |
| 域名 | `proxy-us.apolloinn.site` |
| 平台 | AWS EC2 (t3.micro) |
| 系统 | Ubuntu 24.04 |
| 登录 | `ssh -i apollo-proxy-key.pem ubuntu@44.248.224.204` |
| 密钥 | `apollo-proxy-key.pem`（项目根目录） |
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

## 3. 代理服务器（日本东京）

| 项目 | 值 |
|------|-----|
| IP | `43.206.212.53` |
| 域名 | `proxy-jp.apolloinn.site` |
| 平台 | AWS EC2 |
| 系统 | Ubuntu 24.04 |
| 登录 | SSH 密钥（`apollo-jp.pem`） |
| 服务 | Xray + nginx |
| 订阅 | `https://proxy-jp.apolloinn.site/sub` |

## Cloudflare DNS

| 记录 | 类型 | 值 | 代理 |
|------|------|-----|------|
| `api-jp.apolloinn.site` | A | `52.195.205.77` | ❌（直连） |
| `api.apolloinn.site` | A | `18.223.114.145` | ✅ |
| `proxy-sg.apolloinn.site` | A | `207.148.73.138` | ✅ |
| `proxy-us.apolloinn.site` | A | `44.248.224.204` | ✅ |
| `proxy-jp.apolloinn.site` | A | `43.206.212.53` | ✅ |
| `test.apolloinn.site` | A | `207.148.73.138` | ✅ |

## 数据库

| 环境 | 类型 | 地址 | 用途 |
|------|------|------|------|
| 生产（日本） | PostgreSQL 16（本地） | `localhost:5432/apollo`（52.195.205.77） | 主数据库 |
| 生产（美国） | PostgreSQL（本地） | `localhost:5432/apollo`（18.223.114.145） | 备用数据库 |
| 测试 | PostgreSQL（本地） | `localhost:5432/apollo`（207.148.73.138） | 测试数据库 |
| 备份 | Supabase | 云端 | 仅备份，不作为主库使用 |

## UUID（代理共用）

```
e121a1a4-03a2-446a-8f5f-a1bbe38c63ec
```
