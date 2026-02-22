# Tests — 测试

主要测试上下文压缩模块的正确性。

## 运行

```bash
pip install pytest
cd server   # 需要在 server 目录下，因为 import 路径
pytest ../tests/ -v
```

## 测试文件

| 文件 | 测试内容 |
|------|---------|
| `test_compression.py` | 上下文压缩基础功能 |
| `test_comp_v2.py` | 压缩 V2 策略 |
| `test_comp_v3.py` | 压缩 V3 策略 |
| `test_comp_inspect.py` | 压缩结果检查 |
| `test_real_compression.py` | 真实请求数据压缩测试 |
| `test_debug.py` | 调试用测试 |
| `test_treesitter_diag.py` | Tree-sitter 诊断测试 |
| `captured_requests/` | 捕获的真实请求数据（测试用） |
