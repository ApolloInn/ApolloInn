# Scripts — 运维和分析脚本

独立的 Python 脚本，用于数据分析、调试和运维操作。不依赖服务器运行。

## 常用脚本

| 脚本 | 用途 |
|------|------|
| `import_tokens.py` | 批量导入 Token 到数据库 |
| `validate_accounts.py` | 验证 Cursor 账号有效性 |
| `add_balance.py` | 给用户充值额度 |
| `analyze_compression.py` | 分析上下文压缩效果 |
| `analyze_loop.py` | 分析 Cursor Agent 循环请求模式 |
| `analyze_trace.py` | 分析请求 trace 日志 |

## 使用

大部分脚本需要数据库连接或日志文件作为输入：

```bash
# 示例
python scripts/import_tokens.py --db postgresql://apollo:pass@localhost/apollo
python scripts/analyze_compression.py server/compression_logs/
```

## 修改指南

这些都是一次性或低频使用的脚本，直接改就行，不影响线上服务。
