# Server — 后端 API 服务

FastAPI 应用，核心网关逻辑。

## 目录结构

```
server/
├── app.py                  主入口，FastAPI 应用 + 生命周期管理
├── requirements.txt        Python 依赖
├── .env.example            环境变量模板
├── db/
│   └── schema.sql          PostgreSQL 建表语句
├── core/                   核心逻辑（无状态，纯函数/工具类）
│   ├── config.py           全局配置项（环境变量读取）
│   ├── auth.py             Kiro API 认证（SSO OIDC / refresh token）
│   ├── cache.py            模型信息缓存（ModelInfoCache）
│   ├── model_resolver.py   模型名归一化 + 解析（claude-4.6-opus → claude-opus-4.6）
│   ├── converters_openai.py    OpenAI 格式 → Kiro API 格式转换
│   ├── converters_anthropic.py Anthropic 格式 → Kiro API 格式转换
│   ├── converters_core.py      共享转换逻辑（消息合并、工具转换、thinking 注入）
│   ├── streaming_openai.py     OpenAI SSE 流式响应生成
│   ├── streaming_anthropic.py  Anthropic SSE 流式响应生成
│   ├── streaming_core.py       流式核心（Kiro API 调用 + 事件解析）
│   ├── thinking_parser.py      Thinking 块解析 FSM（<thinking> 标签处理）
│   ├── context_compression.py  上下文压缩（多级策略，154K→68K）
│   ├── truncation_recovery.py  截断恢复（API 返回不完整时自动重试）
│   ├── tokenizer.py            Token 计数
│   ├── http_client.py          HTTP 客户端封装
│   ├── exceptions.py           自定义异常
│   ├── kiro_errors.py          Kiro API 错误码映射
│   ├── network_errors.py       网络错误处理
│   ├── parsers.py              响应解析工具
│   ├── debug_logger.py         调试日志
│   └── utils.py                通用工具函数
├── routes/                 API 路由
│   ├── proxy.py            /v1/chat/completions, /v1/models（OpenAI 兼容）
│   ├── anthropic.py        /v1/messages（Anthropic 兼容）
│   ├── admin.py            /admin/*（Token 管理、用户管理、模型映射）
│   ├── user.py             /user/*（用户自助查询、API Key 管理）
│   └── agent.py            /agent/*（二级代理商接口）
└── services/               有状态服务
    ├── token_pool.py       Token 池管理（PostgreSQL，轮询分配、combo 模型解析）
    ├── auth_bridge.py      认证桥接（为每个 token 创建独立 AuthManager）
    ├── cursor_auth.py      Cursor Pro 账号认证
    └── cursor_utils.py     Cursor 工具函数
```

## 请求流程

```
客户端请求 → routes/proxy.py
  → token_pool 分配 token + 解析 combo 模型
  → converters_openai 转换为 Kiro 格式
  → context_compression 压缩上下文（如果超限）
  → streaming_core 调用 Kiro API
  → thinking_parser 解析 thinking 块
  → streaming_openai 生成 SSE 响应
  → 记录用量到 usage_records
```

## 关键配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `DATABASE_URL` | 必填 | PostgreSQL 连接串 |
| `LOG_LEVEL` | INFO | 日志级别 |
| `CONTEXT_COMPRESSION` | true | 上下文压缩开关 |
| `FAKE_REASONING_MAX_TOKENS` | 2500 | Thinking 模式最大 token 数 |
| `DEBUG_MODE` | off | 调试模式（off/errors/all/trace:用户名） |

## 修改指南

- 添加新 API 端点 → `routes/` 下新建或修改路由文件
- 修改模型映射逻辑 → `core/model_resolver.py`
- 调整压缩策略 → `core/context_compression.py`
- 修改 thinking 行为 → `core/thinking_parser.py` + `core/config.py`
- 添加新的 Token 类型 → `services/token_pool.py` + `db/schema.sql`
