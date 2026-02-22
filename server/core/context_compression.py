# -*- coding: utf-8 -*-
"""
Context Compression v2 — 基于优先级的动态剪枝系统。

设计哲学（参考 Cursor Priompt 架构）：
  不试图将所有信息"压缩"进 Prompt，而是通过精准的去重、骨架化和动态优先级
  渲染来确保只有最关键的信息进入有限的 Token 窗口。

核心原则：
  1. 幽灵文件去重（Ghost File Dedup）：同一文件多次读取只保留最后一次
  2. 已消化内容折叠：Agent 已处理过的 tool_result 可以激进压缩
  3. 结构化骨架化：代码文件保留 import + 签名 + 类型，删除实现体
  4. 分析模式渐进压缩：不是"全保护"，而是早期 skeleton + 最近完整
  5. 纯安全网：token 不超限就不动

工具感知压缩策略：
  Read       → AST 骨架化（保留文件名+import+签名+类型定义+docstring）
  Grep       → 保留文件路径+匹配行，压缩上下文行
  Shell      → 保留前5行+后20行+错误行，压缩中间输出
  Glob       → 不压缩（路径列表，通常很小）
  Write/Edit → 不压缩（确认消息，通常很短）
  HTML       → 提取 meta 信息 + 激进 head_tail（0.05 ratio）
  WebSearch  → head_tail 保留
  其他       → 通用策略（AST → 正则 → head_tail）

压缩层级（按需逐级触发）：
  Level 0:   不压缩（总 tokens < 阈值）
  Level 0.5: 幽灵文件去重 — 同文件多次读取只保留最后一次（零信息损失）
  Level 1:   清理截断重试循环 + 冗余去重 + 图片压缩（零/低信息损失）
  Level 2:   压缩早期大 tool_result — 按工具类型智能压缩（含分析模式的 Read）
  Level 2.5: 压缩 RECENT tool_result（更高阈值）
  Level 3:   压缩 assistant 长回复 — 决策摘要 + tool_use input 折叠
  Level 3.5: 压缩 assistant tool_calls arguments（OpenAI 格式）
  Level 4:   砍掉早期已消化的对话轮次
  Level 5:   激进压缩所有剩余 tool_result（最后手段）
"""

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


# ==================================================================================================
# grep_ast / Tree-sitter 初始化（可选依赖，失败则 fallback 到正则）
# ==================================================================================================
#
# 使用 grep_ast 的 TreeContext 做骨架化（参考 Aider 的 RepoMap 方案）。
# TreeContext 比手动 AST 遍历更紧凑：只渲染 Lines of Interest + 必要的父级作用域，
# 用 ⋮ 省略号标记折叠区域。实测压缩率 40-60%，且保留完整结构层次。
#
# grep_ast 内部自带 tree-sitter parser（通过 grep_ast.tsl），
# 不依赖 tree_sitter_languages，避免 tree-sitter 版本冲突。

_TS_AVAILABLE = False
_GREP_AST_AVAILABLE = False
_TS_PARSERS: Dict[str, Any] = {}  # language_name -> parser (grep_ast.tsl)

try:
    from grep_ast import TreeContext as _TreeContext, filename_to_lang as _filename_to_lang
    from grep_ast.tsl import get_parser as _grep_ast_get_parser
    _GREP_AST_AVAILABLE = True
    _TS_AVAILABLE = True  # 保持向后兼容（其他地方检查 _TS_AVAILABLE）
    logger.info("[Compression] grep_ast loaded OK (TreeContext + tree-sitter)")
except ImportError:
    try:
        from tree_sitter_languages import get_parser as _ts_get_parser_fallback
        _TS_AVAILABLE = True
        logger.info("[Compression] grep_ast not available, using tree_sitter_languages fallback")
    except ImportError:
        logger.warning(
            "[Compression] Neither grep_ast nor tree_sitter_languages installed, "
            "falling back to regex skeletonization. "
            "Install with: pip install grep-ast"
        )


# grep_ast 使用的语言名与 tree_sitter_languages 不同的映射
# 我们的 _EXT_TO_LANG 用 tree_sitter_languages 命名（如 "c_sharp"），
# 但 grep_ast.tsl.get_parser() 需要不同的名字（如 "csharp"）
_LANG_NAME_FIXES: Dict[str, str] = {
    "c_sharp": "csharp",
}


def _fix_lang_name(lang: str) -> str:
    """将 tree_sitter_languages 风格的语言名转换为 grep_ast 风格。"""
    return _LANG_NAME_FIXES.get(lang, lang)


def _get_ts_parser(lang: str):
    """获取指定语言的 tree-sitter parser，带缓存。优先用 grep_ast。"""
    if not _TS_AVAILABLE:
        return None
    if lang in _TS_PARSERS:
        return _TS_PARSERS[lang]
    try:
        if _GREP_AST_AVAILABLE:
            parser = _grep_ast_get_parser(_fix_lang_name(lang))
        else:
            parser = _ts_get_parser_fallback(lang)
        _TS_PARSERS[lang] = parser
        return parser
    except Exception:
        _TS_PARSERS[lang] = None
        return None


# 文件扩展名 -> tree-sitter 语言名
_EXT_TO_LANG: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".cs": "c_sharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".lua": "lua",
    ".r": "r",
    ".R": "r",
    ".hs": "haskell",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sql": "sql",
    ".md": "markdown",
    ".vue": "vue",
    ".svelte": "svelte",
    ".dart": "dart",
    ".zig": "zig",
}

# 各语言中需要保留签名的 AST 节点类型
# 这些节点的 body/block 子节点会被替换为 "// ..."
_SKELETON_NODE_TYPES: Dict[str, Dict[str, str]] = {
    # language -> {node_type -> body_field_name}
    "python": {
        "function_definition": "body",
        "class_definition": "body",
    },
    "javascript": {
        "function_declaration": "body",
        "method_definition": "body",
        "class_declaration": "body",
        "arrow_function": "body",
    },
    "typescript": {
        "function_declaration": "body",
        "method_definition": "body",
        "class_declaration": "body",
        "arrow_function": "body",
        "interface_declaration": "body",
    },
    "tsx": {
        "function_declaration": "body",
        "method_definition": "body",
        "class_declaration": "body",
        "arrow_function": "body",
        "interface_declaration": "body",
    },
    "java": {
        "method_declaration": "body",
        "class_declaration": "body",
        "interface_declaration": "body",
        "constructor_declaration": "body",
    },
    "go": {
        "function_declaration": "body",
        "method_declaration": "body",
    },
    "rust": {
        "function_item": "body",
        "impl_item": "body",
        "struct_item": "body",
    },
    "ruby": {
        "method": "body",
        "class": "body",
        "module": "body",
    },
    "php": {
        "function_definition": "body",
        "method_declaration": "body",
        "class_declaration": "body",
    },
    "c": {
        "function_definition": "body",
    },
    "cpp": {
        "function_definition": "body",
        "class_specifier": "body",
    },
    "c_sharp": {
        "method_declaration": "body",
        "class_declaration": "body",
        "interface_declaration": "body",
    },
    "swift": {
        "function_declaration": "body",
        "class_declaration": "body",
    },
    "kotlin": {
        "function_declaration": "function_body",
        "class_declaration": "class_body",
    },
}

# 各语言中始终完整保留的节点类型（import、注释、装饰器等）
_ALWAYS_KEEP_TYPES = {
    # Python
    "import_statement", "import_from_statement", "decorated_definition",
    "decorator",
    # JS/TS
    "import_statement", "export_statement",
    # Java
    "import_declaration", "package_declaration", "annotation",
    # Go
    "import_declaration", "package_clause",
    # Rust
    "use_declaration", "attribute_item", "mod_item",
    # Ruby
    "require", "require_relative",
    # PHP
    "namespace_definition", "use_declaration",
    # C/C++
    "preproc_include", "preproc_define", "preproc_ifdef",
    # C#
    "using_directive", "namespace_declaration",
    # 通用
    "comment", "line_comment", "block_comment", "doc_comment",
    "string", "expression_statement",  # docstrings
}


# ==================================================================================================
# Token Budget 配置
# ==================================================================================================

DEFAULT_CONTEXT_WINDOW = 128000

# 触发压缩的阈值 = 窗口 × ratio
# 注意：我们的 chars/2.5 估算比 Kiro API 实际 tokenizer 偏低 ~5-10%
# 所以触发线要留足余量，否则估算 82K 实际 88K 就漏过了
COMPRESSION_TRIGGER_RATIO = 0.70   # 90K / 128K — 输出已通过 chunked writing 限制，输入可以更宽松
COMPRESSION_TARGET_RATIO = 0.55    # 70K / 128K — 留 58K 给输出+工具定义，实际输出只用 ~4K tokens

# tool_result 压缩阈值：低于此字符数的不压缩
LARGE_RESULT_THRESHOLD = 1500

# chars -> tokens 估算系数（中英混合）
# 实测数据（37 次请求）：我们估算 130K 时 Kiro API 实际报 106K
# 实际 chars/token 比值约 2.8~3.2（中英混合+代码内容）
# 旧值 2.2 导致严重高估 token 数（25-35%），过度触发压缩
# 新值 2.8 更接近实际，减少不必要的压缩，保留更多上下文
CHARS_PER_TOKEN = 2.8


# ==================================================================================================
# 消息分区（Zone）配置 — 基于距离末尾的消息数（五区策略）
# ==================================================================================================
#
# 消息按距离末尾的位置分为五个区域，压缩力度递增：
#
#   Zone A（最近 10 条）  ：绝对保护，不动
#   Zone B（最近 11-30 条）：基本保留，只做去重和图片压缩
#   Zone C（最近 31-60 条）：中度压缩，AST 骨架化 + 工具摘要
#   Zone D（最近 61-120 条）：简要概要
#   Zone E（120 条之前）  ：直接删掉
#
#   [oldest ── Zone E ── Zone D ──── Zone C ──── Zone B ── Zone A]
#   [msg 0 ................................................msg N]

ZONE_A_SIZE = 10    # 绝对保护（最近 10 条）
ZONE_B_SIZE = 30    # 基本保留（最近 30 条，含 Zone A）
ZONE_C_SIZE = 60    # 中度压缩（最近 60 条，含 Zone A+B）
ZONE_D_SIZE = 120   # 简要概要（最近 120 条，含 Zone A+B+C）
# Zone E = 120 条之前，直接删掉


# ==================================================================================================
# 优先级常量（兼容旧代码，部分辅助函数仍使用）
# ==================================================================================================

PRIORITY_SYSTEM = 100
PRIORITY_LAST_USER = 95
PRIORITY_ERROR_DIAG = 90
PRIORITY_RECENT = 80
PRIORITY_NORMAL = 50
PRIORITY_EARLY_RESULT = 30
PRIORITY_EARLY_ASSISTANT = 20

# 兼容旧代码引用
RECENT_MESSAGES_PROTECTED = ZONE_B_SIZE
ABSOLUTE_PROTECTED_MESSAGES = ZONE_A_SIZE


# ==================================================================================================
# Token 估算
# ==================================================================================================

def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return int(len(text) / CHARS_PER_TOKEN)


def estimate_request_tokens(
    messages: List[Dict[str, Any]],
    tools: Optional[List] = None,
) -> int:
    total = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total += _estimate_tokens(content)
        elif isinstance(content, list):
            total += _estimate_tokens(json.dumps(content, ensure_ascii=False))
        tc = m.get("tool_calls", [])
        if tc:
            total += _estimate_tokens(json.dumps(tc, ensure_ascii=False))
    if tools:
        total += _estimate_tokens(json.dumps(tools, ensure_ascii=False))
    return total


# ==================================================================================================
# tool_result 内容读写工具函数
# ==================================================================================================

def _get_result_text(block: Dict[str, Any]) -> str:
    """
    从 tool_result block 中提取纯文本内容。

    Cursor 的 tool_result 格式多样：
      1. content: "plain string"
      2. content: [{"type": "text", "text": "..."}]
      3. content 不存在，直接有 text 字段
    """
    bc = block.get("content", "")
    if isinstance(bc, str):
        return bc
    if isinstance(bc, list):
        parts = []
        for sub in bc:
            if isinstance(sub, dict) and sub.get("type") == "text":
                parts.append(sub.get("text", ""))
            elif isinstance(sub, str):
                parts.append(sub)
        return "\n".join(parts)
    return block.get("text", "")


def _set_result_text_inplace(block: Dict[str, Any], new_text: str) -> None:
    """原地替换 tool_result block 的文本内容，保持原有格式结构。"""
    bc = block.get("content", "")
    if isinstance(bc, str):
        block["content"] = new_text
    elif isinstance(bc, list):
        block["content"] = [{"type": "text", "text": new_text}]
    else:
        block["content"] = new_text


def _apply_block_compressions(
    msg: Dict[str, Any],
    block_map: Dict[int, str],
) -> Dict[str, Any]:
    """对消息中指定的 content blocks 应用压缩文本。"""
    new_m = dict(msg)
    new_content = []
    for j, block in enumerate(msg["content"]):
        if j in block_map:
            new_block = dict(block)
            _set_result_text_inplace(new_block, block_map[j])
            new_content.append(new_block)
        else:
            new_content.append(block)
    new_m["content"] = new_content
    return new_m


# ==================================================================================================
# Tool ID → 文件名映射（精确语言检测）
# ==================================================================================================

