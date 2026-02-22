# Apollo Gateway API 接入文档

## 基本信息

- 生产服务器（美东）：`https://api.apolloinn.site`
- 生产服务器（美西）：`https://api2.apolloinn.site`
- 生产服务器（日本）：`https://api3.apolloinn.site`
- 认证方式：Bearer Token（API Key）
- 兼容协议：OpenAI Chat Completions API / Anthropic Messages API

---

## 认证

所有请求需在 Header 中携带 API Key：

**OpenAI 协议：**
```
Authorization: Bearer <your-api-key>
```

**Anthropic 协议：**
```
x-api-key: <your-api-key>
```

---

## 三种接入路径

Apollo Gateway 提供三种不同的接入路径，适配不同客户端场景：

| 路径 | 完整端点 | 协议 | 适用场景 |
|------|---------|------|---------|
| Cursor 专用 | `https://api.apolloinn.site/v1/chat/completions` | OpenAI | Cursor IDE，自动处理 thinking 标签、重试、保活 |
| 标准 OpenAI | `https://api.apolloinn.site/standard/v1/chat/completions` | OpenAI | 通用 OpenAI 兼容客户端（ChatBox、LobeChat 等） |
| Anthropic 原生 | `https://api.apolloinn.site/v1/messages` | Anthropic | Anthropic SDK 客户端（Claude Code CLI 等） |

> 以上示例使用美东服务器，也可替换为 `api2.apolloinn.site`（美西）或 `api3.apolloinn.site`（日本）。

各路径对应的 Base URL 配置：

| 路径 | Base URL |
|------|----------|
| Cursor 专用 | `https://api.apolloinn.site/v1` |
| 标准 OpenAI | `https://api.apolloinn.site/standard/v1` |
| Anthropic 原生 | `https://api.apolloinn.site` |

> Cursor 专用路径内置了 thinking 标签转换、重试、保活等增强功能；标准路径只做纯净协议转换；Anthropic 路径原生透传 thinking block。

---

## 可用模型

| 模型 ID | 说明 |
|---------|------|
| `claude-opus-4.6` | Claude Opus 4.6 |
| `claude-sonnet-4.6` | Claude Sonnet 4.6 |
| `claude-opus-4.5` | Claude Opus 4.5 |
| `claude-sonnet-4.5` | Claude Sonnet 4.5 |
| `claude-sonnet-4` | Claude Sonnet 4 |
| `claude-haiku-4.5` | Claude Haiku 4.5 |
| `auto-kiro` | 自动选择模型 |

模型名称不区分大小写（如 `Claude-Opus-4.6` 会自动转为 `claude-opus-4.6`）。

**别名映射**（以下别名也可使用）：

| 别名 | 实际模型 |
|------|---------|
| `kiro-opus-4-6` | claude-opus-4.6 |
| `kiro-sonnet-4-6` | claude-sonnet-4.6 |
| `kiro-opus-4-5` | claude-opus-4.5 |
| `kiro-sonnet-4-5` | claude-sonnet-4.5 |
| `kiro-sonnet-4` | claude-sonnet-4 |
| `kiro-haiku-4-5` | claude-haiku-4.5 |
| `kiro-haiku` | claude-haiku-4.5 |
| `kiro-auto` | auto-kiro |

---

## 标准接口详解（推荐）

### `POST /standard/v1/chat/completions`

#### 请求体

```json
{
  "model": "claude-sonnet-4.6",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "stream": true,
  "reasoning_mode": "reasoning_content",
  "context_compression": true
}
```

#### 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | string | 是 | - | 模型 ID |
| `messages` | array | 是 | - | 消息列表，格式同 OpenAI |
| `stream` | boolean | 否 | false | 是否流式返回 |
| `tools` | array | 否 | - | 工具定义，格式同 OpenAI Function Calling |
| `reasoning_mode` | string | 否 | `"drop"` | 推理内容处理方式，见下方说明 |
| `context_compression` | boolean | 否 | `true` | 是否启用上下文压缩，见下方说明 |

#### `reasoning_mode` 参数

控制模型的推理过程（thinking）如何返回给客户端：

| 值 | 行为 |
|----|------|
| `"drop"` | **默认**。丢弃所有推理内容，只返回最终回答 |
| `"reasoning_content"` | 推理内容放在 `reasoning_content` 字段返回（与 OpenAI o1 格式一致） |
| `"content"` | 推理内容用 `<think>...</think>` 标签包裹后拼接到 `content` 字段 |

> **注意**：`reasoning_mode` 是扩展字段，非 OpenAI 官方参数。使用 OpenAI SDK 时需通过 `extra_body` 传递：
> ```python
> response = client.chat.completions.create(
>     model="claude-sonnet-4.6",
>     messages=[{"role": "user", "content": "Hello"}],
>     stream=True,
>     extra_body={"reasoning_mode": "reasoning_content"}
> )
> ```

#### `context_compression` 参数

控制是否对消息上下文进行自动压缩：

| 值 | 行为 |
|----|------|
| `true` | **默认**。当消息总 token 数接近模型上下文窗口时，自动压缩早期消息以避免超限 |
| `false` | 关闭压缩，消息原样透传。适合客户端自行管理上下文长度的场景 |

