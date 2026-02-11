# 如何将 user-client 集成到 9router

## 需要的修改

### 1. 复制文件到 9router

```bash
cp user-client/auto-setup.js 9router-master/src/lib/kiroAutoSetup.js
cp user-client/setup-page.js 9router-master/src/shared/components/KiroSetupPage.js
```

### 2. 修改 9router 的 dashboard 入口页

编辑 `9router-master/src/app/(dashboard)/dashboard/page.js`，
在页面加载时检查是否已配置 Kiro Gateway，未配置则显示 SetupPage。

### 3. 修改 server-init.js

在 `9router-master/src/server-init.js` 中添加启动时自动检查逻辑。

### 4. 精简不需要的页面

用户端不需要：
- providers 手动管理页面（自动配置）
- translator 页面
- 大部分 CLI tools 页面

只保留：
- endpoint 页面（查看 API 地址和 key）
- combos 页面（查看模型映射）
- profile 页面（管理自己的 API key）
