"""内嵌 UI 页面 — Apollo Agent 完整用户面板。

本地 agent 同时充当：
1. 静态页面服务器（提供此 HTML）
2. 远程 API 代理（/api/* → https://apolloinn.site/*）
3. 本地 Cursor 操作（/status, /switch, /license-activate）
"""

AGENT_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Apollo Agent</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap" rel="stylesheet">
<style>
:root{
  --c-primary:#e8501e;--c-primary-dark:#c43d12;--c-primary-light:#ff7a4d;
  --c-primary-bg:rgba(232,80,30,.06);--c-primary-bg-strong:rgba(232,80,30,.12);
  --c-text:#1a1a1a;--c-sec:#777;--c-surface:#fff;--c-accent:#f3f4f6;
  --bg-app:#f0f0f2;
  --glass-capsule:rgba(255,255,255,.82);--glass-bg:rgba(255,255,255,.35);
  --shadow-card:0 1px 1px rgba(0,0,0,.03),0 2px 4px rgba(0,0,0,.03),0 8px 16px rgba(0,0,0,.04),inset 0 1px 0 rgba(255,255,255,.8);
  --shadow-lg:0 4px 8px rgba(0,0,0,.04),0 16px 40px rgba(0,0,0,.06);
  --shadow-md:0 2px 4px rgba(0,0,0,.04),0 8px 20px rgba(0,0,0,.04);
  --border-light:1px solid rgba(255,255,255,.7);--border-subtle:1px solid rgba(0,0,0,.06);
  --c-ok:#22c55e;--c-warn:#f59e0b;--c-err:#ef4444;
  --header-h:62px;--r-sm:8px;--r-md:12px;--r-lg:20px;--r-xl:24px;
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;background:radial-gradient(ellipse at 10% 10%,rgba(255,248,245,.9) 0%,transparent 50%),radial-gradient(ellipse at 90% 80%,rgba(240,232,228,.6) 0%,transparent 50%),radial-gradient(ellipse at 50% 50%,#f8f6f5 0%,#f0eeec 100%);color:var(--c-text);height:100vh;overflow:hidden;-webkit-font-smoothing:antialiased}
#root{display:flex;flex-direction:column;height:100vh;overflow:hidden}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:rgba(0,0,0,.08);border-radius:2px}

/* Header */
.header{height:var(--header-h);display:flex;align-items:center;padding:0 28px;background:linear-gradient(180deg,rgba(255,255,255,.92) 0%,rgba(255,255,255,.8) 100%);backdrop-filter:blur(30px);border-bottom:1px solid rgba(255,255,255,.6);box-shadow:0 1px 3px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.03);z-index:100;flex-shrink:0}
.header-logo{display:flex;align-items:center;gap:12px}
.logo-mark{width:34px;height:34px;background:linear-gradient(135deg,var(--c-primary) 0%,var(--c-primary-dark) 100%);border-radius:10px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:16px;box-shadow:0 2px 6px rgba(232,80,30,.3)}
.logo-text{font-size:13px;font-weight:900;letter-spacing:.22em;text-transform:uppercase}.logo-text span{font-weight:400;color:var(--c-sec)}
.header-right{margin-left:auto;display:flex;align-items:center;gap:12px}
.user-pill{padding:5px 14px;background:var(--c-primary-bg);border-radius:20px;font-size:10px;font-weight:700;color:var(--c-primary);display:flex;align-items:center;gap:6px}
.user-pill .material-symbols-rounded{font-size:14px}
.btn-logout{padding:5px 12px;border:1px solid rgba(0,0,0,.08);background:transparent;border-radius:var(--r-sm);font-family:inherit;font-size:10px;font-weight:600;color:var(--c-sec);cursor:pointer;transition:.15s}
.btn-logout:hover{background:rgba(0,0,0,.03)}

/* Main */
.main-scroll{flex:1;overflow-y:auto;padding:24px}
.main-inner{max-width:720px;margin:0 auto}

/* Stats */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:24px}
.stat-card{padding:18px 20px;background:var(--glass-capsule);border-radius:var(--r-lg);box-shadow:var(--shadow-card);border:var(--border-light)}
.stat-card.highlight{background:linear-gradient(135deg,var(--c-primary),var(--c-primary-light));color:#fff;border:none;box-shadow:0 4px 16px rgba(232,80,30,.25)}
.stat-card.highlight .stat-label{color:rgba(255,255,255,.7)}.stat-card.highlight .stat-value{color:#fff}.stat-card.highlight .stat-sub{color:rgba(255,255,255,.7)}
.stat-label{font-size:9px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--c-sec);margin-bottom:4px}
.stat-value{font-size:24px;font-weight:800}.stat-sub{font-size:10px;color:var(--c-sec);margin-top:2px}

/* Balance */
.balance-wrap{margin-top:8px}.balance-meta{display:flex;justify-content:space-between;font-size:10px;color:var(--c-sec);margin-bottom:4px}
.balance-bar{height:12px;background:rgba(0,0,0,.04);border-radius:6px;overflow:hidden}
.balance-fill{height:100%;border-radius:6px;transition:width .5s ease}
.balance-fill.ok{background:linear-gradient(90deg,var(--c-primary),var(--c-primary-light))}
.balance-fill.low{background:linear-gradient(90deg,#f59e0b,#fbbf24)}.balance-fill.crit{background:var(--c-err)}

/* Section / Card / Table */
.section-title{font-size:10px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--c-sec);margin:24px 0 12px;display:flex;align-items:center;gap:8px}
.section-title .material-symbols-rounded{font-size:16px;color:var(--c-primary)}
.card{background:var(--glass-capsule);border-radius:var(--r-lg);box-shadow:var(--shadow-card);border:var(--border-light);margin-bottom:16px;overflow:hidden}
.card-header{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:var(--border-subtle)}
.card-title{font-size:11px;font-weight:700;letter-spacing:.15em;text-transform:uppercase}
.card-body{padding:16px 20px}
table{width:100%;border-collapse:collapse}
th{font-size:9px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--c-sec);text-align:left;padding:10px 14px;border-bottom:var(--border-subtle)}
td{font-size:12px;padding:12px 14px;border-bottom:1px solid rgba(0,0,0,.03)}
tr:hover td{background:var(--c-primary-bg)}
.mono{font-family:'SF Mono','Fira Code',monospace;font-size:11px;color:var(--c-sec)}

/* Buttons */
.btn{padding:7px 16px;border:none;border-radius:var(--r-sm);font-family:inherit;font-size:11px;font-weight:600;cursor:pointer;transition:.15s;display:inline-flex;align-items:center;gap:6px}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn-primary{background:var(--c-primary);color:#fff}.btn-primary:hover:not(:disabled){background:var(--c-primary-dark);transform:translateY(-1px);box-shadow:0 2px 8px rgba(232,80,30,.3)}
.btn-danger{background:transparent;border:1px solid rgba(239,68,68,.2);color:var(--c-err);padding:5px 10px;font-size:10px}.btn-danger:hover{background:rgba(239,68,68,.05)}
.btn-ghost{background:transparent;border:1px solid rgba(0,0,0,.08);color:var(--c-sec);padding:5px 10px;font-size:10px}.btn-ghost:hover{background:rgba(0,0,0,.03)}
.btn-sm{padding:5px 10px;font-size:10px}
.btn .material-symbols-rounded{font-size:14px}

/* Copy / Endpoint */
.copy-btn{background:transparent;border:none;cursor:pointer;color:var(--c-sec);padding:4px;border-radius:6px;transition:.15s;display:inline-flex;align-items:center}
.copy-btn:hover{color:var(--c-primary);background:var(--c-primary-bg)}
.copy-btn .material-symbols-rounded{font-size:14px}
.endpoint-box{background:rgba(0,0,0,.03);border-radius:var(--r-sm);padding:12px 16px;font-family:'SF Mono','Fira Code',monospace;font-size:11px;color:var(--c-sec);margin-bottom:8px;display:flex;align-items:center;justify-content:space-between}
.endpoint-hint{margin-top:14px;font-size:11px;color:var(--c-sec);line-height:1.7}
.endpoint-hint code{background:rgba(0,0,0,.04);padding:1px 5px;border-radius:3px;font-size:10px}

/* Cursor */
.cursor-progress{display:flex;align-items:center;gap:12px;padding:8px 0;font-size:12px;color:var(--c-sec)}
.cursor-progress-spinner{width:18px;height:18px;border:2px solid rgba(0,0,0,.08);border-top-color:var(--c-primary);border-radius:50%;animation:spin .8s linear infinite;flex-shrink:0}
@keyframes spin{to{transform:rotate(360deg)}}
.cursor-done{display:flex;align-items:flex-start;gap:10px;padding:4px 0}

/* Bar Chart */
.bar-chart{display:flex;flex-direction:column;gap:10px}
.bar-row{display:flex;align-items:center;gap:12px}
.bar-label{font-size:11px;font-weight:600;min-width:130px}
.bar-track{flex:1;height:10px;background:rgba(0,0,0,.04);border-radius:5px;overflow:hidden}
.bar-fill{height:100%;background:linear-gradient(90deg,var(--c-primary),var(--c-primary-light));border-radius:5px;transition:width .5s}
.bar-value{font-size:11px;font-weight:600;color:var(--c-sec);min-width:70px;text-align:right}

/* Toast */
.toast-wrap{position:fixed;top:76px;right:24px;z-index:300;display:flex;flex-direction:column;gap:8px}
.toast{padding:12px 18px;background:var(--c-surface);border-radius:var(--r-md);box-shadow:var(--shadow-md);font-size:12px;font-weight:500;display:flex;align-items:center;gap:8px;animation:toastIn .3s;border-left:3px solid var(--c-primary)}
.toast-ok{border-left-color:var(--c-ok)}.toast-err{border-left-color:var(--c-err)}
@keyframes toastIn{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:none}}

/* Login */
.login-wrap{flex:1;display:flex;align-items:center;justify-content:center}
.login-box{background:var(--glass-capsule);border-radius:var(--r-xl);box-shadow:var(--shadow-lg);padding:48px 40px;width:380px;text-align:center;border:var(--border-light)}
.login-logo{width:60px;height:60px;background:linear-gradient(135deg,var(--c-primary),var(--c-primary-light));border-radius:var(--r-lg);display:flex;align-items:center;justify-content:center;margin:0 auto 20px;box-shadow:0 4px 16px rgba(232,80,30,.3)}
.login-logo span{color:#fff;font-weight:900;font-size:26px}
.login-title{font-size:20px;font-weight:800;margin-bottom:4px}
.login-sub{font-size:11px;color:var(--c-sec);margin-bottom:28px}
.login-input{width:100%;padding:11px 16px;border:var(--border-subtle);background:var(--glass-bg);border-radius:var(--r-sm);font-family:inherit;font-size:13px;outline:none;margin-bottom:14px;transition:border-color .2s}
.login-input:focus{border-color:var(--c-primary);box-shadow:0 0 0 3px var(--c-primary-bg)}
.login-btn{width:100%;padding:11px;border:none;background:var(--c-primary);color:#fff;border-radius:var(--r-sm);font-family:inherit;font-size:13px;font-weight:700;cursor:pointer;transition:.15s}
.login-btn:hover{background:var(--c-primary-dark);transform:translateY(-1px);box-shadow:0 4px 12px rgba(232,80,30,.3)}

/* Modal */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.25);backdrop-filter:blur(6px);z-index:250;display:flex;align-items:center;justify-content:center;animation:modalFadeIn .2s}
.modal-box{background:var(--c-surface);border-radius:var(--r-xl);box-shadow:var(--shadow-lg);padding:28px 32px;min-width:360px;max-width:460px;width:90%;animation:modalSlideIn .25s}
.modal-title{font-size:15px;font-weight:800;margin-bottom:8px}
.modal-message{font-size:12px;color:var(--c-sec);line-height:1.6;margin-bottom:16px;white-space:pre-line}
.modal-actions{display:flex;gap:8px;justify-content:flex-end}
@keyframes modalFadeIn{from{opacity:0}to{opacity:1}}
@keyframes modalSlideIn{from{opacity:0;transform:translateY(-12px) scale(.97)}to{opacity:1;transform:none}}

.empty{text-align:center;padding:24px;color:var(--c-sec);font-size:12px}
.hidden{display:none!important}
</style>
</head>
<body>
<div id="root">
  <!-- Login -->
  <div id="loginView" class="login-wrap">
    <div class="login-box">
      <div class="login-logo"><span>A</span></div>
      <div class="login-title">Apollo Gateway</div>
      <div class="login-sub">用户面板 · 桌面版</div>
      <input class="login-input" id="tokenInput" type="password" placeholder="输入 apollo-xxx Token..." autofocus>
      <button class="login-btn" id="loginBtn" onclick="doLogin()">登 录</button>
    </div>
  </div>

  <!-- Dashboard -->
  <div id="dashView" class="hidden" style="display:flex;flex-direction:column;height:100vh">
    <header class="header">
      <div class="header-logo">
        <div class="logo-mark">A</div>
        <div class="logo-text">APOLLO <span>AGENT</span></div>
      </div>
      <div class="header-right">
        <div class="user-pill"><span class="material-symbols-rounded">person</span><span id="userName"></span></div>
        <button class="btn-logout" onclick="doLogout()">退出</button>
      </div>
    </header>
    <div class="main-scroll">
      <div class="main-inner">
        <!-- Cash/Token Toggle -->
        <div style="display:flex;justify-content:flex-end;margin-bottom:8px">
          <div style="display:inline-flex;background:rgba(0,0,0,.04);border-radius:10px;padding:3px;border:1px solid rgba(0,0,0,.03)">
            <button id="togToken" onclick="toggleCash(false)" style="display:flex;align-items:center;gap:5px;padding:5px 14px;border:none;border-radius:8px;cursor:pointer;font-size:11px;font-family:inherit;font-weight:700;color:var(--c-primary);background:rgba(255,255,255,.95);box-shadow:0 1px 3px rgba(0,0,0,.06);transition:all .2s"><span class="material-symbols-rounded" style="font-size:14px">token</span>计费Token</button>
            <button id="togCash" onclick="toggleCash(true)" style="display:flex;align-items:center;gap:5px;padding:5px 14px;border:none;border-radius:8px;cursor:pointer;font-size:11px;font-family:inherit;font-weight:400;color:var(--c-sec);background:transparent;box-shadow:none;transition:all .2s"><span class="material-symbols-rounded" style="font-size:14px">attach_money</span>现金额度</button>
          </div>
        </div>

        <!-- Stats -->
        <div class="stats-grid">
          <div class="stat-card highlight"><div class="stat-label">剩余额度</div><div class="stat-value" id="sBalance">—</div><div class="stat-sub" id="sGranted"></div></div>
          <div class="stat-card"><div class="stat-label">已消耗</div><div class="stat-value" id="sUsed">—</div></div>
          <div class="stat-card"><div class="stat-label">总请求</div><div class="stat-value" id="sReqs">—</div></div>
        </div>
        <div class="card" id="barCard" style="margin-bottom:24px"><div class="card-body"><div class="stat-label">额度使用进度</div><div class="balance-wrap"><div class="balance-meta"><span id="barUsed"></span><span id="barLeft"></span></div><div class="balance-bar"><div class="balance-fill" id="barFill"></div></div></div></div></div>

        <!-- 计费标准 -->
        <div class="card" style="margin-bottom:24px"><div class="card-body" style="font-size:11px;color:var(--c-sec);line-height:1.8">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;color:var(--c-text);font-size:12px;font-weight:600"><span class="material-symbols-rounded" style="font-size:16px">calculate</span>计费标准（每 1M tokens）</div>
          <table style="width:100%;font-size:11px"><thead><tr><th style="text-align:left">模型级别</th><th>适用模型</th><th>输入 (Input)</th><th>输出 (Output)</th></tr></thead><tbody>
            <tr><td>旗舰级 (Opus)</td><td>Opus 4.6 / 4.5</td><td style="font-family:monospace">$5.00</td><td style="font-family:monospace">$25.00</td></tr>
            <tr><td>均衡型 (Sonnet)</td><td>Sonnet 4.6 / 4.5 / 4</td><td style="font-family:monospace">$3.00</td><td style="font-family:monospace">$15.00</td></tr>
            <tr><td>轻量级 (Haiku)</td><td>Haiku 4.5</td><td style="font-family:monospace">$1.00</td><td style="font-family:monospace">$5.00</td></tr>
          </tbody></table>
          <div style="margin-top:8px;padding:6px 10px;background:rgba(0,0,0,.03);border-radius:6px;font-size:11px">计费公式：<code style="background:rgba(0,0,0,.06);padding:1px 4px;border-radius:3px">计费Token = 输入Token × 输入权重 + 输出Token × 输出权重</code><span style="margin-left:8px;color:var(--c-sec)">（权重 = 模型价格 ÷ $25）</span></div>
        </div></div>

        <!-- Cursor Account -->
        <div class="section-title"><span class="material-symbols-rounded">badge</span>Cursor 会员</div>
        <div class="card">
          <div class="card-body" id="memberBody">
            <div style="display:flex;align-items:center;gap:12px">
              <div style="width:40px;height:40px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:12px;display:flex;align-items:center;justify-content:center;flex-shrink:0"><span class="material-symbols-rounded" style="color:#fff;font-size:20px">diamond</span></div>
              <div style="flex:1">
                <div style="font-size:13px;font-weight:700" id="memberEmail">加载中...</div>
                <div style="display:flex;align-items:center;gap:8px;margin-top:4px">
                  <span id="memberBadge" style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff">PRO</span>
                  <span id="memberMode" style="font-size:10px;color:var(--c-sec)"></span>
                </div>
              </div>
              <div id="memberStatus" style="text-align:right;font-size:10px;color:var(--c-sec)"></div>
            </div>
          </div>
        </div>

        <!-- Cursor -->
        <div class="section-title"><span class="material-symbols-rounded">desktop_mac</span>Cursor 配置</div>
        <div class="card">
          <div class="card-header">
            <span class="card-title">Cursor Pro 智能换号</span>
            <div style="display:flex;align-items:center;gap:8px">
              <span id="agentBadge" style="font-size:10px;display:flex;align-items:center;gap:4px"></span>
              <button class="btn btn-primary btn-sm hidden" id="byokBtn" onclick="doByokSetup()"><span class="material-symbols-rounded">bolt</span>智能换号</button>
            </div>
          </div>
          <div class="card-body" id="cursorBody">
            <div class="cursor-progress"><div class="cursor-progress-spinner"></div><span>检测 Agent 状态...</span></div>
          </div>
        </div>

        <!-- API Keys -->
        <div class="section-title"><span class="material-symbols-rounded">key</span>API Keys</div>
        <div class="card">
          <div class="card-header"><span class="card-title">我的 API Keys</span><button class="btn btn-primary btn-sm" onclick="createKey()"><span class="material-symbols-rounded">add</span>创建</button></div>
          <div class="card-body" id="keysBody"><div class="empty">加载中...</div></div>
        </div>

        <!-- Endpoint -->
        <div class="section-title"><span class="material-symbols-rounded">link</span>接入信息</div>
        <div class="card"><div class="card-body">
          <div class="stat-label">Base URL</div>
          <div class="endpoint-box"><span>https://api.apolloinn.site/v1</span><button class="copy-btn" onclick="copy('https://api.apolloinn.site/v1')"><span class="material-symbols-rounded">content_copy</span></button></div>
          <div class="endpoint-hint">在 OpenAI 兼容客户端（Cursor、ChatBox 等）中填入上方地址作为 Base URL，API Key 填你的 <code>ap-xxx</code> key 即可。</div>
        </div></div>

        <!-- Proxy Guide -->
        <div class="section-title"><span class="material-symbols-rounded">settings_suggest</span>配置反向代理（重要）</div>
        <div class="card"><div class="card-body" style="font-size:12px;color:var(--c-sec);line-height:1.9">
          <div style="margin-bottom:8px;color:var(--c-text);font-size:13px">切换账号后，请按以下步骤配置反向代理以长期稳定使用：</div>
          <div style="padding-left:4px">
            进入 Cursor 工作区，点击右上角齿轮图标，进入 Cursor Settings<br>
            选择 Models 选项卡，展开底部"自定义 API Keys"<br>
            打开 OpenAI API Key 和 Override OpenAI Base URL 两个开关<br>
            填入你的 API Key（<code>ap-xxx</code>）和接口地址：
          </div>
          <div style="position:relative;margin:8px 0 8px 4px"><code style="background:rgba(0,0,0,.06);padding:6px 30px 6px 8px;border-radius:4px;display:block;font-size:11px">https://api.apolloinn.site/v1</code><button class="copy-btn" style="position:absolute;top:4px;right:4px" onclick="copy('https://api.apolloinn.site/v1')"><span class="material-symbols-rounded" style="font-size:14px">content_copy</span></button></div>
          <div style="padding-left:4px">在 Models 列表中添加自定义模型，如 <code>Kiro-Opus-4-6</code></div>
          <div style="margin-top:10px;padding:8px 12px;background:rgba(255,180,0,.08);border-radius:8px;font-size:11px;line-height:1.6">注意：请使用反向代理模型（Kiro- 开头），不要直接使用 Cursor 自带账号的模型，以免账号透支风控。</div>
        </div></div>

        <!-- Model List -->
        <div class="section-title"><span class="material-symbols-rounded">shuffle</span>可用模型</div>
        <div class="card"><div class="card-header"><span class="card-title">Cursor 反向代理模型</span></div><div class="card-body" id="cursorModelsBody"></div></div>
        <div class="card" style="margin-top:12px"><div class="card-header"><span class="card-title">Cline / ChatBox 等客户端</span></div><div class="card-body" id="clineModelsBody"></div></div>

        <!-- Usage by date -->
        <div class="section-title"><span class="material-symbols-rounded">monitoring</span>用量统计</div>
        <div class="card"><div style="overflow-x:auto" id="datesBody"><div class="empty">加载中...</div></div></div>

        <!-- Usage by model -->
        <div class="section-title"><span class="material-symbols-rounded">model_training</span>按模型用量</div>
        <div class="card"><div class="card-body" id="modelsBody"><div class="empty">加载中...</div></div></div>

        <!-- Clean Cursor -->
        <div class="section-title" style="margin-top:36px"><span class="material-symbols-rounded">delete_forever</span>完全清理 Cursor</div>
        <div class="card" style="border:1px solid rgba(239,68,68,.15)">
          <div class="card-header">
            <span class="card-title" style="color:var(--c-err)">卸载并清理 Cursor（Windows）</span>
          </div>
          <div class="card-body" id="cleanBody">
            <div style="font-size:12px;color:var(--c-sec);line-height:1.8">
              <div style="margin-bottom:8px">彻底删除 Cursor 客户端及所有配置文件，包括：</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 16px;padding-left:4px;font-size:11px">
                <span>• 安装目录和程序文件</span>
                <span>• 用户数据和认证信息</span>
                <span>• 缓存和临时文件</span>
                <span>• 项目索引和扩展元数据</span>
                <span>• 更新缓存</span>
                <span>• 注册表残留</span>
              </div>
              <div style="margin-top:10px;padding:8px 12px;background:rgba(239,68,68,.06);border-radius:8px;font-size:11px;color:var(--c-err)">
                ⚠ 此操作不可逆，执行后需要重新下载安装 Cursor。仅支持 Windows 系统。
              </div>
              <div id="cleanResult" style="margin-top:10px"></div>
              <div style="margin-top:14px;display:flex;flex-direction:column;align-items:center;gap:10px">
                <button class="btn btn-danger" id="cleanBtn" onclick="doCleanCursor()" style="padding:10px 32px;font-size:12px"><span class="material-symbols-rounded">delete_forever</span>一键清理 Cursor</button>
                <a href="https://www.cursor.com/" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:6px;padding:8px 16px;background:var(--c-accent);border:1px solid rgba(0,0,0,.08);border-radius:var(--r-sm);font-size:12px;font-weight:600;color:var(--c-text);text-decoration:none;transition:.15s" onmouseover="this.style.background='var(--c-primary-bg)'" onmouseout="this.style.background='var(--c-accent)'"><span class="material-symbols-rounded" style="font-size:16px">open_in_new</span>Cursor: The best way to code with AI</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Toast container -->
<div class="toast-wrap" id="toastWrap"></div>
<!-- Modal -->
<div id="modalOverlay" class="modal-overlay hidden"></div>

<script>
const API_BASE = "https://api.apolloinn.site";
const AGENT = "http://127.0.0.1:19080";
let token = localStorage.getItem("apollo_user_token") || "";
let currentUser = "";
let agentOnline = false;
let licenseActivated = false;
let showCash = false;

/* ── Helpers ── */
function $(s){ return document.querySelector(s); }
function fmtNum(n){ if(n>=1e6) return (n/1e6).toFixed(1)+"M"; if(n>=1e3) return (n/1e3).toFixed(1)+"K"; return n.toString(); }
function fmtCash(n){ const c=n*25/1e6; if(c>=0.01) return "$"+c.toFixed(2); if(c>=0.001) return "$"+c.toFixed(3); return "$"+c.toFixed(4); }
const MODEL_PRICE = {opus:[5,25], sonnet:[3,15], haiku:[1,5]};
function getModelTier(m){ const l=m.toLowerCase(); if(l.includes("opus")) return "opus"; if(l.includes("sonnet")) return "sonnet"; if(l.includes("haiku")) return "haiku"; return "opus"; }
function rawCash(model,p,c){ const [ip,op]=MODEL_PRICE[getModelTier(model)]||[5,25]; const v=(p*ip+c*op)/1e6; if(v>=0.01) return "$"+v.toFixed(2); if(v>=0.001) return "$"+v.toFixed(3); return "$"+v.toFixed(4); }
function rawCashApprox(p,c){ const v=(p*5+c*25)/1e6; if(v>=0.01) return "$"+v.toFixed(2); if(v>=0.001) return "$"+v.toFixed(3); return "$"+v.toFixed(4); }
function copy(t){ navigator.clipboard.writeText(t).then(()=>toast("已复制","ok")); }

function toast(msg, type){
  const w = $("#toastWrap");
  const d = document.createElement("div");
  d.className = "toast" + (type==="ok"?" toast-ok":type==="err"?" toast-err":"");
  d.textContent = msg;
  w.appendChild(d);
  setTimeout(()=>d.remove(), 3000);
}

function showModal(title, message){
  return new Promise(resolve=>{
    const o = $("#modalOverlay");
    o.className = "modal-overlay";
    o.innerHTML = `<div class="modal-box"><div class="modal-title">${title}</div><div class="modal-message">${message}</div><div class="modal-actions"><button class="btn btn-ghost btn-sm" id="modalCancel">取消</button><button class="btn btn-primary btn-sm" id="modalOk">确认</button></div></div>`;
    $("#modalCancel").onclick = ()=>{ o.className="modal-overlay hidden"; resolve(false); };
    $("#modalOk").onclick = ()=>{ o.className="modal-overlay hidden"; resolve(true); };
  });
}

function showAlert(title, message){
  return new Promise(resolve=>{
    const o = $("#modalOverlay");
    o.className = "modal-overlay";
    o.innerHTML = `<div class="modal-box"><div class="modal-title">${title}</div><div class="modal-message">${message}</div><div class="modal-actions"><button class="btn btn-primary btn-sm" id="modalOk">确定</button></div></div>`;
    $("#modalOk").onclick = ()=>{ o.className="modal-overlay hidden"; resolve(); };
  });
}

async function api(method, path, body){
  const opts = { method, headers: { "Authorization": "Bearer " + token, "Content-Type": "application/json" } };
  if(body) opts.body = JSON.stringify(body);
  const r = await fetch(API_BASE + path, opts);
  if(!r.ok){ const e = await r.json().catch(()=>({detail:r.statusText})); throw new Error(e.detail||r.statusText); }
  return r.json();
}

async function agentApi(method, path, body){
  const opts = { method, headers: { "Content-Type": "application/json" }, mode: "cors" };
  if(body) opts.body = JSON.stringify(body);
  return fetch(AGENT + path, opts).then(r=>r.json());
}

/* ── Login ── */
async function doLogin(){
  const input = $("#tokenInput").value.trim();
  if(!input) return;
  token = input;
  try{
    const me = await api("GET", "/user/me");
    localStorage.setItem("apollo_user_token", token);
    agentApi("POST","/save-token",{usertoken:token}).catch(()=>{});
    currentUser = me.name;
    showDashboard();
  } catch(e){
    token = "";
    toast("Token 无效","err");
  }
}
$("#tokenInput").addEventListener("keydown", e=>{ if(e.key==="Enter") doLogin(); });

function doLogout(){
  localStorage.removeItem("apollo_user_token");
  agentApi("POST","/save-token",{usertoken:""}).catch(()=>{});
  token = ""; currentUser = "";
  $("#dashView").className = "hidden";
  $("#loginView").className = "login-wrap";
  $("#tokenInput").value = "";
}

/* ── Dashboard ── */
function showDashboard(){
  $("#loginView").className = "hidden";
  $("#dashView").className = "";
  $("#dashView").style.display = "flex";
  $("#userName").textContent = currentUser;
  loadData();
  checkAgent();
  setInterval(()=>{ loadData(); checkAgent(); }, 10000);
}

function toggleCash(v){
  showCash=v;
  const tBtn=$("#togToken"), cBtn=$("#togCash");
  tBtn.style.fontWeight=v?"400":"700"; tBtn.style.color=v?"var(--c-sec)":"var(--c-primary)"; tBtn.style.background=v?"transparent":"rgba(255,255,255,.95)"; tBtn.style.boxShadow=v?"none":"0 1px 3px rgba(0,0,0,.06)";
  cBtn.style.fontWeight=v?"700":"400"; cBtn.style.color=v?"var(--c-primary)":"var(--c-sec)"; cBtn.style.background=v?"rgba(255,255,255,.95)":"transparent"; cBtn.style.boxShadow=v?"0 1px 3px rgba(0,0,0,.06)":"none";
  if(lastUsage) { renderStats(lastUsage); renderUsage(lastUsage.usage||{}); }
}

let lastUsage = null;

async function loadData(){
  try{
    const [me, usage, keys, combos] = await Promise.all([
      api("GET","/user/me"), api("GET","/user/usage"), api("GET","/user/apikeys"), api("GET","/user/combos")
    ]);
    lastUsage = usage;
    renderStats(usage);
    renderKeys(keys.apikeys||[]);
    renderModels(combos.combos||{});
    renderUsage(usage.usage||{});
  } catch(e){ toast("加载数据失败: "+e.message,"err"); }
}

function renderStats(u){
  const granted = u.token_granted||0, balance = u.token_balance||0;
  const used = u.usage?.total_tokens||0;
  const fmt = showCash ? fmtCash : fmtNum;
  $("#sBalance").textContent = fmt(balance);
  $("#sGranted").textContent = "已分配 " + fmt(granted);
  $("#sUsed").textContent = fmt(used);
  $("#sReqs").textContent = u.requestCount||0;
  if(granted>0){
    $("#barCard").style.display = "";
    const pct = granted>0?(balance/granted)*100:0;
    const cls = pct>30?"ok":pct>10?"low":"crit";
    $("#barUsed").textContent = fmt(used)+" 已用";
    $("#barLeft").textContent = fmt(balance)+" 剩余";
    const fill = $("#barFill");
    fill.className = "balance-fill "+cls;
    fill.style.width = Math.min(100,100-pct).toFixed(1)+"%";
  } else { $("#barCard").style.display = "none"; }
}

function renderKeys(keys){
  const body = $("#keysBody");
  if(!keys.length){ body.innerHTML = '<div class="empty">暂无 API Key，点击上方"创建"按钮生成</div>'; return; }
  let html = '<table><thead><tr><th>API Key</th><th>操作</th></tr></thead><tbody>';
  keys.forEach(k=>{
    html += `<tr><td><span style="display:inline-flex;align-items:center;gap:8px"><span class="mono">${k}</span><button class="copy-btn" onclick="copy('${k}')"><span class="material-symbols-rounded">content_copy</span></button></span></td><td><button class="btn btn-danger btn-sm" onclick="revokeKey('${k}')"><span class="material-symbols-rounded">delete</span></button></td></tr>`;
  });
  html += '</tbody></table>';
  body.innerHTML = html;
}

function renderModels(combos){
  const capitalize = s => s.split("-").map(w=>w.charAt(0).toUpperCase()+w.slice(1)).join("-");
  const allSet = new Set();
  Object.values(combos).forEach(targets=>{ if(Array.isArray(targets)) targets.forEach(t=>{ if(t && t!=="auto-kiro") allSet.add(t); }); });
  Object.keys(combos).forEach(n=>allSet.add(n));
  const rank = m=>{ const l=m.toLowerCase(); if(l.includes("opus")&&(l.includes("4.6")||l.includes("4-6"))) return 10; if(l.includes("opus")&&(l.includes("4.5")||l.includes("4-5"))) return 20; if(l.includes("sonnet")&&(l.includes("4.6")||l.includes("4-6"))) return 30; if(l.includes("sonnet")&&(l.includes("4.5")||l.includes("4-5"))) return 40; if(l.includes("sonnet")&&/4(?!\.)/.test(l)&&!l.includes("4.5")&&!l.includes("4.6")&&!l.includes("4-5")&&!l.includes("4-6")) return 50; if(l.includes("haiku")) return 60; if(l.includes("auto")) return 70; return 80; };
  const allModels = Array.from(allSet).sort((a,b)=>rank(a)-rank(b)||a.localeCompare(b)).map(m=>({raw:m,display:capitalize(m)}));

  const cursorModels = allModels.filter(m=>m.raw.toLowerCase().startsWith("kiro-"));
  const clineModels = allModels.filter(m=>!m.raw.toLowerCase().startsWith("kiro-"));

  function renderList(containerId, models){
    const body = $(containerId);
    if(!models.length){ body.innerHTML = '<div class="empty">暂无</div>'; return; }
    let html = '<div style="display:flex;flex-wrap:wrap;gap:6px">';
    models.forEach(m=>{
      html += `<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(0,0,0,.04);border-radius:6px;padding:4px 10px;font-size:12px"><span class="mono">${m.display}</span><button class="copy-btn" onclick="copy('${m.display}')"><span class="material-symbols-rounded" style="font-size:13px">content_copy</span></button></span>`;
    });
    html += '</div>';
    body.innerHTML = html;
  }
  renderList("#cursorModelsBody", cursorModels);
  renderList("#clineModelsBody", clineModels);

  const countEl = $("#modelCount");
  if(countEl) countEl.textContent = allModels.length + " 个";
}

function renderUsage(usage){
  // By date
  const dates = Object.entries(usage.by_date||{}).sort((a,b)=>b[0].localeCompare(a[0]));
  const dBody = $("#datesBody");
  if(!dates.length){ dBody.innerHTML = '<div class="empty">暂无使用记录</div>'; }
  else {
    let html = '<table><thead><tr><th>日期</th><th>请求数</th><th>Prompt</th><th>Completion</th><th>'+(showCash?"费用":"总计")+'</th></tr></thead><tbody>';
    dates.forEach(([d,v])=>{
      const total = showCash ? rawCashApprox(v.prompt,v.completion) : fmtNum(v.prompt+v.completion);
      html += `<tr><td>${d}</td><td>${v.requests}</td><td>${fmtNum(v.prompt)}</td><td>${fmtNum(v.completion)}</td><td style="font-weight:700">${total}</td></tr>`;
    });
    html += '</tbody></table>';
    dBody.innerHTML = html;
  }
  // By model
  const models = Object.entries(usage.by_model||{});
  const mBody = $("#modelsBody");
  if(!models.length){ mBody.innerHTML = '<div class="empty">暂无数据</div>'; return; }
  const maxM = Math.max(...models.map(([,v])=>v.prompt+v.completion),1);
  let mhtml = '<div class="bar-chart">';
  models.forEach(([m,v])=>{
    const total = v.prompt+v.completion;
    const pct = (total/maxM*100).toFixed(1);
    const val = showCash ? rawCash(m,v.prompt,v.completion) : fmtNum(total);
    mhtml += `<div class="bar-row"><span class="bar-label">${m}</span><div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div><span class="bar-value">${val}</span></div>`;
  });
  mhtml += '</div>';
  mBody.innerHTML = mhtml;
}

async function createKey(){
  try{
    const r = await api("POST","/user/apikeys");
    toast("API Key 创建成功: "+r.apikey,"ok");
    loadData();
  } catch(e){ toast("创建失败: "+e.message,"err"); }
}

async function revokeKey(key){
  const ok = await showModal("撤销 API Key","确定撤销此 API Key？撤销后无法恢复。");
  if(!ok) return;
  try{
    await api("DELETE","/user/apikeys",{apikey:key});
    toast("已撤销","ok"); loadData();
  } catch(e){ toast("撤销失败: "+e.message,"err"); }
}

/* ── Cursor / Agent ── */
async function checkAgent(){
  const badge = $("#agentBadge");
  const btn = $("#byokBtn");
  const body = $("#cursorBody");
  try{
    const d = await agentApi("GET","/status");
    agentOnline = d.ok===true;
    licenseActivated = !!d.license_activated;

    badge.innerHTML = `<span style="width:6px;height:6px;border-radius:50%;background:var(--c-ok);display:inline-block"></span><span style="color:var(--c-ok)">Agent 在线</span>`;

    // 更新会员卡本地状态
    const localEmail = d.current_email || "";
    const localMembership = d.membership || "";
    if(localEmail){
      $("#memberEmail").textContent = localEmail;
      $("#memberStatus").innerHTML = '<span style="color:var(--c-ok)">已连接</span>';
    }
    $("#memberMode").textContent = "";

    // 不管是否已激活 promax，都尝试拉激活码（兼容旧流程）
    try{
      const ar = await api("GET","/user/cursor-activation");
      if(ar.activation_code && ar.activation_code !== d.activation_code){
        const actRes = await agentApi("POST","/license-activate",{code:ar.activation_code});
        if(actRes.ok){ licenseActivated=true; }
      } else if(ar.activation_code && !licenseActivated){
        const actRes = await agentApi("POST","/license-activate",{code:ar.activation_code});
        if(actRes.ok){ licenseActivated=true; }
      }
    } catch(e){}

    btn.className = "btn btn-primary btn-sm";
    body.innerHTML = `<div style="padding:8px 12px;background:rgba(0,200,100,.06);border-radius:8px;font-size:11px;display:flex;align-items:center;gap:6px"><span class="material-symbols-rounded" style="color:var(--c-ok);font-size:16px">verified</span><span>已就绪 · 当前账号: ${d.current_email||"—"}</span></div><div style="margin-top:8px;padding:8px 12px;background:var(--c-primary-bg);border-radius:8px;font-size:10px;color:var(--c-sec);line-height:1.6">点击「智能换号」自动获取新鲜账号并完成切换，之后在 Cursor 中选择 kiro 模型即可使用。</div>`;
  } catch {
    agentOnline = false; licenseActivated = false;
    badge.innerHTML = `<span style="width:6px;height:6px;border-radius:50%;background:var(--c-sec);display:inline-block"></span><span style="color:var(--c-sec)">连接中</span>`;
    btn.className = "btn btn-primary btn-sm hidden";
    $("#memberMode").textContent = "Agent 未连接";
    body.innerHTML = `<div style="font-size:12px;color:var(--c-sec);line-height:1.8"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><div class="cursor-progress-spinner"></div><span style="font-weight:600;font-size:13px;color:var(--c-text)">Agent 正在启动...</span></div><div>本地服务正在初始化，请稍候片刻。</div></div>`;
  }
}

async function doByokSetup(){
  const ok = await showModal("智能换号","将关闭 Cursor 并自动获取新鲜账号完成切换，完成后自动重新打开。");
  if(!ok) return;
  const btn = $("#byokBtn");
  const body = $("#cursorBody");
  btn.disabled = true;
  btn.innerHTML = '<span class="material-symbols-rounded">hourglass_top</span>换号中...';
  body.innerHTML = '<div class="cursor-progress"><div class="cursor-progress-spinner"></div><span>正在获取新鲜账号并切换...</span></div>';
  try{
    const d = await agentApi("POST","/switch",{usertoken: token});
    if(d.ok){
      body.innerHTML = `<div class="cursor-done"><span class="material-symbols-rounded" style="color:var(--c-ok);font-size:20px">check_circle</span><div><div style="font-weight:700;font-size:13px">切换完成</div><div style="font-size:11px;color:var(--c-sec);margin-top:2px">账号: ${d.email||"新账号"} · 在 Cursor 中选择 kiro 模型即可使用</div></div></div>`;
      toast("已切换到 "+(d.email||"新账号"),"ok");
      setTimeout(checkAgent, 3000);
    } else {
      await showAlert("换号失败", d.error||"未知错误");
      checkAgent();
    }
  } catch(e){
    toast("Agent 连接失败","err");
    checkAgent();
  }
  btn.disabled = false;
  btn.innerHTML = '<span class="material-symbols-rounded">bolt</span>智能换号';
}

/* ── Clean Cursor ── */
async function doCleanCursor(){
  const ok = await showModal("⚠ 完全清理 Cursor","此操作将：\n\n1. 强制关闭 Cursor 所有进程\n2. 卸载 Cursor 程序\n3. 删除全部用户数据、缓存、配置\n4. 清理注册表残留\n\n操作不可逆，确定继续？");
  if(!ok) return;
  const btn = $("#cleanBtn");
  const result = $("#cleanResult");
  btn.disabled = true;
  btn.innerHTML = '<span class="material-symbols-rounded">hourglass_top</span>清理中...';
  result.innerHTML = '<div class="cursor-progress"><div class="cursor-progress-spinner"></div><span>正在清理 Cursor...</span></div>';
  try{
    const d = await agentApi("POST","/clean-cursor",{});
    if(d.ok){
      let html = '<div style="font-size:12px;line-height:1.8">';
      html += '<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px"><span class="material-symbols-rounded" style="color:var(--c-ok);font-size:16px">check_circle</span><span style="font-weight:700">清理完成</span></div>';
      if(d.steps && d.steps.length){
        html += '<div style="background:rgba(0,0,0,.03);border-radius:8px;padding:10px 14px;font-size:11px;color:var(--c-sec);max-height:200px;overflow-y:auto">';
        d.steps.forEach(s=>{ html += '<div>'+s+'</div>'; });
        html += '</div>';
      }
      html += '</div>';
      result.innerHTML = html;
      toast("Cursor 已完全清理","ok");
    } else {
      result.innerHTML = '<div style="color:var(--c-err);font-size:12px">清理失败: '+(d.error||"未知错误")+'</div>';
      toast("清理失败","err");
    }
  } catch(e){
    result.innerHTML = '<div style="color:var(--c-err);font-size:12px">请求失败: '+e.message+'</div>';
    toast("Agent 连接失败","err");
  }
  btn.disabled = false;
  btn.innerHTML = '<span class="material-symbols-rounded">delete_forever</span>一键清理 Cursor';
}

/* ── Init ── */
(async function init(){
  // 优先用 localStorage，没有则从后端 config 恢复
  if(!token){
    try{
      const r = await agentApi("GET","/get-token");
      if(r.ok && r.usertoken){ token = r.usertoken; localStorage.setItem("apollo_user_token",token); }
    } catch{}
  }
  if(token){
    try{
      const me = await api("GET","/user/me");
      currentUser = me.name;
      showDashboard();
    } catch {
      token = "";
      localStorage.removeItem("apollo_user_token");
    }
  }
})();
</script>
</body>
</html>"""