> **注意**：关闭压缩后，如果消息总长度超过模型上下文窗口，请求可能会失败。请确保客户端自行控制上下文长度。
>
> ```python
> response = client.chat.completions.create(
>     model="claude-sonnet-4.6",
>     messages=[{"role": "user", "content": "Hello"}],
>     extra_body={"context_compression": False}
> )
> ```

#### 流式响应示例（`reasoning_mode: "reasoning_content"`）

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","reasoning_content":"Let me think about this..."},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Hello! How can I help you?"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

#### 流式响应示例（`reasoning_mode: "content"`）

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":"<think>\nLet me think about this...\n</think>\n"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Hello! How can I help you?"},"finish_reason":null}]}

data: [DONE]
```

#### 非流式响应示例（`reasoning_mode: "reasoning_content"`）

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "claude-sonnet-4.6",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you?",
        "reasoning_content": "Let me think about this..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 50,
    "total_tokens": 75
  }
}
```

---

## Anthropic 接口详解

### `POST /v1/messages`

#### 请求体

```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 8096,
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "What's in this image?"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "..."}}
      ]
    }
  ],
  "stream": true
}
```

#### 参数说明

完全兼容 Anthropic Messages API 格式，主要参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | string | 是 | - | 模型 ID（支持 Apollo 别名和 Anthropic 原生名称） |
| `max_tokens` | integer | 是 | - | 最大输出 token 数 |
| `messages` | array | 是 | - | 消息列表，Anthropic 原生格式 |
| `system` | string/array | 否 | - | 系统提示词 |
| `stream` | boolean | 否 | false | 是否流式返回 |
| `tools` | array | 否 | - | 工具定义，Anthropic 原生格式 |
| `temperature` | number | 否 | - | 温度参数 |

#### 特性说明

- **Thinking**：模型推理过程通过原生 `thinking` content block 返回，客户端可自行折叠/展示
- **图片**：支持 base64 格式的 `image` content block，压缩路径中完整保留
- **工具调用**：支持 Anthropic 原生 `tool_use` / `tool_result` 格式
- **上下文压缩**：始终开启，长对话自动压缩

#### 流式响应格式

遵循 Anthropic SSE 规范：

```
event: message_start
data: {"type":"message_start","message":{"id":"msg_xxx","type":"message","role":"assistant","model":"claude-sonnet-4-20250514","usage":{"input_tokens":25,"output_tokens":1}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"thinking","thinking":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"thinking_delta","thinking":"Let me think..."}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: content_block_start
data: {"type":"content_block_start","index":1,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"text_delta","text":"Hello!"}}

event: content_block_stop
data: {"type":"content_block_stop","index":1}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":50}}

event: message_stop
data: {"type":"message_stop"}
```

---

## 快速接入示例

### Python（OpenAI SDK）

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key",
    base_url="https://api.apolloinn.site/standard/v1"
)

# 不需要推理过程
response = client.chat.completions.create(
    model="claude-sonnet-4.6",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)
for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Python（带推理内容）

```python
import httpx
import json

resp = httpx.post(
    "https://api.apolloinn.site/standard/v1/chat/completions",
    headers={"Authorization": "Bearer your-api-key"},
    json={
        "model": "claude-sonnet-4.6",
        "messages": [{"role": "user", "content": "What is 25 * 37?"}],
        "reasoning_mode": "reasoning_content",
        "stream": False
    }
)
data = resp.json()
msg = data["choices"][0]["message"]
print("Thinking:", msg.get("reasoning_content", ""))
print("Answer:", msg["content"])
```

### cURL

```bash
curl -X POST https://api.apolloinn.site/standard/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4.6",
    "messages": [{"role": "user", "content": "Hello!"}],
    "reasoning_mode": "drop",
    "stream": false
  }'
```

### Cursor IDE 接入

在 Cursor Settings → Models 中配置：

- **Override OpenAI Base URL**: `https://api.apolloinn.site/v1`
- **API Key**: 你的 API Key

Cursor 会自动使用 `/v1/chat/completions` 端点，推理内容会自动转为 `<think>` 标签格式。

### Python（Anthropic SDK）

```python
from anthropic import Anthropic

client = Anthropic(
    api_key="your-api-key",
    base_url="https://api.apolloinn.site"
)

# 流式调用
with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=8096,
    messages=[{"role": "user", "content": "Hello!"}],
) as stream:
    for event in stream:
        if event.type == "content_block_delta":
            if event.delta.type == "thinking_delta":
                print(f"[thinking] {event.delta.thinking}", end="")
            elif event.delta.type == "text_delta":
                print(event.delta.text, end="")
```

### Claude Code CLI 接入

```bash
# 设置环境变量
export ANTHROPIC_API_KEY="your-api-key"
export ANTHROPIC_BASE_URL="https://api.apolloinn.site"

# 直接使用
claude
```

---

## 错误码

| HTTP 状态码 | 说明 |
|------------|------|
| 401 | API Key 无效或缺失 |
| 403 | 账户已禁用或额度不足 |
| 422 | 请求体格式错误 |
| 429 | 请求过于频繁 |
| 503 | 服务暂时不可用（无可用 token） |
