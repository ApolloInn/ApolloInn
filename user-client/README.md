# User Client

精简版 9router 用户端。

用户只需：
1. 填入管理员给的 usertoken
2. 首次启动自动配置好 Kiro 模型提供方、连接、模型映射
3. 拿着 9router 的公网地址 + 自定义 API key + 模型名即可调用

## 启动

```bash
npm install
npm run dev
```

首次打开会提示输入 usertoken，之后自动配置完成。
