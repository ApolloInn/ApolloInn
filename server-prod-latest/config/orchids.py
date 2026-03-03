# -*- coding: utf-8 -*-
"""
Orchids (Orchids AI Coding Agent) 配置 — Clerk 认证、API URL、模型映射。
"""

import os


# ==================================================================================================
# Orchids Clerk Settings
# ==================================================================================================

ORCHIDS_CLERK_BASE_URL = os.getenv(
    "ORCHIDS_CLERK_BASE_URL",
    "https://clerk.orchids.app",
)
ORCHIDS_CLERK_API_VERSION = "2025-11-10"
ORCHIDS_CLERK_JS_VERSION = "5.117.0"

# ==================================================================================================
# Orchids API URLs
# ==================================================================================================

ORCHIDS_UPSTREAM_URL = os.getenv(
    "ORCHIDS_UPSTREAM_URL",
    "https://orchids-server.calmstone-6964e08a.westeurope.azurecontainerapps.io/agent/coding-agent",
)

ORCHIDS_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Orchids/0.0.57 Chrome/138.0.7204.251 Electron/37.10.3 Safari/537.36"
)

# 固定的 project ID（Orchids 内部使用）
ORCHIDS_DEFAULT_PROJECT_ID = "280b7bae-cd29-41e4-a0a6-7f603c43b607"

# ==================================================================================================
# Orchids Models
# ==================================================================================================

# agentMode 值来源: Orchids 客户端源码 MODEL_OPTIONS
# 仅包含 supportsOrchids=true 的模型
# 用户直接用 agentMode 值请求
ORCHIDS_MODELS = [
    # Claude
    "claude-sonnet-4-6",
    "claude-opus-4.6",
    "claude-haiku-4-5",
    # Gemini
    "gemini-3.1-pro",
    "gemini-3-flash",
    # GPT (GPT-5.3 Codex 不走 Orchids 服务端)
    "gpt-5.2-codex",
    "gpt-5.2",
    # 其他
    "grok-4.1-fast",
    "glm-5",
    "kimi-k2.5",
]

ORCHIDS_ONLY_MODELS = set(ORCHIDS_MODELS)

# 用户请求名 → agentMode（此处是直通映射，用户请求名就是 agentMode 值）
ORCHIDS_MODEL_MAP = {m: m for m in ORCHIDS_MODELS}
