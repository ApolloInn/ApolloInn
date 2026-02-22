"""从 proxy.py 的日志中找工具名，或者直接看 Cursor 文档中已知的工具列表。
同时修改 compression dump 把 tools 也存进去。"""
import json, sys

# 从本地的 compression_logs 中找一个有 tools 的
# 但 compression_logs 只存了 messages...
# 需要看 proxy.py 的日志

# 已知 Cursor 工具列表（从 system prompt 和实际使用中收集）:
#
# === 读取类（只读，不修改文件）===
# Read / read_file / ReadFile  — 读取文件内容（返回带行号的代码）
# Glob / glob                  — 文件路径模式匹配（返回文件列表）
# Grep / grep / Search         — 正则搜索文件内容（返回匹配行）
# ListDir / list_dir           — 列出目录内容
# ListFiles / list_files       — 列出文件
# ReadLints                    — 读取 linter 错误
#
# === 写入类（修改文件）===
# Write / write_to_file        — 写入/创建文件（返回确认）
# Edit / edit_file             — 编辑文件（返回确认）
# 
# === 执行类 ===
# Shell / run_command           — 执行 shell 命令（返回 stdout/stderr）
#
# === 其他 ===
# todo_write                   — 任务管理
# codebase_search              — 语义搜索
# web_search                   — 网页搜索
# fetch_url                    — 获取网页内容

# 每种工具的 tool_result 压缩策略：
strategies = {
    "Read": {
        "desc": "读取文件内容",
        "result_type": "代码文件全文（带行号）",
        "preserve": "文件路径、import/export、类/函数签名、类型定义、关键注释",
        "compress": "函数体实现细节",
        "method": "AST 骨架化（tree-sitter）",
        "example_before": "1|import { foo } from 'bar';\n2|export class MyClass {\n3|  constructor() {\n4|    this.x = 1;\n5|    this.y = 2;\n...\n50|  }\n51|}",
        "example_after": "File: src/MyClass.ts\nimport { foo } from 'bar';\nexport class MyClass {\n  constructor() { /* ... 47 lines */ }\n}",
    },
    "Glob": {
        "desc": "文件路径匹配",
        "result_type": "文件路径列表",
        "preserve": "完整保留（通常很小）",
        "compress": "不压缩",
        "method": "无",
    },
    "Grep": {
        "desc": "正则搜索",
        "result_type": "匹配行 + 上下文",
        "preserve": "匹配行、文件路径",
        "compress": "上下文行（保留匹配行前后各1行）",
        "method": "减少上下文行数",
    },
    "Write": {
        "desc": "写入文件",
        "result_type": "确认消息（很短）",
        "preserve": "完整保留",
        "compress": "不压缩",
        "method": "无",
    },
    "Edit": {
        "desc": "编辑文件",
        "result_type": "确认消息（很短）",
        "preserve": "完整保留",
        "compress": "不压缩",
        "method": "无",
    },
    "Shell": {
        "desc": "执行命令",
        "result_type": "stdout/stderr 输出",
        "preserve": "命令、退出码、错误信息、最后几行输出",
        "compress": "中间的大量输出（如 npm install 的进度条）",
        "method": "head_tail（保留前10行+后20行）",
    },
    "ListDir": {
        "desc": "列出目录",
        "result_type": "文件/目录列表",
        "preserve": "完整保留（通常不大）",
        "compress": "不压缩",
        "method": "无",
    },
    "codebase_search": {
        "desc": "语义搜索",
        "result_type": "匹配的代码片段",
        "preserve": "文件路径、匹配片段",
        "compress": "上下文代码",
        "method": "只保留匹配行",
    },
}

for name, s in strategies.items():
    print(f"=== {name} ({s['desc']}) ===")
    print(f"  Result: {s['result_type']}")
    print(f"  Preserve: {s['preserve']}")
    print(f"  Compress: {s['compress']}")
    print(f"  Method: {s['method']}")
    print()
