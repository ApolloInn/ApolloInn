-- Apollo Gateway — PostgreSQL Schema

-- 全局配置
CREATE TABLE IF NOT EXISTS admin_config (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Kiro 凭证池
CREATE TABLE IF NOT EXISTS tokens (
  id             TEXT PRIMARY KEY,
  refresh_token  TEXT DEFAULT '',
  access_token   TEXT DEFAULT '',
  expires_at     TEXT DEFAULT '',
  region         TEXT DEFAULT 'us-east-1',
  client_id_hash TEXT DEFAULT '',
  client_id      TEXT DEFAULT '',
  client_secret  TEXT DEFAULT '',
  auth_method    TEXT DEFAULT '',
  provider       TEXT DEFAULT '',
  profile_arn    TEXT DEFAULT '',
  status         TEXT DEFAULT 'active',
  added_at       TIMESTAMPTZ DEFAULT now(),
  last_used      TIMESTAMPTZ,
  use_count      INTEGER DEFAULT 0
);

-- 用户
CREATE TABLE IF NOT EXISTS users (
  id             TEXT PRIMARY KEY,
  name           TEXT NOT NULL,
  usertoken      TEXT UNIQUE NOT NULL,
  status         TEXT DEFAULT 'active',
  assigned_token_id TEXT DEFAULT '',
  cursor_email   TEXT DEFAULT '',
  created_at     TIMESTAMPTZ DEFAULT now(),
  last_used      TIMESTAMPTZ,
  request_count  INTEGER DEFAULT 0,
  token_balance  BIGINT DEFAULT 0,
  token_granted  BIGINT DEFAULT 0,
  quota_daily_tokens    INTEGER DEFAULT 0,
  quota_monthly_tokens  INTEGER DEFAULT 0,
  quota_daily_requests  INTEGER DEFAULT 0
);

-- 用户 API Keys
CREATE TABLE IF NOT EXISTS user_apikeys (
  apikey  TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_apikeys_user ON user_apikeys(user_id);

-- 用量记录（逐条）
CREATE TABLE IF NOT EXISTS usage_records (
  id               BIGSERIAL PRIMARY KEY,
  user_id          TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  model            TEXT NOT NULL,
  prompt_tokens    INTEGER DEFAULT 0,
  completion_tokens INTEGER DEFAULT 0,
  token_id         TEXT DEFAULT '',
  recorded_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_records(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_records(recorded_at);
CREATE INDEX IF NOT EXISTS idx_usage_token ON usage_records(token_id);

-- 模型映射（combo + alias 合并）
CREATE TABLE IF NOT EXISTS model_mappings (
  name       TEXT PRIMARY KEY,
  type       TEXT NOT NULL CHECK (type IN ('combo', 'alias')),
  targets    JSONB NOT NULL,
  is_builtin BOOLEAN DEFAULT false
);

-- Cursor Pro 登录凭证池
CREATE TABLE IF NOT EXISTS cursor_tokens (
  id             TEXT PRIMARY KEY,
  email          TEXT DEFAULT '',
  password       TEXT DEFAULT '',
  access_token   TEXT DEFAULT '',
  refresh_token  TEXT DEFAULT '',
  note           TEXT DEFAULT '',
  status         TEXT DEFAULT 'active',
  assigned_user  TEXT DEFAULT '',
  added_at       TIMESTAMPTZ DEFAULT now(),
  last_used      TIMESTAMPTZ,
  use_count      INTEGER DEFAULT 0
);

-- Cursor Promax 激活码池
CREATE TABLE IF NOT EXISTS promax_keys (
  id             TEXT PRIMARY KEY,
  api_key        TEXT NOT NULL,
  note           TEXT DEFAULT '',
  status         TEXT DEFAULT 'active',
  assigned_user  TEXT DEFAULT '',
  added_at       TIMESTAMPTZ DEFAULT now(),
  last_used      TIMESTAMPTZ,
  use_count      INTEGER DEFAULT 0
);

-- ── 迁移（ALTER 兼容已有表） ──
ALTER TABLE cursor_tokens ADD COLUMN IF NOT EXISTS password TEXT DEFAULT '';
ALTER TABLE usage_records ADD COLUMN IF NOT EXISTS token_id TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS assigned_token_id TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS cursor_email TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS switch_count INTEGER DEFAULT 0;

-- cursor_tokens 扩展字段
ALTER TABLE cursor_tokens ADD COLUMN IF NOT EXISTS machine_ids JSONB DEFAULT '{}';
ALTER TABLE cursor_tokens ADD COLUMN IF NOT EXISTS last_refreshed_at TIMESTAMPTZ;
ALTER TABLE cursor_tokens ADD COLUMN IF NOT EXISTS frozen_until TIMESTAMPTZ;

-- ── 二级代理商 ──
CREATE TABLE IF NOT EXISTS agents (
  id              TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  agent_key       TEXT UNIQUE NOT NULL,
  status          TEXT DEFAULT 'active',
  created_at      TIMESTAMPTZ DEFAULT now(),
  max_users       INTEGER DEFAULT 50,
  token_pool      BIGINT DEFAULT 0,
  token_used      BIGINT DEFAULT 0,
  commission_rate NUMERIC(5,2) DEFAULT 0
);

-- users 表加 agent_id 字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS agent_id TEXT DEFAULT '';

-- ── 额度流水（充值/扣减/退还记录） ──
CREATE TABLE IF NOT EXISTS token_transactions (
  id          BIGSERIAL PRIMARY KEY,
  user_id     TEXT NOT NULL,              -- 目标用户（不加外键，删用户后流水保留）
  agent_id    TEXT DEFAULT '',            -- 操作代理商（空=admin 操作）
  type        TEXT NOT NULL,              -- grant / deduct / refund
  amount      BIGINT NOT NULL,            -- 正数=充值，负数=扣减
  balance_after BIGINT DEFAULT 0,         -- 操作后用户余额
  source      TEXT DEFAULT 'admin',       -- admin / agent / system
  note        TEXT DEFAULT '',            -- 备注
  created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_txn_user ON token_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_txn_agent ON token_transactions(agent_id);
CREATE INDEX IF NOT EXISTS idx_txn_date ON token_transactions(created_at);

-- ── 账号池归属 & 领取次数 ──
ALTER TABLE cursor_tokens ADD COLUMN IF NOT EXISTS owner_type TEXT DEFAULT 'admin';
ALTER TABLE cursor_tokens ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS claim_remaining INTEGER DEFAULT 0;

-- cursor_tokens 邮箱密码
ALTER TABLE cursor_tokens ADD COLUMN IF NOT EXISTS email_password TEXT DEFAULT '';

-- ── Cursor 账号领取/回收日志 ──
CREATE TABLE IF NOT EXISTS cursor_claim_logs (
  id          BIGSERIAL PRIMARY KEY,
  user_id     TEXT NOT NULL,
  user_name   TEXT DEFAULT '',
  email       TEXT DEFAULT '',
  action      TEXT NOT NULL,          -- claim / revoke
  source      TEXT DEFAULT 'admin',   -- admin / agent
  agent_id    TEXT DEFAULT '',
  created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_claim_logs_user ON cursor_claim_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_claim_logs_email ON cursor_claim_logs(email);
CREATE INDEX IF NOT EXISTS idx_claim_logs_date ON cursor_claim_logs(created_at);
