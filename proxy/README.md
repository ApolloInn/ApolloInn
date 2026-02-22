# 代理节点配置

Xray + nginx + Cloudflare CDN 代理节点的配置模板。

## 文件说明

| 文件 | 说明 |
|------|------|
| `xray-config.json` | Xray 配置（VLESS + VMess，两台服务器通用） |
| `nginx-proxy.conf` | nginx 反代模板（`{{DOMAIN}}` 替换为实际域名） |
| `sub-template.yaml` | Clash/Stash 订阅模板（`{{DOMAIN}}` + `{{NODE_NAME}}`） |

## 部署新节点

```bash
# 1. 安装 xray
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install

# 2. 复制 xray 配置
cp xray-config.json /usr/local/etc/xray/config.json
systemctl restart xray

# 3. 复制 nginx 配置，替换域名
sed 's/{{DOMAIN}}/proxy-xx.apolloinn.site/g' nginx-proxy.conf > /etc/nginx/sites-enabled/proxy

# 4. 申请 SSL 证书
certbot certonly --nginx -d proxy-xx.apolloinn.site

# 5. 生成订阅文件
sed 's/{{DOMAIN}}/proxy-xx.apolloinn.site/g; s/{{NODE_NAME}}/Apollo-XX/g' sub-template.yaml > /var/www/sub.yaml

# 6. 重载 nginx
nginx -s reload
```

## 注意事项

- 模板端口：vless=10001, vmess=10002
- OR 历史遗留端口不同：vless=10086, vmess=10087，部署时注意对应修改 nginx 的 proxy_pass
- Cloudflare SSL 模式需设为 Flexible 或 Full，避免 301 循环
- HTTP 80 端口不做 301 跳转（Cloudflare 回源走 HTTP）

## 当前节点

| 节点 | 域名 | IP | 订阅 |
|------|------|----|------|
| 🇺🇸 美国 (Oregon) | `proxy-us.apolloinn.site` | 44.248.224.204 | `https://proxy-us.apolloinn.site/sub` |
| 🇯🇵 日本 (Tokyo) | `proxy-jp.apolloinn.site` | 43.206.212.53 | `https://proxy-jp.apolloinn.site/sub` |

每个订阅包含 4 个节点，命名规范：`国旗 地区 | 协议 | 连接方式`

| 节点名 | 协议 | 连接方式 | 说明 |
|--------|------|----------|------|
| XX \| VMess \| CDN | VMess | Cloudflare CDN | 兼容性好，抗封 |
| XX \| VLess \| CDN | VLess | Cloudflare CDN | 更轻量，抗封 |
| XX \| VMess \| Direct | VMess | 直连 IP | 低延迟 |
| XX \| VLess \| Direct | VLess | 直连 IP | 低延迟，直连被封时用 CDN |
