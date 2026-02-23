# 部署手册

## 环境要求

- Python 3.10+
- PostgreSQL 14+
- nginx（反向代理 + TLS）
- Cloudflare（DNS + CDN）

## 服务器拓扑

| 角色 | 域名 | 区域 |
|------|------|------|
| API 主力 | `api.apolloinn.site` | 美东 Ohio |
| API 备用 | `api2.apolloinn.site` | 美西 Oregon |
| API 备用 | `api3.apolloinn.site` | 日本 Tokyo |
| 测试 | `test.apolloinn.site` | 新加坡 |

Oregon 和 Tokyo 节点连接 Ohio 主库，不部署本地数据库。

## 首次部署

### 1. 系统准备

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv postgresql nginx certbot
```

### 2. 数据库初始化

```bash
sudo -u postgres createdb apollo
sudo -u postgres psql -d apollo -f db/schema.sql
```

### 3. 应用部署

```bash
cd /opt
git clone <repo> apollo
cd apollo/server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 DATABASE_URL 等配置
```

### 4. systemd 服务

创建 `/etc/systemd/system/apollo.service`：

```ini
[Unit]
Description=Apollo Gateway
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/apollo/server
Environment=PATH=/opt/apollo/server/venv/bin:/usr/bin
ExecStart=/opt/apollo/server/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable apollo
sudo systemctl start apollo
```

### 5. nginx 配置

`/etc/nginx/sites-available/apollo`：

```nginx
server {
    listen 80;
    server_name api.apolloinn.site;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/apollo /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

TLS 由 Cloudflare 代理处理（Full 模式），或用 certbot 自签。

## 日常运维

### 更新代码

```bash
cd /opt/apollo
git pull
sudo systemctl restart apollo
```

### 查看日志

```bash
sudo journalctl -u apollo -f
```

### 数据库备份

```bash
# 手动备份
pg_dump -U postgres apollo > backup_$(date +%Y%m%d).sql

# 备份到 Supabase（脚本）
cd /opt/apollo/server
python backup_to_supabase.py
```

### 健康检查

```bash
curl https://api.apolloinn.site/health
# 期望: {"status": "ok", "service": "apollo-gateway"}
```

## 前端部署

三个前端面板（admin / agent / user）均部署在 Vercel：

```bash
cd admin  # 或 agent / user
npm run build
# 通过 Vercel CLI 或 Git 集成自动部署
```

各面板的 `vercel.json` 已配置 SPA 路由重写。
