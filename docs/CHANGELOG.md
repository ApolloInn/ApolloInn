# ApolloInn 更新日志

## v2.4.0 — 2026-02-16

### 🧠 Thinking 模型支持
- 新增 `-thinking` 模型变体（如 `claude-opus-4-6-thinking`），Cursor 模型列表自动生成对应条目
- `reasoning_content` 自动转换为 `<think>...</think>` 标签，Cursor 可正确显示思维链 UI
- `model_resolver` 支持 `-thinking` 后缀的模型名标准化

### 📦 Anthropic Messages API 兼容
- 新增 `/v1/messages` 路由，支持 Anthropic 原生格式的请求转发
- 新增 `converters_anthropic.py`：OpenAI ↔ Anthropic 消息格式双向转换
- 新增 `streaming_anthropic.py`：Anthropic SSE 流式响应处理

### 🗜️ 压缩系统重构
- **常态化压缩**：Phase 1-3b（清理/骨架化/摘要化/折叠）每次请求都执行，不再等超限才触发
  - Zone C/D 的 Read 结果始终做 AST 骨架化
  - Zone D assistant 始终做摘要化 + tool_use input 折叠
  - Zone C assistant 始终做折叠
- **阈值触发阶段**保持不变：Phase 2c（pair dropping）、Phase 4-6 仅在超标时执行
- Zone A（最近 10 条）绝对保护贯穿所有阶段

### 🔍 Subagent 模式
- 新增 `_detect_subagent_mode()`：通过 user 消息中的特征标记（`file search specialist`、`READ-ONLY MODE`、`read-only exploration task`）检测 Cursor subagent
- Subagent 模式下只允许 AST 骨架化，禁止 head_tail 截断、pair dropping、assistant 摘要化等破坏性压缩
- 对所有消息做骨架化（只保护最后 2 条），不受 Zone 分区限制
- 骨架化后仍超限时，自动对 Markdown 文件做结构化骨架化（保留标题/列表/代码块标记，去掉正文段落）

### 📝 Markdown 骨架化
- 新增 `_skeletonize_markdown()`：保留 `#` 标题、列表项、代码块声明、表格行，去掉纯文本段落
- 仅在 subagent 模式下代码骨架化后仍超限时触发，避免不必要的信息损失
