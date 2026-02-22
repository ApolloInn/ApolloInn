"""临时脚本：挂在服务器上，下一次请求时 dump 完整的 tools 定义到文件。
用法：放到 /opt/apollo/ 下，在 proxy.py 中临时加一行调用。

但更简单的方式：直接看 converters_openai.py 中 build_kiro_payload 的 tools 转换逻辑，
Cursor 发来的 tools 就是标准 OpenAI function calling 格式。

实际上我们可以直接看 Cursor 的源码或者从日志中提取。
"""

# Cursor 已知工具列表（从 system prompt 提示 + 实际 tool_use 中收集）:
#
# 1. Read        — 读取文件内容（参数: path）
# 2. Glob        — 文件路径模式匹配（参数: glob_pattern, target_directory）  
# 3. Grep        — 正则搜索（参数: pattern, path, include）
# 4. Search      — 语义搜索 / codebase_search
# 5. Write       — 写入/创建文件（参数: path, content）
# 6. Edit        — 编辑文件（参数: path, old_string, new_string）
# 7. Shell       — 执行命令（参数: command, cwd）
# 8. Delete      — 删除文件
# 9. ListDir     — 列出目录
# 10. ReadLints  — 读取 linter 错误
# 11. todo_write — 任务管理
# 12. web_search — 网页搜索
# 13. fetch_url  — 获取网页内容
#
# 但具体有哪些、description 多长，需要看实际请求。
