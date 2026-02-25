# -*- coding: utf-8 -*-
"""
Kiro Gateway Core — 上游 kiro-gateway 核心库。

提供 Kiro API 认证、格式转换、流式处理等基础能力。
Apollo Gateway 的 routes/ 和 services/ 层调用此包。

注意：此包的 import 按需进行（在各模块内 from core.xxx import ...），
不在 __init__.py 中预加载，避免启动时加载未使用的模块。
"""
