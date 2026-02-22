# 如何将 client 集成到 9router

## 需要的修改

### 1. 复制文件到 9router

```bash
cp client/auto-setup.js 9router-master/src/lib/kiroAutoSetup.js
cp client/setup-page.js 9router-master/src/shared/components/KiroSetupPage.js
```

### 2. 修改 9router 的 dashboard 入口页

编辑 `9router-master/src/app/(dashboard)/dashboard/page.js`，
在页面加载时检查是否已配置 Kiro Gateway，未配置则显示 SetupPage。

### 3. 修改 server-init.js

在 `9router-master/src/server-init.js` 中添加启动时自动检查逻辑。