def _build_tool_id_to_path(messages: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    从 assistant 消息的 tool_calls / tool_use 中提取 tool_call_id → file_path 映射。

    这样在处理 tool_result 时，可以通过 tool_use_id 精确获取文件路径和语言，
    不需要从 tool_result 文本内容中猜测。
    """
    id_map: Dict[str, str] = {}

    for m in messages:
        if m.get("role") != "assistant":
            continue

        # OpenAI 格式: tool_calls 字段
        tc = m.get("tool_calls") or []
        for call in tc:
            if not isinstance(call, dict):
                continue
            call_id = call.get("id", "")
            func = call.get("function", {})
            name = func.get("name", "")
            # 只关心读文件类工具
            if name not in ("Read", "read_file", "ReadFile", "read", "Grep", "grep", "Search"):
                continue
            args_str = func.get("arguments", "")
            if not args_str:
                continue
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except (json.JSONDecodeError, TypeError):
                continue
            path = args.get("path") or args.get("relative_workspace_path") or args.get("filePath") or ""
            if path and call_id:
                id_map[call_id] = path

        # Anthropic 格式: content list with tool_use blocks
        content = m.get("content", "")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                block_id = block.get("id", "")
                name = block.get("name", "")
                if name not in ("Read", "read_file", "ReadFile", "read", "Grep", "grep", "Search"):
                    continue
                inp = block.get("input", {})
                if not isinstance(inp, dict):
                    continue
                path = inp.get("path") or inp.get("relative_workspace_path") or inp.get("filePath") or ""
                if path and block_id:
                    id_map[block_id] = path

    return id_map


def _build_tool_id_to_name(messages: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    从 assistant 消息的 tool_calls / tool_use 中提取 tool_call_id → tool_name 映射。

    用于在压缩 tool_result 时，精确知道是哪个工具产生的结果，
    从而选择对应的压缩策略（Read → AST 骨架化，Shell → head_tail 等）。
    """
    id_map: Dict[str, str] = {}

    for m in messages:
        if m.get("role") != "assistant":
            continue

        # OpenAI 格式: tool_calls 字段
        tc = m.get("tool_calls") or []
        for call in tc:
            if not isinstance(call, dict):
                continue
            call_id = call.get("id", "")
            func = call.get("function", {})
            name = func.get("name", "")
            if call_id and name:
                id_map[call_id] = name

        # Anthropic 格式: content list with tool_use blocks
        content = m.get("content", "")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                block_id = block.get("id", "")
                name = block.get("name", "")
                if block_id and name:
                    id_map[block_id] = name

    return id_map


def _get_tool_result_id(block: Dict[str, Any]) -> str:
    """从 tool_result block 中提取 tool_use_id。"""
    return block.get("tool_use_id", "") or block.get("tool_call_id", "")


# ==================================================================================================
# 分析模式检测
# ==================================================================================================

def _detect_subagent_mode(messages: List[Dict[str, Any]]) -> bool:
    """
    检测是否是 Cursor subagent（文件搜索/分析子任务）。

    Cursor 的分析模式会派出 subagent 并行读取大量文件。
    subagent 的 Read 结果是分析"原材料"，只允许 AST 骨架化，
    不允许 head_tail 截断、pair dropping、assistant 摘要化等破坏性压缩。

    检测方式：扫描 user 消息中的 text 内容，查找 subagent 特征指令。
    Cursor subagent 的 user 消息会包含：
      - "file search specialist" — subagent 角色声明
      - "READ-ONLY MODE" — 只读模式标记
      - "read-only exploration task" — 只读探索任务标记
    """
    _SUBAGENT_MARKERS = [
        "file search specialist",
        "read-only mode",
        "read-only exploration task",
    ]

    for m in messages:
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if isinstance(content, str):
            lower = content[:2000].lower()
            for marker in _SUBAGENT_MARKERS:
                if marker in lower:
                    return True
        elif isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "text":
                    text = b.get("text", "")
                    lower = text[:2000].lower()
                    for marker in _SUBAGENT_MARKERS:
                        if marker in lower:
                            return True
    return False


# ==================================================================================================
# Tree-sitter AST 骨架化（核心压缩引擎）
# ==================================================================================================

def _detect_language_from_text(text: str, hint_path: str = "") -> Optional[str]:
    """
    从 tool_result 文本中检测编程语言。

    检测策略（按优先级）：
      0. 如果有 hint_path（从 tool_id 映射获得），直接用扩展名
      1. 从前几行提取文件路径 → 扩展名 → 语言
      2. 去除行号前缀后做内容特征检测（扫描前 80 行）
      3. 从内容特征启发式判断
    """
    # 策略 0: 精确路径提示（来自 tool_id → path 映射）
    if hint_path:
        lang = _ext_to_lang(hint_path)
        if lang:
            return lang

    lines = text.strip().split("\n", 80)

    # 策略 1: 直接从前几行找文件路径
    for line in lines[:5]:
        line = line.strip()
        # 去除行号前缀
        ln_match = re.match(r'^\s*\d+\|(.*)', line)
        if ln_match:
            line = ln_match.group(1).strip()
        # 绝对路径
        if line.startswith("/") and not line.startswith("//"):
            lang = _ext_to_lang(line)
            if lang:
                return lang
        if len(line) > 2 and line[1] == ":" and line[2] in ("/", "\\"):
            lang = _ext_to_lang(line)
            if lang:
                return lang
        # "Content of file.ts:" 或路径片段
        path_match = re.search(r'[\w/\\.-]+\.(\w+)', line)
        if path_match:
            ext = "." + path_match.group(1).lower()
            if ext in _EXT_TO_LANG:
                return _EXT_TO_LANG[ext]

    # 策略 2: 去除行号后做内容特征检测（扫描更多行以覆盖长 JSDoc 头部）
    clean_lines = []
    for line in lines[:80]:
        ln_match = re.match(r'^\s*\d+\|(.*)', line)
        if ln_match:
            clean_lines.append(ln_match.group(1))
        else:
            clean_lines.append(line)
    sample = "\n".join(clean_lines)

    # ── Python 检测（最先，因为 self. 是极强特征）──
    # self.xxx 是 Python 独有特征（JS/TS 用 this.）
    has_self = bool(re.search(r'\bself\.\w+', sample))
    has_def = bool(re.search(r'^\s*def\s+\w+', sample, re.MULTILINE))
    has_class_py = bool(re.search(r'^\s*class\s+\w+.*:', sample, re.MULTILINE))
    has_import_py = bool(re.search(r'^(from|import)\s+\w+', sample, re.MULTILINE))
    has_decorator = bool(re.search(r'^\s*@\w+', sample, re.MULTILINE))

    # self. + (def | class | import | @decorator) → 确定是 Python
    if has_self and (has_def or has_class_py or has_import_py or has_decorator):
        return "python"
    # import + def/class → Python
    if has_import_py and (has_def or has_class_py):
        return "python"
    # 纯 self. 出现多次（代码片段没有 def/class 但满是 self.xxx）
    if has_self and sample.count("self.") >= 3:
        return "python"

    # ── TypeScript/JavaScript ──
    # import/export 是 JS/TS 强特征（Python 的 import 已在上面处理）
    if re.search(r'^\s*(import|export)\s+(type\s+)?[{*\w]', sample, re.MULTILINE):
        return "typescript"
    # const/let/var + 赋值（但排除 Python 的 self.xxx 场景）
    if re.search(r'^\s*(const|let|var)\s+\w+\s*[=:]', sample, re.MULTILINE):
        return "typescript"
    if re.search(r'^\s*(interface|type)\s+\w+\s*[{=<]', sample, re.MULTILINE):
        return "typescript"
    # JSDoc 开头 + JS/TS 关键字
    if re.search(r'/\*\*', sample) and re.search(r'\b(function|const|export|import|async|await|=>|module|require)\b', sample):
        return "typescript"
    # 纯 JSDoc 开头
    first_non_empty = ""
    for cl in clean_lines[:5]:
        if cl.strip():
            first_non_empty = cl.strip()
            break
    if first_non_empty.startswith("/**"):
        return "typescript"
    # this.xxx 是 JS/TS 特征（区别于 Python 的 self.）
    if re.search(r'\bthis\.\w+', sample) and re.search(r'\b(function|class|const|let|var|=>)\b', sample):
        return "typescript"

    # ── Go ──
    if re.search(r'^package\s+\w+', sample, re.MULTILINE):
        if re.search(r'^import\s*\(', sample, re.MULTILINE) or re.search(r'^func\s+', sample, re.MULTILINE):
            return "go"
    # ── Java ──
    if re.search(r'^package\s+[\w.]+;', sample, re.MULTILINE):
        return "java"
    # ── Rust ──
    if re.search(r'^(use|fn|pub|mod|struct|impl)\s+', sample, re.MULTILINE):
        return "rust"
    # ── Markdown ──
    if re.search(r'^#{1,3}\s+', sample, re.MULTILINE) and sample.count('#') > 3:
        return "markdown"

    # ── Python fallback（只有 import，没有 def/class）──
    if has_import_py:
        return "python"
    # ── Python 弱特征 fallback（有 def 或 class:）──
    if has_def or has_class_py:
        return "python"

    return None


def _ext_to_lang(path: str) -> Optional[str]:
    """从文件路径提取扩展名并映射到 tree-sitter 语言名。"""
    for ext, lang in _EXT_TO_LANG.items():
        if path.rstrip().endswith(ext):
            return lang
    return None


def _strip_line_numbers(text: str) -> Tuple[str, bool]:
    """
    去除 Cursor Read 工具的行号前缀。

    Cursor 格式: "123|code here"
    返回: (去除行号后的纯代码, 是否有行号)
    """
    lines = text.split("\n")
    has_line_nums = False
    clean_lines = []

    # 检查前 5 行是否有行号格式
    check_count = 0
    for line in lines[:10]:
        if re.match(r'^\s*\d+\|', line):
            check_count += 1
    has_line_nums = check_count >= 3

    if not has_line_nums:
        return text, False

    for line in lines:
        m = re.match(r'^\s*\d+\|(.*)', line)
        if m:
            clean_lines.append(m.group(1))
        else:
            clean_lines.append(line)

    return "\n".join(clean_lines), True


def _skeletonize_with_treesitter(text: str, lang: str) -> Optional[str]:
    """
    用 grep_ast TreeContext 做精确 AST 骨架化（参考 Aider RepoMap 方案）。

    核心思路：
      1. 用 tree-sitter 解析代码，找到所有定义节点（函数、类、import 等）的行号
      2. 将这些行号作为 Lines of Interest (LOI) 传给 TreeContext
      3. TreeContext 自动渲染 LOI + 必要的父级作用域，用 ⋮ 折叠其余部分

    优势（vs 旧的手动 AST 遍历 + 字节替换）：
      - 更紧凑：只渲染必要行，不保留空的函数体占位符
      - 更准确：TreeContext 理解作用域嵌套，自动保留必要的上下文
      - 更通用：不需要为每种语言维护 body_field_name 映射表
      - 更稳定：不做字节级替换，避免 UTF-8 编码偏移问题

    返回 None 表示 grep_ast 不可用或解析失败。
    """
    # ── 优先使用 grep_ast TreeContext（更紧凑的输出）──
    if _GREP_AST_AVAILABLE:
        return _skeletonize_with_grep_ast_tc(text, lang)

    # ── Fallback: 旧的 tree-sitter 手动遍历方式 ──
    return _skeletonize_with_treesitter_legacy(text, lang)


def _collect_definition_lines(node, depth: int = 0, in_function_body: bool = False) -> set:
    """
    递归遍历 AST，收集所有定义节点的起始行号。

    参考 Aider 的 tags query 策略（业内最佳实践）：
      - 只标记真正的"定义"节点：function、class、interface、type、enum
      - 不标记 import/export（TreeContext 会自动保留文件顶部上下文）
      - 不标记 arrow_function（内部函数表达式不是顶级定义）
      - 不标记函数体内的嵌套定义（TreeContext 会自动折叠）

    这样 TreeContext 只渲染定义行 + 必要的父级作用域，其余全部折叠为 ⋮。
    """
    lines = set()
    node_type = node.type

    # ── 真正的定义节点（参考 Aider 的 *-tags.scm）──
    # Python: class_definition, function_definition
    # JS/TS: function_declaration, method_definition, class_declaration,
    #         interface_declaration, type_alias_declaration, enum_declaration
    # Go: function_declaration, method_declaration, type_declaration
    # Rust: function_item, struct_item, impl_item, trait_item, enum_item
    # Java: method_declaration, class_declaration, interface_declaration, constructor_declaration
    # C/C++: function_definition, class_specifier (struct/class)
    _REAL_DEFINITION_TYPES = {
        # 函数/方法
        "function_definition", "function_declaration",
        "method_definition", "method_declaration",
        "constructor_declaration",
        "function_item",  # Rust
        # 类/接口/结构体
        "class_definition", "class_declaration", "class_specifier",
        "interface_declaration",
        "abstract_class_declaration",
        "struct_item", "impl_item", "trait_item",  # Rust
        "enum_declaration", "enum_item",
        "type_alias_declaration",
        # Go
        "type_declaration",
        # 装饰器包裹的定义（Python @decorator）
        "decorated_definition",
        # Module (TypeScript namespace, Ruby module)
        "module",
    }

    if node_type in _REAL_DEFINITION_TYPES:
        lines.add(node.start_point[0])

    # 递归子节点
    for child in node.children:
        lines |= _collect_definition_lines(child, depth + 1)
    return lines


def _skeletonize_with_grep_ast_tc(text: str, lang: str) -> Optional[str]:
    """
    使用 grep_ast TreeContext 渲染代码骨架。

    流程：
      1. 去除 Cursor 行号前缀（TreeContext 需要纯代码）
      2. 提取文件路径头（如果有）
      3. 用 tree-sitter 解析，收集定义行号
      4. TreeContext 渲染 LOI + 父级作用域
      5. 清理输出格式（去除 │ 前缀）
    """
    # 去除行号前缀
    clean_text, had_line_nums = _strip_line_numbers(text)

    # 提取文件路径头
    lines = clean_text.split("\n")
    header_line = ""
    if lines and (lines[0].strip().startswith("/") or
                  (len(lines[0].strip()) > 2 and lines[0].strip()[1] == ":")):
        header_line = lines[0]
        clean_text = "\n".join(lines[1:])

    # 确保以换行结尾（TreeContext 要求）
    if not clean_text.endswith("\n"):
        clean_text += "\n"

    # 解析 AST
    try:
        parser = _grep_ast_get_parser(_fix_lang_name(lang))
        tree = parser.parse(clean_text.encode("utf-8"))
    except Exception as e:
        logger.debug(f"[Compression] grep_ast parse failed for {lang}: {e}")
        return None

    root = tree.root_node
    if root.has_error and root.named_child_count == 0:
        return None

    # 收集定义行号
    def_lines = _collect_definition_lines(root)
    if not def_lines:
        return None

    # 构造文件名用于 TreeContext 语言检测
    # grep_ast 的 filename_to_lang 需要文件名来确定语言
    _LANG_TO_EXT = {
        "python": "f.py", "javascript": "f.js", "typescript": "f.ts",
        "tsx": "f.tsx", "java": "f.java", "go": "f.go", "rust": "f.rs",
        "ruby": "f.rb", "php": "f.php", "c": "f.c", "cpp": "f.cpp",
        "c_sharp": "f.cs", "swift": "f.swift", "kotlin": "f.kt",
        "scala": "f.scala", "lua": "f.lua", "dart": "f.dart",
        "zig": "f.zig", "vue": "f.vue", "svelte": "f.svelte",
        "bash": "f.sh", "html": "f.html", "css": "f.css",
    }
    fake_fname = _LANG_TO_EXT.get(lang, f"f.{lang}")

    try:
        tc = _TreeContext(
            fake_fname,
            clean_text,
            color=False,
            line_number=False,
            child_context=False,
            last_line=False,
            margin=0,
            mark_lois=False,
            loi_pad=0,
            show_top_of_file_parent_scope=True,  # 保留文件顶部 import 区域
        )
        tc.add_lines_of_interest(def_lines)
        tc.add_context()
        result = tc.format()
    except Exception as e:
        logger.debug(f"[Compression] TreeContext format failed for {lang}: {e}")
        return None

    if not result or not result.strip():
        return None

    # 清理 TreeContext 输出格式：
    # - 去除 │ 前缀（TreeContext 用它标记可见行）
    # - 保留 ⋮ 省略号标记
    cleaned_lines = []
    for line in result.split("\n"):
        if line.startswith("│"):
            cleaned_lines.append(line[1:])  # 去除 │ 前缀
        elif line.startswith("⋮"):
            cleaned_lines.append("...")  # 替换为通用省略号
        else:
            cleaned_lines.append(line)
    result = "\n".join(cleaned_lines)

    # 恢复文件路径头
    if header_line:
        result = header_line + "\n" + result

    return result


def _skeletonize_with_treesitter_legacy(text: str, lang: str) -> Optional[str]:
    """
    旧版 tree-sitter 骨架化（当 grep_ast 不可用时的 fallback）。

    使用 tree_sitter_languages 解析，手动遍历 AST 替换函数体。
    比 grep_ast TreeContext 输出更冗长，但仍比纯正则好。
    """
    parser = _get_ts_parser(lang)
    if parser is None:
        return None

    clean_text, had_line_nums = _strip_line_numbers(text)

    lines = clean_text.split("\n")
    header_line = ""
    if lines and (lines[0].strip().startswith("/") or
                  (len(lines[0].strip()) > 2 and lines[0].strip()[1] == ":")):
        header_line = lines[0]
        clean_text = "\n".join(lines[1:])

    try:
        tree = parser.parse(clean_text.encode("utf-8"))
    except Exception as e:
        logger.debug(f"[Compression] tree-sitter legacy parse failed for {lang}: {e}")
        return None

    root = tree.root_node
    if root.has_error and root.named_child_count == 0:
        return None

    skeleton_types = _SKELETON_NODE_TYPES.get(lang, {})
    source_bytes = clean_text.encode("utf-8")
    source_lines = clean_text.split("\n")

    _CONTAINER_TYPES = {
        "class_definition", "class_declaration", "class_specifier",
        "interface_declaration", "impl_item", "module",
        "namespace_declaration",
    }

    replacements = []

    def _walk(node):
        node_type = node.type
        if node_type in skeleton_types:
            body_field = skeleton_types[node_type]
            body_node = node.child_by_field_name(body_field)
            if node_type in _CONTAINER_TYPES:
                for child in node.children:
                    _walk(child)
                return
            if body_node is not None:
                body_start_line = body_node.start_point[0]
                body_end_line = body_node.end_point[0]
                body_lines = body_end_line - body_start_line + 1
                if body_lines > 3:
                    indent = ""
                    if body_start_line < len(source_lines):
                        body_first_line = source_lines[body_start_line]
                        indent = body_first_line[:len(body_first_line) - len(body_first_line.lstrip())]
                    if lang == "python":
                        replacement = f"\n{indent}    # ... ({body_lines} lines)\n{indent}    pass"
                    else:
                        replacement = f" {{ /* ... ({body_lines} lines) */ }}"
                    replacements.append((body_node.start_byte, body_node.end_byte, replacement))
                    for child in node.children:
                        if child.id != body_node.id:
                            _walk(child)
                    return
        for child in node.children:
            _walk(child)

    _walk(root)

    if not replacements:
        return None

    replacements.sort(key=lambda r: -r[0])
    result_bytes = bytearray(source_bytes)
    for start, end, replacement in replacements:
        result_bytes[start:end] = replacement.encode("utf-8")

    result = result_bytes.decode("utf-8", errors="replace")
    if header_line:
        result = header_line + "\n" + result
    return result


# ==================================================================================================
# 正则骨架化（Fallback）
# ==================================================================================================

_SIGNATURE_PATTERNS = [
    re.compile(r"^(\s*)(async\s+)?def\s+\w+\s*\(.*$"),
    re.compile(r"^(\s*)class\s+\w+.*:"),
    re.compile(r"^(\s*)(export\s+)?(async\s+)?function\s+\w+"),
    re.compile(r"^(\s*)(export\s+)?(const|let|var)\s+\w+\s*=\s*(async\s+)?\("),
    re.compile(r"^(\s*)(export\s+)?class\s+\w+"),
    re.compile(r"^(\s*)(export\s+)?(interface|type|enum)\s+\w+"),
    re.compile(r"^(\s*)(public|private|protected|static|final|abstract|override|virtual|async)\s+"),
    re.compile(r"^(\s*)func\s+"),
    re.compile(r"^(\s*)type\s+\w+\s+(struct|interface)"),
    re.compile(r"^(\s*)(pub\s+)?fn\s+\w+"),
    re.compile(r"^(\s*)(pub\s+)?struct\s+\w+"),
    re.compile(r"^(\s*)impl\s+"),
]

_IMPORT_PATTERNS = [
    re.compile(r"^(\s*)(import|from)\s+"),
    re.compile(r"^(\s*)(const|let|var)\s+.*require\("),
    re.compile(r"^(\s*)#include\s+"),
    re.compile(r"^(\s*)using\s+"),
    re.compile(r"^(\s*)package\s+"),
]

_DECORATOR_PATTERN = re.compile(r"^(\s*)@\w+")


def _is_signature_line(line: str) -> bool:
    for pat in _SIGNATURE_PATTERNS:
        if pat.match(line):
            return True
    return False


def _is_import_line(line: str) -> bool:
    for pat in _IMPORT_PATTERNS:
        if pat.match(line):
            return True
    return False


def _looks_like_code(text: str) -> bool:
    """启发式判断文本是否是代码。"""
    lines = text.split("\n", 30)
    code_indicators = 0
    for line in lines[:30]:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^\d+\|", stripped):
            code_indicators += 2
        if any(c in stripped for c in ["{", "}", "()", "=>", "->", "::", ";"]):
            code_indicators += 1
        if _is_import_line(stripped) or _is_signature_line(stripped):
            code_indicators += 2
    return code_indicators >= 5


def _skeletonize_markdown(text: str) -> Optional[str]:
    """
    Markdown 骨架化：保留标题、列表项首行、代码块声明行，去掉正文段落。

    保留：
      - # / ## / ### 等标题行
      - - / * / 数字. 列表项（只保留首行）
      - ```language 代码块的开头和结尾标记
      - 表格行（| 开头）
      - 行号前缀会先去除再判断
    去掉：
      - 纯文本段落（连续的非结构行）
      - 代码块内部内容（只保留 ```lang ... ```）
    """
    raw_lines = text.split("\n")
    # 去除行号前缀
    lines = []
    for line in raw_lines:
        m = re.match(r'^\s*\d+\|(.*)', line)
        lines.append(m.group(1) if m else line)

    kept = []
    in_code_block = False
    skipped = 0

    for line in lines:
        stripped = line.strip()

        # 代码块边界
        if stripped.startswith("```"):
            if in_code_block:
                # 结束代码块
                kept.append(line)
                in_code_block = False
            else:
                # 开始代码块 — 如果之前有跳过的行，标记一下
                if skipped > 0:
                    kept.append(f"  ... [{skipped} lines] ...")
                    skipped = 0
                kept.append(line)
                in_code_block = True
            continue

        if in_code_block:
            skipped += 1
            continue

        # 标题行
        if re.match(r'^#{1,6}\s', stripped):
            if skipped > 0:
                kept.append(f"  ... [{skipped} lines] ...")
                skipped = 0
            kept.append(line)
            continue

        # 列表项
        if re.match(r'^[-*]\s|^\d+\.\s', stripped):
            if skipped > 0:
                kept.append(f"  ... [{skipped} lines] ...")
                skipped = 0
            kept.append(line)
            continue

        # 表格行
        if stripped.startswith("|"):
            if skipped > 0:
                kept.append(f"  ... [{skipped} lines] ...")
                skipped = 0
            kept.append(line)
            continue

        # 空行 — 保留（结构分隔）
        if not stripped:
            if skipped > 0:
                kept.append(f"  ... [{skipped} lines] ...")
                skipped = 0
            kept.append("")
            continue

        # 其他正文 — 跳过
        skipped += 1

    if skipped > 0:
        kept.append(f"  ... [{skipped} lines] ...")

    result = "\n".join(kept)
    # 只有压缩了足够多才返回
    if len(result) < len(text) * 0.90:
        return result
    return None


def _skeletonize_with_regex(text: str) -> str:
    """正则骨架化：保留 import + 签名 + 注释，实现体替换为 ..."""
    lines = text.split("\n")
    kept = []
    skip_body = False
    body_indent = 0
    skipped_count = 0
    in_header = True

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if in_header or not skip_body:
                kept.append(line)
            continue

        clean_line = line
        line_num_match = re.match(r"^(\d+\|)(.*)", line)
        if line_num_match:
            clean_line = line_num_match.group(2)
        clean_stripped = clean_line.strip()

        if _is_import_line(clean_stripped):
            kept.append(line)
            continue

        if _DECORATOR_PATTERN.match(clean_stripped):
            in_header = False
            skip_body = False
            kept.append(line)
            continue

        if _is_signature_line(clean_stripped):
            in_header = False
            if skip_body and skipped_count > 0:
                kept.append(f"{'  ' * body_indent}  // ... ({skipped_count} lines)")
                skipped_count = 0
            skip_body = True
            body_indent = len(clean_line) - len(clean_line.lstrip())
            kept.append(line)
            continue

        if clean_stripped.startswith(("#", "//", "/*", "*", "'''", '"""')):
            if not skip_body:
                kept.append(line)
            continue

        if skip_body:
            current_indent = len(clean_line) - len(clean_line.lstrip())
            if current_indent <= body_indent and clean_stripped:
                if skipped_count > 0:
                    kept.append(f"{'  ' * (body_indent + 1)}// ... ({skipped_count} lines)")
                    skipped_count = 0
                skip_body = False
                if _is_signature_line(clean_stripped):
                    body_indent = current_indent
                    skip_body = True
                    kept.append(line)
                    continue
                kept.append(line)
            else:
                skipped_count += 1
            continue

        in_header = False
        kept.append(line)

    if skip_body and skipped_count > 0:
        kept.append(f"{'  ' * (body_indent + 1)}// ... ({skipped_count} lines)")

    return "\n".join(kept)


# ==================================================================================================
# Markdown 报告结构化压缩（Task subagent 报告等）
# ==================================================================================================

def _is_markdown_report(text: str) -> bool:
    """
    检测文本是否是 Markdown 格式的分析报告。

    Task subagent 返回的报告特征：
      - 以 "This is the last output of the subagent:" 开头
      - 包含 ## / ### 标题
      - 包含 Markdown 列表（- xxx）
      - 包含代码块引用（```...```）
    """
    if len(text) < 500:
        return False

    lines = text.split("\n", 60)
    heading_count = 0
    list_count = 0
    has_subagent_prefix = False

    for line in lines[:60]:
        stripped = line.strip()
        if "subagent" in stripped.lower() or "last output" in stripped.lower():
            has_subagent_prefix = True
        if re.match(r'^#{1,4}\s+', stripped):
            heading_count += 1
        if re.match(r'^[-*]\s+', stripped):
            list_count += 1

    # 有 subagent 前缀 + 标题 → 确定是报告
    if has_subagent_prefix and heading_count >= 2:
        return True
    # 大量标题 + 列表 → Markdown 报告
    if heading_count >= 3 and list_count >= 3:
        return True
    # 标题密度高（每 20 行至少 1 个标题）
    if heading_count >= 2 and heading_count / max(len(lines), 1) > 0.03:
        return True

    return False


def _compress_markdown_report(text: str, keep_ratio: float = 0.3) -> str:
    """
    结构化压缩 Markdown 分析报告。

    保留高信息密度内容：
      - 所有标题行（## xxx, ### xxx）
      - 列表项（- xxx, * xxx, 1. xxx）
      - 代码块（```...```）— 短的完整保留，长的 head_tail
      - 粗体行（**xxx**）
      - 文件路径行
      - 表格行

    压缩低信息密度内容：
      - 纯段落解释文字 → 只保留首句
      - Agent ID 尾部标记 → 删除
    """
    lines = text.split("\n")
    kept = []
    in_code_block = False
    code_block_lines = []
    paragraph_buffer = []  # 连续的纯段落行
    list_count_in_section = 0

    def _flush_paragraph():
        """将段落缓冲区压缩后输出 — 只保留首句。"""
        if not paragraph_buffer:
            return
        combined = " ".join(l.strip() for l in paragraph_buffer)
        if len(combined) <= 150:
            # 短段落：完整保留
            for line in paragraph_buffer:
                kept.append(line)
        else:
            # 长段落：只保留第一句（到第一个句号）
            first_line = paragraph_buffer[0]
            # 尝试在第一行找句号截断
            for end_mark in [". ", "。"]:
                pos = first_line.find(end_mark)
                if 0 < pos < 200:
                    first_line = first_line[:pos + len(end_mark)]
                    break
            if len(first_line) > 200:
                first_line = first_line[:200] + "..."
            kept.append(first_line)
            total_omitted = sum(len(l) for l in paragraph_buffer) - len(first_line)
            if total_omitted > 50:
                kept.append(f"  (...{total_omitted} chars of explanation omitted)")
        paragraph_buffer.clear()

    def _flush_code_block():
        """将代码块压缩后输出。"""
        if not code_block_lines:
            return
        total_code = sum(len(l) for l in code_block_lines)
        if total_code <= 500 or len(code_block_lines) <= 15:
            for line in code_block_lines:
                kept.append(line)
        else:
            head_n = min(8, len(code_block_lines))
            tail_n = min(5, len(code_block_lines) - head_n)
            for line in code_block_lines[:head_n]:
                kept.append(line)
            omitted = len(code_block_lines) - head_n - tail_n
            if omitted > 0:
                kept.append(f"  // ... ({omitted} lines omitted)")
            if tail_n > 0:
                for line in code_block_lines[-tail_n:]:
                    kept.append(line)
        code_block_lines.clear()

    for line in lines:
        stripped = line.strip()

        # ── 代码块处理 ──
        if stripped.startswith("```"):
            if in_code_block:
                _flush_code_block()
                kept.append(line)
                in_code_block = False
            else:
                _flush_paragraph()
                in_code_block = True
                kept.append(line)
            continue

        if in_code_block:
            code_block_lines.append(line)
            continue

        # ── Agent ID 尾部标记 — 删除 ──
        if stripped.startswith("Agent ID:"):
            _flush_paragraph()
            continue

        # ── 空行 ──
        if not stripped:
            _flush_paragraph()
            kept.append("")
            continue

        # ── 分隔线 ──
        if stripped == "---":
            _flush_paragraph()
            kept.append(line)
            continue

        # ── 标题行 — 始终保留 ──
        if re.match(r'^#{1,4}\s+', stripped):
            _flush_paragraph()
            kept.append(line)
            list_count_in_section = 0
            continue

        # ── 列表项 — 保留（带限制）──
        if re.match(r'^[-*]\s+', stripped) or re.match(r'^\d+\.\s+', stripped):
            _flush_paragraph()
            list_count_in_section += 1
            if list_count_in_section <= 30:
                if len(line) > 250:
                    kept.append(line[:250] + "...")
                else:
                    kept.append(line)
            elif list_count_in_section == 31:
                kept.append("  (...more list items omitted)")
            continue

        # ── 粗体行 / 关键数据行 — 保留 ──
        if stripped.startswith("**") or re.match(r'^[A-Z][a-z]+:', stripped):
            _flush_paragraph()
            if len(line) > 250:
                kept.append(line[:250] + "...")
            else:
                kept.append(line)
            continue

        # ── 文件路径行 — 保留 ──
        if re.search(r'[\w/\\]+\.\w{1,5}', stripped) and ("/" in stripped or "\\" in stripped):
            _flush_paragraph()
            kept.append(line)
            continue

        # ── 表格行 — 保留 ──
        if stripped.startswith("|"):
            _flush_paragraph()
            kept.append(line)
            continue

        # ── 纯段落文字 — 缓冲，稍后压缩 ──
        paragraph_buffer.append(line)

    # 处理尾部
    if in_code_block:
        _flush_code_block()
    _flush_paragraph()

    result = "\n".join(kept)

    # 如果压缩效果不明显（<8% 压缩），直接返回原文
    if len(result) > len(text) * 0.92:
        return text

    return result


# ==================================================================================================
# 统一压缩入口：_compress_content
# ==================================================================================================

def _head_tail_compress(text: str, keep_ratio: float = 0.3) -> str:
    """头尾保留压缩。"""
    total_keep = int(len(text) * keep_ratio)
    if total_keep >= len(text):
        return text
    head_size = int(total_keep * 0.6)
    tail_size = total_keep - head_size
    head = text[:head_size]
    tail = text[-tail_size:] if tail_size > 0 else ""
    omitted = len(text) - head_size - tail_size
    return f"{head}\n\n... [{omitted} chars omitted] ...\n\n{tail}"


def _compress_content(text: str, recency: float, hint_path: str = "", tool_name: str = "") -> str:
    """
    按工具类型智能压缩单个 tool_result 的文本内容。

    tool_name: 产生此 tool_result 的工具名（Read/Grep/Shell/Glob 等）。
    recency: 0.0 (最早) ~ 1.0 (最新)，越早压缩越狠。
    hint_path: 从 tool_id 映射获得的文件路径（精确语言检测）。

    按工具类型分发策略：
      Read       → AST 骨架化（保留文件名+结构+签名+import）
      Grep       → 保留匹配行+文件路径，压缩上下文行
      Shell      → 保留命令+退出码+错误+最后输出，压缩中间输出
      Glob       → 不压缩（通常很小）
      Write/StrReplace/Delete → 不压缩（确认消息很短）
      其他       → 通用策略（AST → 正则 → head_tail）
    """
    keep_ratio = 0.15 + recency * 0.30
    tool_upper = tool_name.lower() if tool_name else ""

    # ── Glob / ListDir / Write / StrReplace / Delete / EditNotebook / TodoWrite ──
    # 这些工具的 result 通常很短，不压缩
    if tool_upper in ("glob", "listdir", "list_dir", "listfiles", "list_files",
                       "write", "write_to_file", "strreplace", "str_replace",
                       "delete", "editnotebook", "todowrite", "todo_write",
                       "askquestion", "switchmode", "generateimage",
                       "listmcpresources", "fetchmcpresource"):
        return text

    # ── Shell — 命令输出压缩 ──
    if tool_upper in ("shell", "run_command"):
        return _compress_shell_output(text, keep_ratio)

    # ── Grep / Search — 搜索结果压缩 ──
    if tool_upper in ("grep", "search", "semanticsearch", "semantic_search",
                       "codebase_search"):
        return _compress_grep_result(text, keep_ratio)

    # ── Task subagent 报告 — Markdown 结构化压缩 ──
    if tool_upper in ("task", "subagent"):
        if _is_markdown_report(text):
            return _compress_markdown_report(text, max(keep_ratio, 0.30))
        return _head_tail_compress(text, keep_ratio)

    # ── WebSearch / WebFetch — 网页内容压缩 ──
    if tool_upper in ("websearch", "web_search", "webfetch", "web_fetch"):
        return _head_tail_compress(text, keep_ratio)

    # ── Read — 文件内容压缩（核心，最大的 token 消耗者）──
    # 也是默认策略（tool_name 未知时走这条路）
    return _compress_read_result(text, recency, hint_path)


def _compress_html_content(text: str, keep_ratio: float = 0.3) -> str:
    """
    HTML 文件专用压缩 — 提取关键元信息 + 激进 head_tail。

    HTML 文件通常巨大（实测 102K chars），但对代码分析价值低。
    策略：提取 <title>、<meta>、<script src>、<link href> 等关键信息，
    然后对剩余内容做激进 head_tail（ratio=0.05）。
    """
    # 提取关键元信息
    meta_lines = []

    # <title>
    title_match = re.search(r'<title[^>]*>(.*?)</title>', text, re.IGNORECASE | re.DOTALL)
    if title_match:
        meta_lines.append(f"<title>{title_match.group(1).strip()}</title>")

    # <meta> tags（description, charset, viewport 等）
    for meta_match in re.finditer(r'<meta\s+[^>]*?(?:name|charset|http-equiv|property)=[^>]+>', text[:5000], re.IGNORECASE):
        meta_lines.append(meta_match.group(0))

    # <script src="..."> 外部脚本引用
    for script_match in re.finditer(r'<script\s+[^>]*?src=["\']([^"\']+)["\'][^>]*>', text, re.IGNORECASE):
        meta_lines.append(f'<script src="{script_match.group(1)}"></script>')

    # <link href="..."> 样式表引用
    for link_match in re.finditer(r'<link\s+[^>]*?href=["\']([^"\']+)["\'][^>]*>', text[:10000], re.IGNORECASE):
        meta_lines.append(link_match.group(0))

    # 组装结果
    total_chars = len(text)
    header = f"[HTML document: {total_chars} chars]"
    if meta_lines:
        header += "\n" + "\n".join(meta_lines[:15])  # 最多 15 条元信息

    # 激进 head_tail（只保留 5% 的原文）
    aggressive_ratio = min(keep_ratio, 0.05)
    body_compressed = _head_tail_compress(text, aggressive_ratio)

    return header + "\n\n" + body_compressed


def _compress_read_result(text: str, recency: float, hint_path: str = "") -> str:
    """
    Read 工具结果压缩：AST 骨架化。

    保留：文件路径、import/export、类/函数签名、类型定义、装饰器、docstring
    压缩：函数体实现细节
    """
    keep_ratio = 0.15 + recency * 0.30
    lang = _detect_language_from_text(text, hint_path=hint_path)

    # HTML 文件特殊处理 — 通常是巨大的 <!DOCTYPE html> 页面（实测 102K chars）
    # AST skeleton 对 HTML 只能压到 15K（head_tail fallback），效果差
    # 直接用激进 head_tail（0.05 ratio）+ 提取 <title> 和 <meta> 信息
    if lang == "html" or (not lang and ("<!DOCTYPE" in text[:200] or "<html" in text[:500])):
        return _compress_html_content(text, keep_ratio)

    # Markdown / 非代码文本 — 直接头尾保留，tree-sitter 对它没意义
    if lang in ("markdown", "json", "yaml", "toml", "css", "scss", "sql"):
        return _head_tail_compress(text, keep_ratio)

    # 尝试 tree-sitter
    if lang and _TS_AVAILABLE:
        result = _skeletonize_with_treesitter(text, lang)
        if result is not None and len(result) < len(text) * 0.95:
            return result

    # Fallback: 正则骨架化（仅对代码）
    if lang or _looks_like_code(text):
        result = _skeletonize_with_regex(text)
        if len(result) < len(text) * 0.7:
            return result

    # 最终 fallback：对任何大文本都做头尾保留
    if len(text) > LARGE_RESULT_THRESHOLD:
        return _head_tail_compress(text, keep_ratio)

    return text


def _compress_shell_output(text: str, keep_ratio: float = 0.3) -> str:
    """
    Shell 命令输出压缩。

    保留：
      - 前 5 行（通常包含命令本身或关键头部信息）
      - 最后 20 行（通常包含结果/错误/退出码）
      - 包含 error/warning/fail 的行
    压缩：
      - 中间的大量输出（如 npm install 进度、编译日志、测试输出）
    """
    lines = text.split("\n")
    if len(lines) <= 30:
        return text  # 短输出不压缩

    head_lines = 5
    tail_lines = 20

    # 收集包含错误/警告的行
    error_keywords = ("error", "Error", "ERROR", "fail", "Fail", "FAIL",
                      "warning", "Warning", "WARN", "fatal", "Fatal",
                      "exception", "Exception", "traceback", "Traceback",
                      "not found", "denied", "refused", "timeout")
    important_lines = []
    for i, line in enumerate(lines[head_lines:-tail_lines] if len(lines) > head_lines + tail_lines else []):
        if any(kw in line for kw in error_keywords):
            important_lines.append((i + head_lines, line))

    head = lines[:head_lines]
    tail = lines[-tail_lines:]
    middle_total = len(lines) - head_lines - tail_lines

    result_parts = head
    if important_lines:
        result_parts.append(f"\n... [{middle_total} lines of output, showing {len(important_lines)} important lines] ...")
        for idx, line in important_lines[:10]:  # 最多保留 10 条重要行
            result_parts.append(f"  L{idx}: {line}")
        result_parts.append("...")
    else:
        result_parts.append(f"\n... [{middle_total} lines of output omitted] ...")
    result_parts.extend(tail)

    return "\n".join(result_parts)


def _compress_grep_result(text: str, keep_ratio: float = 0.3) -> str:
    """
    Grep/Search 结果压缩。

    Grep 输出格式通常是：
      filepath:line_number:matched_content
    或 ripgrep 格式：
      filepath
      line_number-context_line
      line_number:matched_line
      line_number-context_line

    保留：文件路径 + 匹配行（带 : 的行）
    压缩：上下文行（带 - 的行），只保留匹配行前后各 1 行
    """
    lines = text.split("\n")
    if len(lines) <= 30:
        return text  # 短结果不压缩

    # 检测是否是 ripgrep 格式（有 -- 分隔符和 行号:内容 / 行号-内容 格式）
    has_rg_format = False
    match_count = 0
    for line in lines[:50]:
        if re.match(r'^\d+:', line) or re.match(r'^.+:\d+:', line):
            has_rg_format = True
            match_count += 1

    if not has_rg_format or match_count < 2:
        # 不是标准 grep 格式，用通用 head_tail
        return _head_tail_compress(text, keep_ratio)

    # ripgrep 格式：保留文件路径行 + 匹配行，压缩上下文行
    kept = []
    skipped = 0
    prev_was_match = False

    for line in lines:
        stripped = line.strip()
        # 空行或分隔符
        if not stripped or stripped == "--":
            if skipped > 0:
                kept.append(f"  ... [{skipped} context lines omitted]")
                skipped = 0
            kept.append(line)
            prev_was_match = False
            continue

        # 文件路径行（不以数字开头，不含 : 在前几个字符）
        is_file_path = (stripped.startswith("/") or
                        (len(stripped) > 2 and stripped[1] == ":") or
                        (not re.match(r'^\d+[:-]', stripped) and ":" not in stripped[:5]))

        # 匹配行（行号:内容）
        is_match = bool(re.match(r'^\d+:', stripped) or re.match(r'^.+:\d+:', stripped))

        # 上下文行（行号-内容）
        is_context = bool(re.match(r'^\d+-', stripped) or re.match(r'^.+:\d+-', stripped))

        if is_file_path or is_match:
            if skipped > 0:
                kept.append(f"  ... [{skipped} context lines omitted]")
                skipped = 0
            kept.append(line)
            prev_was_match = is_match
        elif is_context:
            # 只保留紧邻匹配行的上下文（前后各 1 行）
            if prev_was_match:
                kept.append(line)  # 匹配行后的第一行上下文
                prev_was_match = False
            else:
                skipped += 1
        else:
            # 其他行保留
            if skipped > 0:
                kept.append(f"  ... [{skipped} context lines omitted]")
                skipped = 0
            kept.append(line)
            prev_was_match = False

    if skipped > 0:
        kept.append(f"  ... [{skipped} context lines omitted]")

    result = "\n".join(kept)
    # 如果压缩效果不明显，fallback 到 head_tail
    if len(result) > len(text) * 0.85:
        return _head_tail_compress(text, keep_ratio)
    return result


# ==================================================================================================
# Level 1: 清理截断重试循环（零信息损失）
# ==================================================================================================

def _is_error_invalid_args(msg: Dict[str, Any]) -> bool:
    if msg.get("role") != "user":
        return False
    content = msg.get("content", "")
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            bc = block.get("content", "")
            text = ""
            if isinstance(bc, list):
                text = " ".join(
                    sub.get("text", "") for sub in bc if isinstance(sub, dict)
                )
            elif isinstance(bc, str):
                text = bc
            if "Error: Invalid arguments" in text:
                return True
    elif isinstance(content, str) and "Error: Invalid arguments" in content:
        return True
    return False


def _clean_retry_loops(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    清理截断重试产生的无效循环。
    模式：assistant(tool_call) → user("Error: Invalid arguments") 重复多次。
    保留最后一轮，删除之前的重复。
    """
    if len(messages) < 4:
        return messages, 0

    error_indices = set()
    for i, m in enumerate(messages):
        if _is_error_invalid_args(m):
            error_indices.add(i)

    if len(error_indices) < 2:
        return messages, 0

    consecutive_pairs = []
    current_run = []

    for i in sorted(error_indices):
        if i > 0 and messages[i - 1].get("role") == "assistant":
            current_run.append((i - 1, i))
        else:
            if len(current_run) >= 2:
                consecutive_pairs.append(current_run)
            current_run = []

    if len(current_run) >= 2:
        consecutive_pairs.append(current_run)

    remove_set = set()
    total_removed_pairs = 0
    for run in consecutive_pairs:
        for pair in run[:-1]:
            remove_set.add(pair[0])
            remove_set.add(pair[1])
            total_removed_pairs += 1

    if not remove_set:
        return messages, 0

    cleaned = [m for i, m in enumerate(messages) if i not in remove_set]
    logger.info(
        f"[Compression L1-retry] Removed {len(remove_set)} retry loop messages ({total_removed_pairs} error cycles)",
    )
    return cleaned, len(remove_set)


# ==================================================================================================
# Level 1: 冗余去重
# ==================================================================================================

def _extract_file_path_key(text: str) -> Optional[str]:
    """从 tool_result 文本中提取文件路径作为去重 key。"""
    lines = text.strip().split("\n", 5)
    for line in lines[:3]:
        line = line.strip()
        if line.startswith("/") and not line.startswith("//"):
            return "file:" + line.split("\n")[0].strip()
        if len(line) > 2 and line[1] == ":" and line[2] in ("/", "\\"):
            return "file:" + line.split("\n")[0].strip()
    return None


def _deduplicate_tool_results(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """同一文件被多次 read 时，只保留最后一次的完整内容。"""
    if len(messages) < 4:
        return messages, 0

    content_map: Dict[str, List[Tuple[int, int]]] = {}

    for i, m in enumerate(messages):
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if not isinstance(content, list):
            continue
        for j, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            text = _get_result_text(block)
            if len(text) < 500:
                continue

            file_key = _extract_file_path_key(text)
            if not file_key:
                file_key = "hash:" + hashlib.md5(text[:1000].encode()).hexdigest()

            if file_key not in content_map:
                content_map[file_key] = []
            content_map[file_key].append((i, j))

    dedup_targets = {}
    total_deduped = 0

    for key, locations in content_map.items():
        if len(locations) < 2:
            continue
        for loc in locations[:-1]:
            dedup_targets[loc] = f"(Refer to later tool_result for same content: {key})"
            total_deduped += 1

    if not dedup_targets:
        return messages, 0

    result = []
    for i, m in enumerate(messages):
        needs_modify = False
        if m.get("role") == "user" and isinstance(m.get("content"), list):
            for j, block in enumerate(m["content"]):
                if (i, j) in dedup_targets:
                    needs_modify = True
                    break

        if needs_modify:
            new_content = []
            for j, block in enumerate(m["content"]):
                if (i, j) in dedup_targets:
                    new_block = dict(block)
                    _set_result_text_inplace(new_block, dedup_targets[(i, j)])
                    new_content.append(new_block)
                else:
                    new_content.append(block)
            new_m = dict(m)
            new_m["content"] = new_content
            result.append(new_m)
        else:
            result.append(m)

    logger.info(f"[Compression L1-dedup] Deduplicated {total_deduped} repeated tool_results")
    return result, total_deduped


# ==================================================================================================
# Level 1.5: 压缩非最近消息中的 image blocks
# ==================================================================================================

def _compress_image_blocks(
    messages: List[Dict[str, Any]],
    priorities: List[int],
) -> Tuple[List[Dict[str, Any]], int]:
    """
    将非最近消息中的 base64 image block 替换为文本占位符。

    图片 base64 数据通常占 100K+ chars，但对历史上下文理解价值很低。
    保留最近消息的图片（用户可能正在讨论它）。
    """
    saved_chars = 0
    result = list(messages)

    for i, m in enumerate(messages):
        if priorities[i] >= PRIORITY_RECENT:
            continue
        content = m.get("content", "")
        if not isinstance(content, list):
            continue

        has_image = False
        for block in content:
            if isinstance(block, dict) and block.get("type") == "image":
                has_image = True
                break

        if not has_image:
            continue

        new_content = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "image":
                src = block.get("source", {})
                data = src.get("data", "")
                media_type = src.get("media_type", "image")
                size_kb = len(data) * 3 // 4 // 1024  # base64 -> bytes -> KB
                saved_chars += len(data)
                new_content.append({
                    "type": "text",
                    "text": f"[image: {media_type}, ~{size_kb}KB — removed from early context to save tokens]",
                })
            else:
                new_content.append(block)

        new_m = dict(m)
        new_m["content"] = new_content
        result[i] = new_m

    if saved_chars > 0:
        saved_tokens = _estimate_tokens(" " * saved_chars)
        logger.info(f"[Compression L1.5] Replaced image blocks, saved ~{saved_tokens} tokens ({saved_chars // 1000}K chars)")

    return result, saved_chars


# ==================================================================================================
# 优先级评分
# ==================================================================================================

def _contains_error_diagnostic(msg: Dict[str, Any]) -> bool:
    """
    检查消息是否包含报错/诊断信息。

    只检查纯文本 user 消息和 tool_result 中明确的错误输出。
    不对整个 tool_result 做 json.dumps 搜索——代码文件里到处有 "Error" 字样会误判。
    """
    content = msg.get("content", "")

    # 纯文本消息：直接搜索
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        # 只检查 type=text 的 block（用户输入），跳过 tool_result（代码内容）
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    # 只检查短的 tool_result（错误消息通常很短）
                    result_text = _get_result_text(block)
                    if len(result_text) < 500:
                        text_parts.append(result_text)
            elif isinstance(block, str):
                text_parts.append(block)
        text = "\n".join(text_parts)
    else:
        return False

    if not text:
        return False

    error_patterns = [
        "Error:", "error:", "ERROR",
        "TypeError", "SyntaxError", "ReferenceError",
        "Cannot find", "is not defined",
        "diagnostic", "Diagnostic",
        "FAILED", "failed",
        "traceback", "Traceback",
        "Exception", "exception",
    ]
    for pat in error_patterns:
        if pat in text:
            return True
    return False


def _score_message_priority(
    msg: Dict[str, Any],
    idx: int,
    total: int,
    is_last_user: bool,
) -> int:
    """给消息打优先级分。分数越高越不应该被压缩。"""
    role = msg.get("role", "")

    if role == "system":
        return PRIORITY_SYSTEM

    if is_last_user:
        return PRIORITY_LAST_USER

    if idx >= total - RECENT_MESSAGES_PROTECTED:
        return PRIORITY_RECENT

    if role == "user" and _contains_error_diagnostic(msg):
        return PRIORITY_ERROR_DIAG

    if role == "assistant":
        content = msg.get("content", "")
        content_len = len(content) if isinstance(content, str) else (
            len(json.dumps(content, ensure_ascii=False)) if content else 0
        )
        if content_len > 3000 and idx < total * 0.7:
            return PRIORITY_EARLY_ASSISTANT
        return PRIORITY_NORMAL

    if role == "user" and isinstance(msg.get("content"), list):
        has_large_result = False
        for block in msg["content"]:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                text = _get_result_text(block)
                if len(text) > LARGE_RESULT_THRESHOLD:
                    has_large_result = True
                    break
        if has_large_result and idx < total * 0.7:
            return PRIORITY_EARLY_RESULT

    return PRIORITY_NORMAL


def _compute_priorities(messages: List[Dict[str, Any]]) -> List[int]:
    """计算所有消息的优先级。"""
    total = len(messages)
    last_user_idx = -1
    for i in range(total - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user_idx = i
            break
    return [
        _score_message_priority(m, i, total, i == last_user_idx)
        for i, m in enumerate(messages)
    ]


# ==================================================================================================
# Zone 分区分类
# ==================================================================================================

def _classify_zones(total: int) -> Tuple[int, int, int, int]:
    """
    根据消息总数计算各 Zone 的起始索引（五区策略）。

    返回 (zone_e_end, zone_d_start, zone_c_start, zone_b_start, zone_a_start)
    但为了简洁，返回四个边界值：
      (zone_d_start, zone_c_start, zone_b_start, zone_a_start)

    Zone E: [0, zone_d_start)           — 直接删掉
    Zone D: [zone_d_start, zone_c_start) — 简要概要
    Zone C: [zone_c_start, zone_b_start) — AST 骨架化 + 工具摘要
    Zone B: [zone_b_start, zone_a_start) — 基本保留
    Zone A: [zone_a_start, total)        — 绝对保护

    例如 200 条消息：
      Zone E: [0, 80)   Zone D: [80, 140)   Zone C: [140, 170)   Zone B: [170, 190)   Zone A: [190, 200)
    """
    zone_a_start = max(0, total - ZONE_A_SIZE)
    zone_b_start = max(0, total - ZONE_B_SIZE)
    zone_c_start = max(0, total - ZONE_C_SIZE)
    zone_d_start = max(0, total - ZONE_D_SIZE)

    # 确保各区边界不交叉
    zone_d_start = min(zone_d_start, zone_c_start)
    zone_c_start = min(zone_c_start, zone_b_start)
    zone_b_start = min(zone_b_start, zone_a_start)

    return zone_d_start, zone_c_start, zone_b_start, zone_a_start


def _get_zone(idx: int, total: int, zone_d_start: int, zone_c_start: int, zone_b_start: int, zone_a_start: int) -> str:
    """返回消息所在的 Zone 标识：'A', 'B', 'C', 'D', 'E'。"""
    if idx >= zone_a_start:
        return "A"
    if idx >= zone_b_start:
        return "B"
    if idx >= zone_c_start:
        return "C"
    if idx >= zone_d_start:
        return "D"
    return "E"


# ==================================================================================================
# Level 2: 压缩大 tool_result（AST 骨架化 / 头尾保留）
# ==================================================================================================

def _compress_tool_results(
    messages: List[Dict[str, Any]],
    target_tokens: int,
    current_tokens: int,
    priorities: List[int],
    tool_id_map: Optional[Dict[str, str]] = None,
    tool_name_map: Optional[Dict[str, str]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """按优先级压缩 tool_result 内容。优先压缩低优先级的大 tool_result。
    
    v2 变更：分析模式下不再跳过 Read tool_result，而是用 AST skeleton 压缩。
    只有最近 RECENT_MESSAGES_PROTECTED 条消息中的 Read 被保护。
    """
    tokens_to_save = current_tokens - target_tokens
    if tokens_to_save <= 0:
        return messages, 0

    total_msgs = len(messages)
    _id_map = tool_id_map or {}
    _name_map = tool_name_map or {}

    candidates = []
    for i, m in enumerate(messages):
        if priorities[i] >= PRIORITY_RECENT:
            continue
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if not isinstance(content, list):
            continue
        for j, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            text = _get_result_text(block)
            if len(text) < LARGE_RESULT_THRESHOLD:
                continue
            inv_priority = 100 - priorities[i]
            tool_use_id = _get_tool_result_id(block)
            hint_path = _id_map.get(tool_use_id, "")
            tool_name = _name_map.get(tool_use_id, "")
            candidates.append({
                "msg_idx": i,
                "block_idx": j,
                "text": text,
                "chars": len(text),
                "priority": inv_priority * len(text),
                "hint_path": hint_path,
                "tool_name": tool_name,
            })

    if not candidates:
        return messages, 0

    candidates.sort(key=lambda c: -c["priority"])

    saved_total = 0
    compressions: Dict[int, Dict[int, str]] = {}

    for cand in candidates:
        if saved_total >= tokens_to_save:
            break

        text = cand["text"]
        recency = cand["msg_idx"] / total_msgs if total_msgs > 0 else 0.5

        compressed = _compress_content(
            text, recency,
            hint_path=cand.get("hint_path", ""),
            tool_name=cand.get("tool_name", ""),
        )
        saved_chars = len(text) - len(compressed)
        if saved_chars <= 0:
            continue

        mi = cand["msg_idx"]
        if mi not in compressions:
            compressions[mi] = {}
        compressions[mi][cand["block_idx"]] = compressed
        saved_total += _estimate_tokens(text) - _estimate_tokens(compressed)

    if not compressions:
        return messages, 0

    result = []
    for i, m in enumerate(messages):
        if i in compressions:
            result.append(_apply_block_compressions(m, compressions[i]))
        else:
            result.append(m)

    count = sum(len(v) for v in compressions.values())
    logger.info(
        f"[Compression L2] Compressed {count} tool_results, saved ~{saved_total} tokens "
        f"(tree-sitter={'available' if _TS_AVAILABLE else 'unavailable'})",
    )
    return result, saved_total


# ==================================================================================================
# Level 3: 压缩早期 assistant 长回复
# ==================================================================================================

def _is_agent_narration(text: str) -> bool:
    """
    判断 assistant 文本是否是过渡性叙述（而非有价值的分析内容）。

    Agent 在工具调用之间经常插入过渡性文字：
      "Let me read all the files now."
      "I'll start by exploring the packages."
      "Now let me check the database schema."
    这些文字没有分析价值，不应阻止 L4 pair dropping。
    """
    lower = text.lower().strip()
    narration_prefixes = (
        "let me ", "i'll ", "i will ", "now ", "next ",
        "let's ", "ok, ", "okay, ", "alright, ",
        "first, ", "then, ", "now let me ", "now i'll ",
        "i need to ", "i should ", "i want to ",
        "让我", "我来", "接下来", "现在", "首先", "然后",
    )
    for prefix in narration_prefixes:
        if lower.startswith(prefix):
            return True
    # 短文本（< 300 chars）且不含分析关键词 → 叙述
    if len(text) < 300:
        analysis_keywords = (
            "because", "therefore", "however", "the issue",
            "the problem", "this means", "this suggests",
            "in summary", "the key", "importantly",
            "因为", "所以", "但是", "问题是", "这说明", "总结",
        )
        if not any(kw in lower for kw in analysis_keywords):
            return True
    return False


def _is_decision_line(line: str) -> bool:
    """判断是否是决策相关的行。"""
    decision_keywords = [
        "created", "modified", "deleted", "updated", "renamed",
        "创建", "修改", "删除", "更新", "重命名",
        ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml",
        ".css", ".html", ".md", ".sql", ".sh",
        "installed", "deployed", "configured", "fixed", "added", "removed",
        "安装", "部署", "配置", "修复", "添加", "移除",
        "##", "###", "- ", "* ", "1.", "2.", "3.",
    ]
    for kw in decision_keywords:
        if kw in line:
            return True
    return False


def _extract_decision_summary(content: str) -> str:
    """从 assistant 长回复中提取决策摘要。"""
    lines = content.split("\n")
    kept = []
    in_code_block = False
    code_block_skipped = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_block_skipped = False
            else:
                in_code_block = False
                if code_block_skipped:
                    kept.append("// ... [code block omitted] ...")
                    kept.append(line)
                code_block_skipped = False
            continue

        if in_code_block:
            if not code_block_skipped:
                kept.append(line)
                code_lines = sum(1 for ln in kept[-10:] if not ln.strip().startswith("```"))
                if code_lines >= 3:
                    code_block_skipped = True
            continue

        if _is_decision_line(stripped):
            kept.append(line)
        elif len(stripped) < 100:
            kept.append(line)

    result = "\n".join(kept)

    if len(result) < len(content) * 0.15:
        return content[:int(len(content) * 0.3)] + "\n\n... [early response truncated] ..."

    return result


def _compress_early_conversations(
    messages: List[Dict[str, Any]],
    target_tokens: int,
    current_tokens: int,
    priorities: List[int],
    max_idx: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """压缩 assistant 长回复（str content + list content with tool_use blocks）。
    
    max_idx: 只处理 [0, max_idx) 范围内的消息。None 表示处理所有非 RECENT 消息。
    """
    tokens_to_save = current_tokens - target_tokens
    if tokens_to_save <= 0:
        return messages, 0

    saved_total = 0
    result = list(messages)
    limit = max_idx if max_idx is not None else len(messages)

    for i, m in enumerate(messages):
        if saved_total >= tokens_to_save:
            break
        if i >= limit:
            break
        if m.get("role") != "assistant":
            continue

        content = m.get("content", "")
        str_min_chars = 500
        tool_use_min_chars = 1000
        field_min_chars = 500

        # ── Case 1: str content — 决策摘要 ──
        if isinstance(content, str):
            if len(content) < str_min_chars:
                continue
            summary = _extract_decision_summary(content)
            saved_chars = len(content) - len(summary)
            if saved_chars <= 0:
                continue
            new_m = dict(m)
            new_m["content"] = summary
            result[i] = new_m
            saved_total += _estimate_tokens(content) - _estimate_tokens(summary)
            continue

        # ── Case 2: list content — Anthropic format with tool_use blocks ──
        # Cursor sends assistant messages with content: [{"type": "tool_use", "input": {"old_string": "...", "new_string": "..."}}]
        # These tool_use blocks can contain huge code diffs (10K+ chars each)
        if isinstance(content, list):
            new_content = []
            msg_saved = 0
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    new_content.append(block)
                    continue

                block_input = block.get("input", {})
                if not isinstance(block_input, dict):
                    new_content.append(block)
                    continue

                block_json = json.dumps(block_input, ensure_ascii=False)
                if len(block_json) < tool_use_min_chars:
                    new_content.append(block)
                    continue

                # Compress large string fields in tool_use input
                new_input = dict(block_input)
                for field in ("old_string", "new_string", "old_str", "new_str",
                              "content", "file_text", "code", "text", "diff"):
                    val = new_input.get(field)
                    if isinstance(val, str) and len(val) > field_min_chars:
                        lines = val.split("\n")
                        total_lines = len(lines)
                        if total_lines > 10:
                            # Keep first 3 + last 3 lines
                            compressed_val = "\n".join(lines[:3]) + f"\n... [{total_lines - 6} lines omitted] ...\n" + "\n".join(lines[-3:])
                        else:
                            compressed_val = val[:200] + f"\n... [{len(val) - 400} chars omitted] ...\n" + val[-200:]
                        msg_saved += len(val) - len(compressed_val)
                        new_input[field] = compressed_val

                if msg_saved > 0:
                    new_block = dict(block)
                    new_block["input"] = new_input
                    new_content.append(new_block)
                else:
                    new_content.append(block)

            if msg_saved > 0:
                new_m = dict(m)
                new_m["content"] = new_content
                result[i] = new_m
                saved_total += _estimate_tokens(" " * msg_saved)

    if saved_total > 0:
        logger.info(f"[Compression L3] Compressed early conversations, saved ~{saved_total} tokens")

    return result, saved_total


def _skeletonize_for_map(text: str, tool_name: str = "", hint_path: str = "") -> str:
    """
    将 tool_result 转化为高精度"地图"——保留全部结构信息，删除实现细节。

    这是 Repo Map 的核心：模型拿到的每一个 token 都有价值。
    对于 Read 结果，产出 AST 骨架（import + 签名 + 类型 + docstring）。
    对于其他工具，保留关键信息摘要。

    策略（按工具类型）：
      Read  → AST 骨架化（tree-sitter → regex fallback → head_tail）
      Glob  → 完整保留（文件路径列表，通常很小）
      Shell → 前 2 行 + 最后 5 行 + 错误行
      Grep  → 保留文件路径 + 匹配行（去掉上下文行）
      Write/StrReplace → 完整保留（确认消息很短）
      其他  → head_tail
    """
    if not text or not text.strip():
        return "(empty)"

    text = text.strip()
    total_chars = len(text)
    lines = text.split("\n")
    total_lines = len(lines)
    lower_name = tool_name.lower()

    # ── Glob / ListDir — 完整保留 ──
    if lower_name in ("glob", "listdir", "list_dir", "listfiles", "list_files"):
        if total_chars <= 3000:
            return text
        kept = "\n".join(lines[:50])
        return f"{kept}\n... ({total_lines} paths total)"

    # ── Write / StrReplace / Delete — 完整保留（确认消息很短）──
    if lower_name in ("write", "write_to_file", "strreplace", "str_replace",
                       "delete", "editnotebook", "todowrite", "todo_write"):
        if total_chars <= 2000:
            return text
        return _head_tail_compress(text, 0.5)

    # ── Shell — 命令输出：头 + 尾 + 错误行 ──
    if lower_name in ("shell", "run_command"):
        if total_chars <= 800:
            return text
        return _compress_shell_output(text, 0.3)

    # ── Grep / Search — 保留匹配行 ──
    if lower_name in ("grep", "search", "semanticsearch", "semantic_search",
                       "codebase_search"):
        if total_chars <= 2000:
            return text
        return _compress_grep_result(text, 0.3)

    # ── Task subagent 报告 — Markdown 结构化压缩 ──
    if lower_name in ("task", "subagent"):
        if total_chars <= 1500:
            return text
        if _is_markdown_report(text):
            return _compress_markdown_report(text, 0.35)
        # 非 Markdown 格式的 Task 结果 → head_tail
        return _head_tail_compress(text, 0.3)

    # ── Read（最常见，最大的 token 消耗者）→ AST 骨架化 ──
    # 这是核心：把全量代码变成符号骨架（import + 签名 + 类型）
    lang = _detect_language_from_text(text, hint_path=hint_path)

    # HTML → 提取 meta + 激进 head_tail
    if lang == "html" or (not lang and ("<!DOCTYPE" in text[:200] or "<html" in text[:500])):
        return _compress_html_content(text, 0.05)

    # Markdown / JSON / YAML / CSS — 结构化压缩或 head_tail
    if lang in ("markdown", "json", "yaml", "toml", "css", "scss", "sql"):
        if lang == "markdown" and _is_markdown_report(text):
            return _compress_markdown_report(text, 0.3)
        return _head_tail_compress(text, 0.2)

    # 尝试 tree-sitter 骨架化
    if lang and _TS_AVAILABLE:
        skeleton = _skeletonize_with_treesitter(text, lang)
        if skeleton is not None and len(skeleton) < len(text) * 0.95:
            return skeleton

    # Fallback: 正则骨架化
    if lang or _looks_like_code(text):
        skeleton = _skeletonize_with_regex(text)
        if len(skeleton) < len(text) * 0.8:
            return skeleton

    # 最终 fallback: Markdown 报告检测 → head_tail
    if total_chars > 1000:
        if _is_markdown_report(text):
            return _compress_markdown_report(text, 0.3)
        return _head_tail_compress(text, 0.2)

    return text


def _drop_digested_pairs(
    messages: List[Dict[str, Any]],
    target_tokens: int,
    current_tokens: int,
    tools: Optional[List] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    将已消化的 assistant(tool_use) + user(tool_result) 对折叠为 **骨架化地图**。

    核心理念（Map vs Territory）：
      不能把"疆域"（全量代码）给模型，必须给它一张高精度的"地图"。
      地图 = import + class/function 签名 + 类型定义 + docstring
      疆域 = 函数体实现细节

    "已消化" = assistant 发了 tool_call，user 返回了 tool_result，然后 assistant 又继续了。
    这说明 Agent 已经处理了这些信息。

    策略：将 pair 折叠为两条消息：
      assistant: "[Previously called: Read(chat.ts), Read(init.ts), ...]"
      user: 每个 tool_result 替换为骨架化版本（保留完整结构信息）

    这样模型保留了：
      1. 历史感知（知道自己读了哪些文件）
      2. 文件结构地图（import、签名、类型 — 足够推理架构）
      3. 不含实现细节（节省 token）
    """
    import os as _os_fold

    if len(messages) < 4:
        return messages, 0

    tokens_to_save = current_tokens - target_tokens
    if tokens_to_save <= 0:
        return messages, 0

    # 构建 tool_use_id → tool_name / file_path 映射
    _tool_name_map = _build_tool_id_to_name(messages)
    _tool_path_map = _build_tool_id_to_path(messages)

    priorities = _compute_priorities(messages)
    # (assistant_idx, user_idx, assistant_summary, new_user_content)
    fold_pairs: List[Tuple[int, int, str, list]] = []
    saved = 0

    i = 0
    while i < len(messages) - 2 and saved < tokens_to_save:
        if priorities[i] >= PRIORITY_RECENT or messages[i].get("role") == "system":
            i += 1
            continue

        m_curr = messages[i]
        m_next = messages[i + 1] if i + 1 < len(messages) else None
        m_after = messages[i + 2] if i + 2 < len(messages) else None

        is_tool_pair = False
        if (m_curr.get("role") == "assistant" and m_next and m_next.get("role") == "user"
                and m_after and m_after.get("role") == "assistant"):
            curr_content = m_curr.get("content", "")
            has_tool_use = False
            has_analytical_text = False
            # (tool_name, path, tool_use_id)
            tool_info_list = []

            if isinstance(curr_content, list):
                for b in curr_content:
                    if isinstance(b, dict):
                        if b.get("type") == "tool_use":
                            has_tool_use = True
                            name = b.get("name", "?")
                            bid = b.get("id", "")
                            inp = b.get("input", {})
                            path = ""
                            if isinstance(inp, dict):
                                path = (inp.get("path") or inp.get("relative_workspace_path")
                                        or inp.get("pattern") or inp.get("command") or "")
                            tool_info_list.append((name, path, bid))
                        elif b.get("type") == "text":
                            text = b.get("text", "").strip()
                            if len(text) > 200 and not _is_agent_narration(text):
                                has_analytical_text = True

            tc = m_curr.get("tool_calls")
            if tc and isinstance(tc, list):
                for call in tc:
                    if isinstance(call, dict):
                        has_tool_use = True
                        func = call.get("function", {})
                        name = func.get("name", "?")
                        cid = call.get("id", "")
                        try:
                            args = json.loads(func.get("arguments", "{}"))
                        except (json.JSONDecodeError, TypeError):
                            args = {}
                        path = (args.get("path") or args.get("relative_workspace_path")
                                or args.get("pattern") or args.get("command") or "")
                        tool_info_list.append((name, path, cid))

            next_content = m_next.get("content", "")
            has_tool_result = False
            tool_result_blocks = []
            if isinstance(next_content, list):
                for b in next_content:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        has_tool_result = True
                        tool_result_blocks.append(b)

            if has_tool_use and has_tool_result and not has_analytical_text:
                is_tool_pair = True

        if is_tool_pair:
            # ── 构建 assistant 摘要（工具调用列表）──
            assistant_parts = []
            for name, path, _ in tool_info_list:
                if path:
                    short_path = _os_fold.path.basename(path) if "/" in path or "\\" in path else path
                    assistant_parts.append(f"{name}({short_path})")
                else:
                    assistant_parts.append(name)
            assistant_summary = "[Previously called: " + ", ".join(assistant_parts) + "]"

            # ── 构建 user 内容：每个 tool_result 骨架化 ──
            # 建立 tool_use_id → (name, path) 的快速查找
            id_to_info = {}
            for name, path, tid in tool_info_list:
                if tid:
                    id_to_info[tid] = (name, path)

            new_user_blocks = []
            for block in tool_result_blocks:
                text = _get_result_text(block)
                tuid = block.get("tool_use_id", "") or block.get("tool_call_id", "")
                t_name, t_path = id_to_info.get(tuid, ("", ""))
                if not t_name and tuid:
                    t_name = _tool_name_map.get(tuid, "")
                if not t_path and tuid:
                    t_path = _tool_path_map.get(tuid, "")

                # 骨架化：把全量代码变成符号地图
                skeleton = _skeletonize_for_map(text, tool_name=t_name, hint_path=t_path)

                # 保留 tool_result 格式（保持 Cursor 协议兼容）
                new_block = dict(block)
                # 替换 content 为骨架
                if isinstance(new_block.get("content"), list):
                    new_block["content"] = [{"type": "text", "text": skeleton}]
                elif isinstance(new_block.get("content"), str):
                    new_block["content"] = skeleton
                else:
                    new_block["content"] = [{"type": "text", "text": skeleton}]
                new_user_blocks.append(new_block)

            # 计算原始 pair 的 token 数
            pair_tokens = 0
            for idx in (i, i + 1):
                msg_content = messages[idx].get("content", "")
                if isinstance(msg_content, str):
                    pair_tokens += _estimate_tokens(msg_content)
                elif isinstance(msg_content, list):
                    pair_tokens += _estimate_tokens(json.dumps(msg_content, ensure_ascii=False))
                tc_data = messages[idx].get("tool_calls")
                if tc_data:
                    pair_tokens += _estimate_tokens(json.dumps(tc_data, ensure_ascii=False))

            # 新内容的 token 数
            new_tokens = _estimate_tokens(assistant_summary)
            new_tokens += _estimate_tokens(json.dumps(new_user_blocks, ensure_ascii=False))
            net_saved = pair_tokens - new_tokens

            if net_saved > 0:
                # 构建精简版 tool_use 块（只保留 id + name，input 清空）
                # 这样 converter 不会把 user 的 tool_results 当成 orphan
                slim_tool_uses = []
                for name, path, tid in tool_info_list:
                    slim_tool_uses.append({
                        "type": "tool_use",
                        "id": tid,
                        "name": name,
                        "input": {},
                    })
                fold_pairs.append((i, i + 1, assistant_summary, new_user_blocks, slim_tool_uses))
                saved += net_saved

            i += 2
        else:
            i += 1

    if not fold_pairs:
        return messages, 0

    # 应用折叠：替换 pair 为 assistant 摘要 + 骨架化 user 内容
    fold_set = set()
    fold_data = {}  # assistant_idx -> (assistant_summary, new_user_blocks, slim_tool_uses)
    for ai, ui, a_sum, u_blocks, tool_uses in fold_pairs:
        fold_set.add(ai)
        fold_set.add(ui)
        fold_data[ai] = (a_sum, u_blocks, tool_uses)

    result = []
    skip_next = False
    for idx, m in enumerate(messages):
        if skip_next:
            skip_next = False
            continue
        if idx in fold_data:
            a_sum, u_blocks, tool_uses = fold_data[idx]
            # assistant: 文本摘要 + 精简 tool_use 块（保持 tool_use_id 对应关系）
            assistant_content = [{"type": "text", "text": a_sum}] + tool_uses
            result.append({
                "role": "assistant",
                "content": assistant_content,
            })
            # user: 保留 tool_result 格式，内容替换为骨架
            result.append({
                "role": "user",
                "content": u_blocks,
            })
            skip_next = True
        else:
            result.append(m)

    logger.info(
        f"[Compression L4-early] Folded {len(fold_pairs)} digested pairs into summaries, "
        f"saved ~{saved} tokens"
    )
    return result, saved


def _dump_compressed(current: List[Dict[str, Any]], stats: Dict[str, Any], dump_id: Optional[str]) -> None:
    """Dump 压缩后的消息到文件。"""
    if not dump_id:
        return
    try:
        import os as _os
        _dump_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "compression_logs")
        _after_path = _os.path.join(_dump_dir, f"req_{dump_id}_after.json")
        with open(_after_path, "w", encoding="utf-8") as _f:
            json.dump({
                "token_estimate": stats.get("final_tokens", 0),
                "message_count": len(current),
                "level": stats.get("level", 0),
                "tokens_saved": stats.get("tokens_saved", 0),
                "messages": current,
            }, _f, ensure_ascii=False, indent=1)
        logger.info(f"[Compression] Dumped compressed messages to {_after_path}")
    except Exception as _e:
        logger.warning(f"[Compression] Failed to dump compressed messages: {_e}")


# ==================================================================================================
# 调试工具：消息结构快照
# ==================================================================================================

def _message_snapshot(messages: List[Dict[str, Any]]) -> str:
    """生成消息列表的结构快照，用于调试日志。每条消息一行，显示 role + 内容大小。"""
    lines = []
    for i, m in enumerate(messages):
        role = m.get("role", "?")
        content = m.get("content", "")
        tc = m.get("tool_calls")

        if isinstance(content, str):
            content_size = len(content)
            content_desc = f"str({content_size})"
        elif isinstance(content, list):
            block_descs = []
            for b in content:
                if isinstance(b, dict):
                    btype = b.get("type", "?")
                    if btype == "tool_result":
                        text = _get_result_text(b)
                        block_descs.append(f"tool_result({len(text)})")
                    elif btype == "tool_use":
                        inp = b.get("input", {})
                        inp_size = len(json.dumps(inp, ensure_ascii=False)) if isinstance(inp, dict) else 0
                        block_descs.append(f"tool_use({inp_size})")
                    elif btype == "text":
                        block_descs.append(f"text({len(b.get('text', ''))})")
                    elif btype == "image":
                        block_descs.append("image")
                    else:
                        block_descs.append(f"{btype}(?)")
                else:
                    block_descs.append(f"raw({len(str(b))})")
            content_desc = f"[{', '.join(block_descs)}]"
        else:
            content_desc = f"empty"

        tc_desc = ""
        if tc and isinstance(tc, list):
            tc_sizes = []
            for call in tc:
                if isinstance(call, dict):
                    args = call.get("function", {}).get("arguments", "")
                    tc_sizes.append(len(args) if isinstance(args, str) else 0)
            tc_desc = f" +tool_calls({len(tc)})[{','.join(str(s) for s in tc_sizes)}]"

        lines.append(f"  [{i:2d}] {role:10s} {content_desc}{tc_desc}")
    return "\n".join(lines)


# ==================================================================================================
# Level 0.5: 重复文件读取去重
# ==================================================================================================
#
# Cursor Agent 分析模式特征：
#   同一批文件被反复读取 10+ 次（每次可能不同行范围）
#   403K tokens 中大部分是重复的文件内容
#
# 核心洞察：如果同一文件被读了多次，只保留最后一次的完整内容。
# 早期的读取替换为指针 "[File re-read later: path]"。
# 这是纯去重，不做任何内容压缩，零信息损失（最后一次读取保留完整原文）。

def _is_read_tool_name(name: str) -> bool:
    """判断是否是读取类工具。"""
    return name in (
        "Read", "read_file", "ReadFile", "read",
        "Grep", "grep", "Search", "search",
        "Glob", "glob", "ListDir", "list_dir",
        "ListFiles", "list_files",
    )


def _cleanup_digested_reads(
    messages: List[Dict[str, Any]],
    priorities: List[int],
    tool_id_map: Optional[Dict[str, str]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    清理已被 Agent "消化" 的 Read tool_result — 去重策略。

    核心洞察：分析任务中，同一文件会被反复读取 10+ 次。
    压缩早期读取（不管是骨架化还是 head_tail）会导致模型信息不足 → 重读 → 死循环。

    新策略：只做去重，不做内容压缩。
      - 如果同一文件在后续轮次被重新读取了，早期的读取替换为指针：
        "[File was re-read later in the conversation]"
      - 如果一个文件只被读取了一次（没有后续重读），保留原文不动。
      - 这样既省了 token（同一文件 10 次读取只保留最后一次），又不丢信息。

    模式检测：
      [i]   user:      content=[tool_result, tool_result, ...]  ← 文件内容
      [i+1] assistant: content=[tool_use, ...]  或 tool_calls=[...]  ← agent 做了下一步
      → 说明 msg[i] 的 tool_result 已被消化
    """
    if len(messages) < 4:
        return messages, 0

    total = len(messages)
    saved_chars = 0
    result = list(messages)
    _id_map = tool_id_map or {}

    # 构建 tool_id → tool_name 映射
    tool_id_to_name: Dict[str, str] = {}
    for m in messages:
        if m.get("role") != "assistant":
            continue
        content = m.get("content", "")
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    tid = b.get("id", "")
                    tname = b.get("name", "")
                    if tid:
                        tool_id_to_name[tid] = tname
        tc = m.get("tool_calls")
        if tc and isinstance(tc, list):
            for call in tc:
                if isinstance(call, dict):
                    tid = call.get("id", "")
                    tname = call.get("function", {}).get("name", "")
                    if tid:
                        tool_id_to_name[tid] = tname

    # Step 1: 收集每个文件路径的所有读取位置 (msg_idx, block_idx)
    # 用 tool_id_map 精确匹配文件路径
    file_reads: Dict[str, List[Tuple[int, int, int]]] = {}  # path -> [(msg_idx, block_idx, text_len)]

    for i, m in enumerate(messages):
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if not isinstance(content, list):
            continue
        for j, b in enumerate(content):
            if not isinstance(b, dict) or b.get("type") != "tool_result":
                continue
            tool_use_id = _get_tool_result_id(b)
            tool_name = tool_id_to_name.get(tool_use_id, "")
            if not _is_read_tool_name(tool_name):
                continue
            text = _get_result_text(b)
            if len(text) < 200:
                continue
            # 获取文件路径
            path = _id_map.get(tool_use_id, "")
            if not path:
                # fallback: 从 tool_result 文本前几行提取路径
                path = _extract_file_path_key(text) or ""
            if not path:
                continue
            if path not in file_reads:
                file_reads[path] = []
            file_reads[path].append((i, j, len(text)))

    # Step 2: 对于被读取多次的文件，合并分段读取，保留最后一次位置放合并结果
    replace_targets: Dict[Tuple[int, int], str] = {}  # (msg_idx, block_idx) -> replacement text

    for path, reads in file_reads.items():
        if len(reads) < 2:
            continue  # 只读了一次，不处理

        # 智能去重：判断是"全量重读"还是"分段读取"
        #
        # 全量重读：同一文件被完整读取多次（比如文件被修改后重读）
        #   → 只保留最后一次，早期替换为指针
        #
        # 分段读取：同一文件的不同行范围（比如先读 1-100，再读 200-300）
        #   → 每段都是独立信息，不能去重
        #
        # 判断方法：比较最后一次读取的长度和历史最大读取长度
        #   - 最后一次 >= 最大的 70% → 大概率是全量重读，可以去重
        #   - 最后一次明显更短 → 大概率是分段读取，保留所有片段

        last_len = reads[-1][2]
        max_len = max(r[2] for r in reads)

        if last_len >= max_len * 0.70:
            # 全量重读模式：早期读取替换为指针
            for read_info in reads[:-1]:
                mi, bi, text_len = read_info
                replace_targets[(mi, bi)] = f"[System: earlier read of {path} was deduplicated to save context space. The file content is unchanged — refer to the latest Read result below for current content.]"
        else:
            # 分段读取模式：检查是否有完全重复的片段（内容 hash 相同）
            # 只去重内容完全相同的读取，不同片段全部保留
            seen_hashes: Dict[str, int] = {}  # content_hash -> last_seen_index_in_reads
            for ri, (mi, bi, text_len) in enumerate(reads):
                block = messages[mi]["content"][bi]
                text = _get_result_text(block)
                h = hashlib.md5(text[:2000].encode()).hexdigest()
                if h in seen_hashes:
                    # 完全重复的片段，去重早期的
                    prev_ri = seen_hashes[h]
                    prev_mi, prev_bi, _ = reads[prev_ri]
                    if (prev_mi, prev_bi) not in replace_targets:
                        replace_targets[(prev_mi, prev_bi)] = f"[System: duplicate read of {path} deduplicated — same content appears later.]"
                seen_hashes[h] = ri

    if not replace_targets:
        return messages, 0

    # Step 3: 应用替换（早期读取 → 指针）
    for (mi, bi), replacement in replace_targets.items():
        m = result[mi]
        content = m.get("content", "")
        if not isinstance(content, list):
            continue

        # 只在第一次修改时复制消息
        if result[mi] is messages[mi]:
            result[mi] = dict(m)
            result[mi]["content"] = list(content)

        block = result[mi]["content"][bi]
        original_text = _get_result_text(block)
        saved_chars += len(original_text) - len(replacement)
        new_block = dict(block)
        _set_result_text_inplace(new_block, replacement)
        result[mi]["content"][bi] = new_block

    if saved_chars > 0:
        saved_tokens = _estimate_tokens(" " * abs(saved_chars)) if saved_chars > 0 else 0
        deduped_count = len(replace_targets)
        unique_files = len([p for p, reads in file_reads.items() if len(reads) >= 2])
        logger.info(
            f"[Compression L0.5] Deduplicated {deduped_count} repeated file reads "
            f"({unique_files} files), saved ~{saved_tokens} tokens ({saved_chars // 1000}K chars)"
        )

    return result, saved_chars


# ==================================================================================================
# Always-on: 骨架化早期 Read 结果（不依赖 token 超限触发）
# ==================================================================================================

def _always_skeletonize_early_reads(
    messages: List[Dict[str, Any]],
    tools: Optional[List] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    始终对非 RECENT 的 Read tool_result 做 AST 骨架化。

    核心理念：早期读取的代码文件只需要结构信息（import + 签名 + 类型），
    不需要函数体实现细节。模型如果需要细节会重新 Read。
    最近 RECENT_MESSAGES_PROTECTED 条消息保留全文（正在编辑需要精确匹配）。

    这个函数在 token 超限判断之前运行，是"常态"操作而非"压缩"操作。

    Returns:
        (processed_messages, stats_dict)
        stats_dict: {"count": N, "saved_tokens": N}
    """
    stats = {"count": 0, "saved_tokens": 0}

    if len(messages) < 4:
        return messages, stats

    priorities = _compute_priorities(messages)
    tool_id_map = _build_tool_id_to_path(messages)
    tool_name_map = _build_tool_id_to_name(messages)

    total_msgs = len(messages)
    compressions: Dict[int, Dict[int, str]] = {}

    for i, m in enumerate(messages):
        # 只处理非 RECENT 的 user 消息
        if priorities[i] >= PRIORITY_RECENT:
            continue
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if not isinstance(content, list):
            continue

        for j, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue

            text = _get_result_text(block)
            # 只处理较大的 Read 结果（小的不值得骨架化）
            if len(text) < 2000:
                continue

            tool_use_id = _get_tool_result_id(block)
            tool_name = tool_name_map.get(tool_use_id, "")
            hint_path = tool_id_map.get(tool_use_id, "")

            # 只对 Read 类工具做骨架化
            tool_lower = tool_name.lower() if tool_name else ""
            if tool_lower and tool_lower not in ("read", "read_file", "readfile"):
                continue

            # 检测语言 — 只对代码文件做骨架化
            lang = _detect_language_from_text(text, hint_path=hint_path)
            if not lang or lang in ("markdown", "json", "yaml", "toml", "css", "scss", "sql", "html"):
                continue

            # 尝试 tree-sitter 骨架化
            skeleton = None
            if _TS_AVAILABLE:
                skeleton = _skeletonize_with_treesitter(text, lang)
                if skeleton and len(skeleton) >= len(text) * 0.95:
                    skeleton = None  # 压缩效果不明显

            # Fallback: 正则骨架化
            if skeleton is None and (lang or _looks_like_code(text)):
                regex_result = _skeletonize_with_regex(text)
                if len(regex_result) < len(text) * 0.80:
                    skeleton = regex_result

            if skeleton is None:
                continue

            if i not in compressions:
                compressions[i] = {}
            compressions[i][j] = skeleton
            stats["count"] += 1
            stats["saved_tokens"] += _estimate_tokens(text) - _estimate_tokens(skeleton)

    if not compressions:
        return messages, stats

    result = []
    for i, m in enumerate(messages):
        if i in compressions:
            result.append(_apply_block_compressions(m, compressions[i]))
        else:
            result.append(m)

    return result, stats


# ==================================================================================================
# 消息辅助函数（Zone 系统使用）
# ==================================================================================================

def _msg_has_tool_use(m: Dict[str, Any]) -> bool:
    """检查消息是否包含 tool_use（Anthropic 或 OpenAI 格式）。"""
    content = m.get("content", "")
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                return True
    tc = m.get("tool_calls")
    if tc and isinstance(tc, list) and len(tc) > 0:
        return True
    return False


def _msg_has_tool_result(m: Dict[str, Any]) -> bool:
    """检查消息是否包含 tool_result。"""
    content = m.get("content", "")
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                return True
    return False


def _estimate_msg_tokens(m: Dict[str, Any]) -> int:
    """估算单条消息的 token 数。"""
    total = 0
    content = m.get("content", "")
    if isinstance(content, str):
        total += _estimate_tokens(content)
    elif isinstance(content, list):
        total += _estimate_tokens(json.dumps(content, ensure_ascii=False))
    tc = m.get("tool_calls")
    if tc:
        total += _estimate_tokens(json.dumps(tc, ensure_ascii=False))
    return total


# ==================================================================================================
# 上下文引导提示词注入
# ==================================================================================================

def _inject_context_guidance(
    messages: List[Dict[str, Any]],
    stats: Dict[str, Any],
    total_original: int,
) -> List[Dict[str, Any]]:
    """
    在压缩后的消息列表中注入一条 system 消息，告诉模型上下文的分区和压缩情况。

    只在以下条件同时满足时注入：
      1. 确实有压缩发生（tokens_saved > 0）
      2. 消息数 > ZONE_B_SIZE（短对话不需要）
      3. 非 subagent 模式
    """
    if stats.get("tokens_saved", 0) <= 0:
        return messages
    if stats.get("subagent_mode"):
        return messages
    if total_original <= ZONE_B_SIZE:
        return messages

    total_msgs = len(messages)
    zone_d_start, zone_c_start, zone_b_start, zone_a_start = _classify_zones(total_msgs)

    # 构建分区描述
    parts = []
    if zone_d_start > 0:
        parts.append(
            f"- Messages before index {zone_d_start} were from Zone E and have been removed entirely."
        )
    if zone_c_start > zone_d_start:
        parts.append(
            f"- Zone D (messages {zone_d_start}-{zone_c_start - 1}): "
            f"Heavily summarized. Tool results show only file paths and brief excerpts. "
            f"Assistant responses are condensed to key decisions only."
        )
    if zone_b_start > zone_c_start:
        parts.append(
            f"- Zone C (messages {zone_c_start}-{zone_b_start - 1}): "
            f"Moderately compressed. Code files are reduced to AST skeletons "
            f"(imports + signatures + type definitions). Tool inputs are folded."
        )
    if zone_a_start > zone_b_start:
        parts.append(
            f"- Zone B (messages {zone_b_start}-{zone_a_start - 1}): "
            f"Mostly preserved. Only very large results (>15K chars) may be trimmed."
        )
    parts.append(
        f"- Zone A (messages {zone_a_start}-{total_msgs - 1}): "
        f"Fully preserved, no compression applied."
    )

    zone_desc = "\n".join(parts)
    saved_k = stats.get("tokens_saved", 0) // 1000

    guidance = (
        f"[Context Compression Notice]\n"
        f"This conversation's context has been compressed to fit the token window "
        f"(saved ~{saved_k}K tokens). The messages are organized into zones by recency:\n"
        f"\n{zone_desc}\n\n"
        f"If you need details from compressed older messages (Zone C/D), "
        f"re-read the relevant files instead of relying on the truncated content. "
        f"Focus on the user's most recent request and the fully preserved Zone A/B messages."
    )

    # 找到第一条 system 消息，追加到其末尾；如果没有 system 消息，插入一条新的
    result = list(messages)
    injected = False
    for i, m in enumerate(result):
        if m.get("role") == "system":
            old_content = m.get("content", "")
            new_m = dict(m)
            if isinstance(old_content, str):
                new_m["content"] = old_content + "\n\n" + guidance
            else:
                new_m["content"] = guidance
            result[i] = new_m
            injected = True
            break

    if not injected:
        # 在最前面插入一条 system 消息
        result.insert(0, {"role": "system", "content": guidance})

    return result


# ==================================================================================================
# 主入口：compress_context
# ==================================================================================================

def compress_context(
    messages: List[Dict[str, Any]],
    tools: Optional[List] = None,
    context_window: int = DEFAULT_CONTEXT_WINDOW,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    基于消息分区（Zone）的智能上下文压缩系统 — 五区策略。

    消息按距离末尾的位置分为五个区域，压缩力度递增：
      Zone A（最近 10 条）  ：绝对保护，不动
      Zone B（最近 11-30 条）：基本保留，只做去重和图片压缩
      Zone C（最近 31-60 条）：中度压缩，AST 骨架化 + 工具摘要
      Zone D（最近 61-120 条）：简要概要
      Zone E（120 条之前）  ：直接删掉

    处理流程：
      Step 0: Subagent 检测（特殊模式，只做骨架化）
      Step 1: Zone E 删除（>120 条的消息直接丢弃，保留 system 消息）
      Step 2: 全局清理 — 去重 + 重试循环 + 图片压缩
      Step 3: Zone D 概要化 — tool_result 极简摘要 + assistant 决策摘要
      Step 4: Zone C 骨架化 — tool_result AST 骨架 + assistant 折叠
      Step 5: 阈值检查 — 如果仍超标，对 Zone B 做轻压缩
      Step 6: Safety Valve — 最后手段，激进 head_tail
    """
    trigger_threshold = int(context_window * COMPRESSION_TRIGGER_RATIO)
    target_tokens = int(context_window * COMPRESSION_TARGET_RATIO)
    original_tokens = estimate_request_tokens(messages, tools)

    # ── 分区计算 ──
    total_msgs = len(messages)
    zone_d_start, zone_c_start, zone_b_start, zone_a_start = _classify_zones(total_msgs)

    stats = {
        "level": 0,
        "original_tokens": original_tokens,
        "final_tokens": original_tokens,
        "tokens_saved": 0,
        "tree_sitter": _TS_AVAILABLE,
        "zones": (
            f"E:[0,{zone_d_start}) D:[{zone_d_start},{zone_c_start}) "
            f"C:[{zone_c_start},{zone_b_start}) B:[{zone_b_start},{zone_a_start}) "
            f"A:[{zone_a_start},{total_msgs})"
        ),
    }

    # ── 构建工具映射（全局使用）──
    tool_id_map = _build_tool_id_to_path(messages)
    tool_name_map = _build_tool_id_to_name(messages)

    # ── Subagent 模式检测 ──
    # Cursor subagent（文件搜索/分析子任务）的 Read 结果是分析"原材料"，
    # 只允许 AST 骨架化，不允许其他破坏性压缩。
    # 注意：subagent 消息数少，全部在 Zone A/B 内，所以不能用 _always_skeletonize_early_reads
    # （它只处理非 RECENT 消息）。需要对所有 Read 做骨架化，只保护最后 2 条消息。
    is_subagent = _detect_subagent_mode(messages)
    if is_subagent:
        stats["subagent_mode"] = True
        current = list(messages)
        protect_last = 2  # 保护最后 2 条消息（正在进行的 tool_use/result）
        safe_end = max(0, total_msgs - protect_last)
        saved_sub = 0
        count_sub = 0
        compressions_sub: Dict[int, Dict[int, str]] = {}

        for i in range(safe_end):
            m = current[i]
            if m.get("role") != "user":
                continue
            content = m.get("content", "")
            if not isinstance(content, list):
                continue
            for j, block in enumerate(content):
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                text = _get_result_text(block)
                if len(text) < 2000:
                    continue
                tool_use_id = _get_tool_result_id(block)
                tool_name = tool_name_map.get(tool_use_id, "")
                hint_path = tool_id_map.get(tool_use_id, "")
                # 只对 Read 类工具做骨架化（空 tool_name 也尝试，因为映射可能缺失）
                tool_lower = tool_name.lower() if tool_name else ""
                if tool_lower and tool_lower not in ("read", "read_file", "readfile"):
                    logger.debug(f"[Subagent] skip non-read tool: {tool_name} id={tool_use_id[:20]}")
                    continue
                lang = _detect_language_from_text(text, hint_path=hint_path)
                if not lang or lang in ("markdown", "json", "yaml", "toml", "css", "scss", "sql", "html"):
                    logger.debug(f"[Subagent] skip lang={lang} path={hint_path} text[:80]={text[:80]!r}")
                    continue
                skeleton = None
                if _TS_AVAILABLE:
                    skeleton = _skeletonize_with_treesitter(text, lang)
                    if skeleton and len(skeleton) >= len(text) * 0.95:
                        skeleton = None
                if skeleton is None and (lang or _looks_like_code(text)):
                    regex_result = _skeletonize_with_regex(text)
                    if len(regex_result) < len(text) * 0.80:
                        skeleton = regex_result
                if skeleton is None:
                    continue
                if i not in compressions_sub:
                    compressions_sub[i] = {}
                compressions_sub[i][j] = skeleton
                count_sub += 1
                saved_sub += _estimate_tokens(text) - _estimate_tokens(skeleton)

        if compressions_sub:
            for i in compressions_sub:
                current[i] = _apply_block_compressions(current[i], compressions_sub[i])
            current_tokens = estimate_request_tokens(current, tools)
            logger.info(
                f"[Compression] Subagent mode: skeleton-only, "
                f"{count_sub} reads, saved ~{saved_sub} tokens "
                f"({original_tokens // 1000}K -> {current_tokens // 1000}K)"
            )
            stats["level"] = 1
            stats["final_tokens"] = current_tokens
            stats["tokens_saved"] = original_tokens - current_tokens
        else:
            current_tokens = original_tokens
            logger.info(
                f"[Compression] Subagent mode: no skeleton candidates "
                f"({original_tokens // 1000}K tokens)"
            )

        # ── 第二步：代码骨架化后仍超限 → markdown 骨架化 ──
        if current_tokens > trigger_threshold:
            saved_md = 0
            count_md = 0
            compressions_md: Dict[int, Dict[int, str]] = {}

            for i in range(safe_end):
                m = current[i]
                if m.get("role") != "user":
                    continue
                content = m.get("content", "")
                if not isinstance(content, list):
                    continue
                for j, block in enumerate(content):
                    if not isinstance(block, dict) or block.get("type") != "tool_result":
                        continue
                    text = _get_result_text(block)
                    if len(text) < 2000:
                        continue
                    tool_use_id = _get_tool_result_id(block)
                    hint_path = tool_id_map.get(tool_use_id, "")
                    lang = _detect_language_from_text(text, hint_path=hint_path)
                    if lang != "markdown":
                        continue
                    skeleton = _skeletonize_markdown(text)
                    if skeleton is None:
                        continue
                    if i not in compressions_md:
                        compressions_md[i] = {}
                    compressions_md[i][j] = skeleton
                    count_md += 1
                    saved_md += _estimate_tokens(text) - _estimate_tokens(skeleton)

            if compressions_md:
                for i in compressions_md:
                    current[i] = _apply_block_compressions(current[i], compressions_md[i])
                current_tokens = estimate_request_tokens(current, tools)
                logger.info(
                    f"[Compression] Subagent markdown skeleton: "
                    f"{count_md} files, saved ~{saved_md} tokens "
                    f"({stats.get('final_tokens', original_tokens) // 1000}K -> {current_tokens // 1000}K)"
                )
                stats["final_tokens"] = current_tokens
                stats["tokens_saved"] = original_tokens - current_tokens

        return current, stats

    # ======================================================================
    # ── Step 1: Zone E 删除（120 条之前直接丢弃，保留 system 消息）──
    # ======================================================================
    current = list(messages)
    dropped_e = 0
    if zone_d_start > 0:
        kept = []
        for i, m in enumerate(current):
            if i < zone_d_start:
                if m.get("role") == "system":
                    kept.append(m)  # system 消息永远保留
                else:
                    dropped_e += 1
            else:
                kept.append(m)
        if dropped_e > 0:
            current = kept
            current_tokens = estimate_request_tokens(current, tools)
            logger.info(
                f"[Compression S1] Zone E: dropped {dropped_e} messages "
                f"({original_tokens // 1000}K -> {current_tokens // 1000}K)"
            )
    else:
        current_tokens = original_tokens

    # 删除后重新计算分区（消息数变了）
    total_msgs = len(current)
    zone_d_start, zone_c_start, zone_b_start, zone_a_start = _classify_zones(total_msgs)

    # ── Dump 原始消息（方便调试）──
    _dump_id = None
    try:
        import os as _os, time as _time
        _dump_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "compression_logs")
        _os.makedirs(_dump_dir, exist_ok=True)
        try:
            _files = sorted(_os.listdir(_dump_dir))
            if len(_files) > 100:
                for _old in _files[:len(_files) - 100]:
                    _os.remove(_os.path.join(_dump_dir, _old))
        except Exception:
            pass
        _dump_id = _time.strftime("%H%M%S")
        with open(_os.path.join(_dump_dir, f"req_{_dump_id}_before.json"), "w", encoding="utf-8") as _f:
            _d = {"token_estimate": original_tokens, "message_count": len(messages), "messages": messages}
            if tools:
                _d["tools"] = tools
            json.dump(_d, _f, ensure_ascii=False, indent=1)
    except Exception:
        pass

    # ======================================================================
    # ── Step 2: 全局清理（去重 + 重试循环 + 图片）──
    # ======================================================================
    current, removed = _clean_retry_loops(current)
    if removed > 0:
        current_tokens = estimate_request_tokens(current, tools)

    current, deduped = _deduplicate_tool_results(current)
    if deduped > 0:
        current_tokens = estimate_request_tokens(current, tools)

    priorities = _compute_priorities(current)
    current, digested_saved = _cleanup_digested_reads(current, priorities, tool_id_map=tool_id_map)
    if digested_saved > 0:
        current_tokens = estimate_request_tokens(current, tools)

    priorities = _compute_priorities(current)
    current, img_saved = _compress_image_blocks(current, priorities)
    if img_saved > 0:
        current_tokens = estimate_request_tokens(current, tools)

    # 清理后重新计算分区
    total_msgs = len(current)
    zone_d_start, zone_c_start, zone_b_start, zone_a_start = _classify_zones(total_msgs)

    # ======================================================================
    # ── Step 3: Zone D 概要化（61-120 条：tool_result 极简摘要 + assistant 决策摘要）──
    # ======================================================================
    saved_s3 = 0

    # 3a: Zone D tool_result → 极简摘要（只保留文件路径 + 前几行）
    compressions_s3: Dict[int, Dict[int, str]] = {}
    for i in range(zone_d_start, zone_c_start):
        m = current[i]
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if not isinstance(content, list):
            continue
        for j, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            text = _get_result_text(block)
            if len(text) < 500:
                continue
            tool_use_id = _get_tool_result_id(block)
            hint_path = tool_id_map.get(tool_use_id, "")
            t_name = tool_name_map.get(tool_use_id, "")
            # Zone D: 极简 — 只保留路径标识 + head_tail(5%)
            compressed = _head_tail_compress(text, 0.05)
            if hint_path:
                compressed = f"[{hint_path}]\n{compressed}"
            sc = len(text) - len(compressed)
            if sc > 0:
                if i not in compressions_s3:
                    compressions_s3[i] = {}
                compressions_s3[i][j] = compressed
                saved_s3 += _estimate_tokens(text) - _estimate_tokens(compressed)

    if compressions_s3:
        for i in compressions_s3:
            current[i] = _apply_block_compressions(current[i], compressions_s3[i])
        current_tokens = estimate_request_tokens(current, tools)
        count_s3a = sum(len(v) for v in compressions_s3.values())
        logger.info(f"[Compression S3a] Zone D: summarized {count_s3a} tool_results, saved ~{saved_s3} tokens")

    # 3b: Zone D assistant → 决策摘要 + tool_use input 折叠
    saved_s3b = 0
    for i in range(zone_d_start, zone_c_start):
        m = current[i]
        if m.get("role") != "assistant":
            continue
        content = m.get("content", "")

        if isinstance(content, str) and len(content) > 200:
            summary = _extract_decision_summary(content)
            sc = len(content) - len(summary)
            if sc > 0:
                new_m = dict(m)
                new_m["content"] = summary
                current[i] = new_m
                saved_s3b += _estimate_tokens(content) - _estimate_tokens(summary)

        elif isinstance(content, list):
            new_content = []
            msg_saved = 0
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    inp = block.get("input", {})
                    if isinstance(inp, dict) and len(json.dumps(inp, ensure_ascii=False)) > 300:
                        slim_inp = {}
                        for k in ("path", "relative_workspace_path", "command", "pattern"):
                            if k in inp:
                                slim_inp[k] = inp[k]
                        new_block = dict(block)
                        new_block["input"] = slim_inp
                        msg_saved += len(json.dumps(inp, ensure_ascii=False)) - len(json.dumps(slim_inp, ensure_ascii=False))
                        new_content.append(new_block)
                        continue
                elif isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if len(text) > 200:
                        compressed = _head_tail_compress(text, 0.10)
                        msg_saved += len(text) - len(compressed)
                        new_content.append({"type": "text", "text": compressed})
                        continue
                new_content.append(block)
            if msg_saved > 0:
                new_m = dict(m)
                new_m["content"] = new_content
                current[i] = new_m
                saved_s3b += _estimate_tokens(" " * msg_saved)

        # tool_calls (OpenAI 格式)
        tc = m.get("tool_calls")
        if tc and isinstance(tc, list):
            new_tc = []
            tc_saved = 0
            for call in tc:
                if not isinstance(call, dict):
                    new_tc.append(call)
                    continue
                func = call.get("function", {})
                args_str = func.get("arguments", "")
                if not isinstance(args_str, str) or len(args_str) < 300:
                    new_tc.append(call)
                    continue
                try:
                    args_obj = json.loads(args_str)
                except (json.JSONDecodeError, TypeError):
                    new_tc.append(call)
                    continue
                cflag = False
                for field in ("old_string", "new_string", "old_str", "new_str",
                              "content", "file_text", "code", "text", "diff"):
                    val = args_obj.get(field)
                    if isinstance(val, str) and len(val) > 200:
                        args_obj[field] = val[:60] + f" ... [{len(val)} chars] ... " + val[-60:]
                        tc_saved += len(val) - len(args_obj[field])
                        cflag = True
                if cflag:
                    new_call = dict(call)
                    new_call["function"] = dict(func)
                    new_call["function"]["arguments"] = json.dumps(args_obj, ensure_ascii=False)
                    new_tc.append(new_call)
                else:
                    new_tc.append(call)
            if tc_saved > 0:
                if current[i] is m:
                    current[i] = dict(m)
                current[i]["tool_calls"] = new_tc
                saved_s3b += _estimate_tokens(" " * tc_saved)

    if saved_s3b > 0:
        current_tokens = estimate_request_tokens(current, tools)
        logger.info(f"[Compression S3b] Zone D: summarized assistants, saved ~{saved_s3b} tokens")

    # ======================================================================
    # ── Step 4: Zone C 骨架化（31-60 条：AST 骨架 + 工具摘要）──
    # ======================================================================
    saved_s4 = 0
    compressions_s4: Dict[int, Dict[int, str]] = {}

    for i in range(zone_c_start, zone_b_start):
        m = current[i]
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if not isinstance(content, list):
            continue
        for j, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            text = _get_result_text(block)
            if len(text) < LARGE_RESULT_THRESHOLD:
                continue
            tool_use_id = _get_tool_result_id(block)
            hint_path = tool_id_map.get(tool_use_id, "")
            t_name = tool_name_map.get(tool_use_id, "")
            # Zone C: AST 骨架化（保留结构）
            compressed = _skeletonize_for_map(text, tool_name=t_name, hint_path=hint_path)
            sc = len(text) - len(compressed)
            if sc > 0:
                if i not in compressions_s4:
                    compressions_s4[i] = {}
                compressions_s4[i][j] = compressed
                saved_s4 += _estimate_tokens(text) - _estimate_tokens(compressed)

    if compressions_s4:
        for i in compressions_s4:
            current[i] = _apply_block_compressions(current[i], compressions_s4[i])
        current_tokens = estimate_request_tokens(current, tools)
        count_s4 = sum(len(v) for v in compressions_s4.values())
        logger.info(f"[Compression S4a] Zone C: skeletonized {count_s4} tool_results, saved ~{saved_s4} tokens")

    # 4b: Zone C assistant → 折叠
    priorities = _compute_priorities(current)
    current, saved_s4b = _compress_early_conversations(
        current, target_tokens, current_tokens, priorities,
        max_idx=zone_b_start,
    )
    if saved_s4b > 0:
        current_tokens = estimate_request_tokens(current, tools)
        logger.info(f"[Compression S4b] Zone C: folded assistants, saved ~{saved_s4b} tokens")

    # ======================================================================
    # ── 常态化阶段结束，检查是否需要进入阈值触发阶段 ──
    # ======================================================================
    if current_tokens <= trigger_threshold:
        stats["level"] = 4
        stats["final_tokens"] = current_tokens
        stats["tokens_saved"] = original_tokens - current_tokens
        if stats["tokens_saved"] > 0:
            logger.info(
                f"[Compression] Done after Step 4, below trigger: "
                f"{current_tokens // 1000}K tokens (saved {stats['tokens_saved'] // 1000}K)"
            )
        _dump_compressed(current, stats, _dump_id)
        current = _inject_context_guidance(current, stats, len(messages))
        return current, stats

    logger.info(
        f"[Compression] Still over trigger after Step 4: "
        f"{current_tokens // 1000}K >= {trigger_threshold // 1000}K, "
        f"target={target_tokens // 1000}K — entering threshold-gated phases"
    )

    # ======================================================================
    # ── Step 5: Zone B 轻压缩（阈值触发）— 只对超大 tool_result (>15K) 做 head_tail ──
    # ======================================================================
    total_msgs = len(current)
    zone_d_start, zone_c_start, zone_b_start, zone_a_start = _classify_zones(total_msgs)

    saved_s5 = 0
    compressions_s5: Dict[int, Dict[int, str]] = {}
    tokens_to_save = current_tokens - target_tokens

    for i in range(zone_b_start, zone_a_start):
        if saved_s5 >= tokens_to_save:
            break
        m = current[i]
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if not isinstance(content, list):
            continue
        for j, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            text = _get_result_text(block)
            if len(text) < 15000:
                continue
            compressed = _head_tail_compress(text, 0.35)
            sc = len(text) - len(compressed)
            if sc > 0:
                if i not in compressions_s5:
                    compressions_s5[i] = {}
                compressions_s5[i][j] = compressed
                saved_s5 += _estimate_tokens(text) - _estimate_tokens(compressed)

    if compressions_s5:
        for i in compressions_s5:
            current[i] = _apply_block_compressions(current[i], compressions_s5[i])
        current_tokens = estimate_request_tokens(current, tools)
        count_s5 = sum(len(v) for v in compressions_s5.values())
        logger.info(f"[Compression S5] Zone B: head_tail {count_s5} large results (>15K), saved ~{saved_s5} tokens")

    if current_tokens <= target_tokens:
        stats["level"] = 5
        stats["final_tokens"] = current_tokens
        stats["tokens_saved"] = original_tokens - current_tokens
        logger.info(f"[Compression] Done at Step 5: {current_tokens // 1000}K tokens")
        _dump_compressed(current, stats, _dump_id)
        current = _inject_context_guidance(current, stats, len(messages))
        return current, stats

    # ======================================================================
    # ── Step 6: Safety Valve — 激进 head_tail（Zone A 仍不动）──
    # ======================================================================
    total_msgs = len(current)
    zone_d_start, zone_c_start, zone_b_start, zone_a_start = _classify_zones(total_msgs)

    saved_s6 = 0
    compressions_s6: Dict[int, Dict[int, str]] = {}
    tokens_to_save = current_tokens - target_tokens

    for i, m in enumerate(current):
        if saved_s6 >= tokens_to_save:
            break
        if i >= zone_a_start:
            break
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if not isinstance(content, list):
            continue
        for j, block in enumerate(content):
            if saved_s6 >= tokens_to_save:
                break
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            text = _get_result_text(block)
            if len(text) < 1000:
                continue
            if len(text) > 10000:
                keep_ratio = 0.05
            elif len(text) > 5000:
                keep_ratio = 0.10
            else:
                keep_ratio = 0.15
            compressed = _head_tail_compress(text, keep_ratio)
            sc = len(text) - len(compressed)
            if sc > 0:
                if i not in compressions_s6:
                    compressions_s6[i] = {}
                compressions_s6[i][j] = compressed
                saved_s6 += _estimate_tokens(text) - _estimate_tokens(compressed)

    if compressions_s6:
        for i in compressions_s6:
            current[i] = _apply_block_compressions(current[i], compressions_s6[i])
        current_tokens = estimate_request_tokens(current, tools)
        count_s6 = sum(len(v) for v in compressions_s6.values())
        logger.info(f"[Compression S6] Safety valve: force-compressed {count_s6} results, saved ~{saved_s6} tokens")

    # ── 如果还超标且 Zone A 占比过高，压 Zone A 的 tool_result ──
    if current_tokens > target_tokens:
        zone_a_tokens = sum(_estimate_msg_tokens(current[i]) for i in range(zone_a_start, len(current)))
        zone_a_ratio = zone_a_tokens / max(current_tokens, 1)

        if zone_a_ratio >= 0.50:
            protect_last_n = 2
            safe_end = max(zone_a_start, len(current) - protect_last_n)
            saved_s6a = 0
            compressions_s6a: Dict[int, Dict[int, str]] = {}
            tokens_to_save = current_tokens - target_tokens

            for i in range(zone_a_start, safe_end):
                if saved_s6a >= tokens_to_save:
                    break
                m = current[i]
                if m.get("role") != "user":
                    continue
                content = m.get("content", "")
                if not isinstance(content, list):
                    continue
                for j, block in enumerate(content):
                    if saved_s6a >= tokens_to_save:
                        break
                    if not isinstance(block, dict) or block.get("type") != "tool_result":
                        continue
                    text = _get_result_text(block)
                    if len(text) < 3000:
                        continue
                    keep_ratio = 0.10 if len(text) > 30000 else (0.20 if len(text) > 10000 else 0.35)
                    compressed = _head_tail_compress(text, keep_ratio)
                    sc = len(text) - len(compressed)
                    if sc > 0:
                        if i not in compressions_s6a:
                            compressions_s6a[i] = {}
                        compressions_s6a[i][j] = compressed
                        saved_s6a += _estimate_tokens(text) - _estimate_tokens(compressed)

            if compressions_s6a:
                for i in compressions_s6a:
                    current[i] = _apply_block_compressions(current[i], compressions_s6a[i])
                current_tokens = estimate_request_tokens(current, tools)
                count_s6a = sum(len(v) for v in compressions_s6a.values())
                logger.info(
                    f"[Compression S6a] Zone A safety: compressed {count_s6a} tool_results "
                    f"(protected last {protect_last_n}), saved ~{saved_s6a} tokens"
                )

    stats["level"] = 6 if saved_s6 > 0 else 5
    stats["final_tokens"] = current_tokens
    stats["tokens_saved"] = original_tokens - current_tokens
    logger.info(f"[Compression] Final: {current_tokens // 1000}K tokens (saved {stats['tokens_saved'] // 1000}K)")
    _dump_compressed(current, stats, _dump_id)
    current = _inject_context_guidance(current, stats, len(messages))
    return current, stats
