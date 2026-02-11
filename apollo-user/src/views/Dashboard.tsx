import { useEffect, useState, useCallback } from "react";
import { useAuthStore } from "../store/auth";
import { useAppStore } from "../store/app";
import { api, fmtNum } from "../api";
import { confirm, alert } from "../components/Modal";

export function Dashboard() {
  const { userName, logout } = useAuthStore();
  const toast = useAppStore((s) => s.toast);
  const [me, setMe] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);
  const [keys, setKeys] = useState<string[]>([]);
  const [combos, setCombos] = useState<Record<string, any>>({});
  const [cursorResult, setCursorResult] = useState<{
    email: string;
    steps: string[];
  } | null>(null);
  const [agentOnline, setAgentOnline] = useState<boolean | null>(null);
  const [licenseActivated, setLicenseActivated] = useState(false);
  const [smartSwitching, setSmartSwitching] = useState(false);

  // 检测本地 agent + 自动激活
  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const r = await fetch("http://127.0.0.1:19080/status", { mode: "cors" });
        const d = await r.json();
        if (!mounted) return;
        setAgentOnline(d.ok === true);
        if (d.license_activated) {
          setLicenseActivated(true);
        } else if (d.ok) {
          // agent 在线但未激活 → 从服务器拿激活码自动激活
          try {
            const ar = await api("GET", "/user/cursor-activation");
            if (ar.activation_code) {
              const actRes = await fetch("http://127.0.0.1:19080/license-activate", {
                method: "POST", headers: { "Content-Type": "application/json" }, mode: "cors",
                body: JSON.stringify({ code: ar.activation_code }),
              });
              const actData = await actRes.json();
              if (mounted && actData.ok) setLicenseActivated(true);
            }
          } catch { /* 服务器没分配激活码 */ }
        }
      } catch { if (mounted) setAgentOnline(false); }
    };
    check();
    const timer = setInterval(check, 8000);
    return () => { mounted = false; clearInterval(timer); };
  }, []);

  const load = useCallback(async () => {
    const [m, u, k, c] = await Promise.all([
      api("GET", "/user/me"),
      api("GET", "/user/usage"),
      api("GET", "/user/apikeys"),
      api("GET", "/user/combos"),
    ]);
    setMe(m);
    setUsage(u);
    setKeys(k.apikeys || []);
    setCombos(c.combos || {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const createKey = async () => {
    const r = await api("POST", "/user/apikeys");
    toast("API Key 创建成功: " + r.apikey, "ok");
    load();
  };

  const revokeKey = async (key: string) => {
    const ok = await confirm("撤销 API Key", "确定撤销此 API Key？撤销后无法恢复。");
    if (!ok) return;
    await api("DELETE", "/user/apikeys", { apikey: key });
    toast("已撤销", "ok");
    load();
  };

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text).then(() => toast("已复制", "ok"));
  };


  const smartSwitch = async () => {
    const ok = await confirm("智能换号", "将自动获取新鲜账号并完成切换：关闭 Cursor → 重置环境 → 写入新账号 → 重新打开 Cursor。\n\n确认？");
    if (!ok) return;
    setSmartSwitching(true);
    setCursorResult(null);
    try {
      const res = await fetch("http://127.0.0.1:19080/smart-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        mode: "cors",
        body: JSON.stringify({}),
      });
      const d = await res.json();
      if (d.ok) {
        setCursorResult({ email: d.email || "", steps: d.steps || ["完成"] });
        toast(`已切换到 ${d.email || "新账号"}`, "ok");
      } else {
        await alert("换号失败", d.error || "未知错误");
      }
    } catch {
      toast("Agent 连接失败", "err");
    } finally {
      setSmartSwitching(false);
    }
  };

  const comboEntries = Object.entries(combos);

  if (!usage) return <div className="empty">加载中...</div>;

  const granted = usage.token_granted || 0;
  const balance = usage.token_balance || 0;
  const used = usage.usage?.total_tokens || 0;
  const pct = granted > 0 ? (balance / granted) * 100 : 0;
  const barClass = pct > 30 ? "ok" : pct > 10 ? "low" : "empty";

  const dates = Object.entries(usage.usage?.by_date || {}).sort(
    (a, b) => (b[0] as string).localeCompare(a[0] as string)
  ) as [string, any][];

  const models = Object.entries(usage.usage?.by_model || {}) as [string, any][];
  const maxM = Math.max(...models.map(([, v]) => v.prompt + v.completion), 1);

  const apiBase = "https://apolloinn.site";

  return (
    <>
      <header className="header">
        <div className="header-logo">
          <div className="logo-mark">A</div>
          <div className="logo-text">APOLLO <span>USER</span></div>
        </div>
        <div className="header-right">
          <div className="user-pill">
            <span className="material-symbols-rounded">person</span>
            {userName}
          </div>
          <button className="btn-logout" onClick={logout}>退出</button>
        </div>
      </header>

      <div className="main-scroll">
        <div className="main-inner">
          {/* Balance */}
          <div className="stats-grid">
            <div className="stat-card highlight">
              <div className="stat-label">剩余额度</div>
              <div className="stat-value">{fmtNum(balance)}</div>
              <div className="stat-sub">已分配 {fmtNum(granted)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">已消耗</div>
              <div className="stat-value">{fmtNum(used)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">总请求</div>
              <div className="stat-value">{usage.requestCount || 0}</div>
            </div>
          </div>

          {granted > 0 && (
            <div className="card" style={{ marginBottom: 24 }}>
              <div className="card-body">
                <div className="stat-label">额度使用进度</div>
                <div className="balance-wrap">
                  <div className="balance-meta">
                    <span>{fmtNum(used)} 已用</span>
                    <span>{fmtNum(balance)} 剩余</span>
                  </div>
                  <div className="balance-bar">
                    <div
                      className={`balance-fill ${barClass}`}
                      style={{ width: `${Math.min(100, 100 - pct).toFixed(1)}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* API Keys */}
          <div className="section-title">
            <span className="material-symbols-rounded">key</span>API Keys
          </div>
          <div className="card">
            <div className="card-header">
              <span className="card-title">我的 API Keys</span>
              <button className="btn btn-primary btn-sm" onClick={createKey}>
                <span className="material-symbols-rounded">add</span>创建
              </button>
            </div>
            <div className="card-body">
              {keys.length ? (
                <table>
                  <thead><tr><th>API Key</th><th>操作</th></tr></thead>
                  <tbody>
                    {keys.map((k) => (
                      <tr key={k}>
                        <td>
                          <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                            <span className="mono">{k}</span>
                            <button className="copy-btn" onClick={() => copyText(k)} title="复制">
                              <span className="material-symbols-rounded">content_copy</span>
                            </button>
                          </span>
                        </td>
                        <td>
                          <button className="btn btn-danger btn-sm" onClick={() => revokeKey(k)}>
                            <span className="material-symbols-rounded">delete</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="empty">暂无 API Key，点击上方"创建"按钮生成</div>
              )}
            </div>
          </div>

          {/* Endpoint */}
          <div className="section-title">
            <span className="material-symbols-rounded">link</span>接入信息
          </div>
          <div className="card">
            <div className="card-body">
              <div className="stat-label">Base URL</div>
              <div className="endpoint-box">
                <span>{apiBase}/v1</span>
                <button className="copy-btn" onClick={() => copyText(apiBase + "/v1")}>
                  <span className="material-symbols-rounded">content_copy</span>
                </button>
              </div>
              <div className="endpoint-hint">
                在 OpenAI 兼容客户端（Cursor、ChatBox 等）中填入上方地址作为 Base URL，API Key 填你的 <code>ap-xxx</code> key 即可。
              </div>
            </div>
          </div>

          {/* Cursor 权限 */}
          <div className="section-title">
            <span className="material-symbols-rounded">desktop_mac</span>Cursor 权限
          </div>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Cursor Pro 智能换号</span>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {agentOnline !== null && (
                  <span style={{ fontSize: 10, color: agentOnline ? "var(--c-ok)" : "var(--c-sec)", display: "flex", alignItems: "center", gap: 4 }}>
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: agentOnline ? "var(--c-ok)" : "var(--c-sec)", display: "inline-block" }} />
                    {agentOnline ? "Agent 在线" : "Agent 离线"}
                  </span>
                )}
                {agentOnline && licenseActivated && (
                  <button className="btn btn-primary btn-sm" onClick={smartSwitch} disabled={smartSwitching}>
                    <span className="material-symbols-rounded">{smartSwitching ? "hourglass_top" : "bolt"}</span>
                    {smartSwitching ? "换号中..." : "智能换号"}
                  </button>
                )}
              </div>
            </div>
            <div className="card-body">
              {smartSwitching && (
                <div className="cursor-progress">
                  <div className="cursor-progress-spinner" />
                  <span>正在获取新鲜账号并切换...</span>
                </div>
              )}
              {cursorResult ? (
                <div className="cursor-done">
                  <span className="material-symbols-rounded" style={{ color: "var(--c-ok)", fontSize: 20 }}>check_circle</span>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 13 }}>切换完成</div>
                    <div style={{ fontSize: 11, color: "var(--c-sec)", marginTop: 2 }}>
                      账号: {cursorResult.email} · 订阅: Pro
                    </div>
                    <div style={{ fontSize: 10, color: "var(--c-sec)", marginTop: 4 }}>
                      {cursorResult.steps.map((s, i) => <span key={i}>✓ {s}{i < cursorResult.steps.length - 1 ? " → " : ""}</span>)}
                    </div>
                  </div>
                </div>
              ) : !smartSwitching ? (
                <div style={{ fontSize: 12, color: "var(--c-sec)", lineHeight: 1.8 }}>
                  {agentOnline ? (
                    <div>
                      {licenseActivated ? (
                        <div style={{ padding: "8px 12px", background: "rgba(0,200,100,0.06)", borderRadius: 8, fontSize: 11, display: "flex", alignItems: "center", gap: 6 }}>
                          <span className="material-symbols-rounded" style={{ color: "var(--c-ok)", fontSize: 16 }}>verified</span>
                          <span>已就绪 · 点击上方「智能换号」自动获取新鲜账号并完成切换</span>
                        </div>
                      ) : (
                        <div style={{ padding: "10px 12px", background: "rgba(0,0,0,0.03)", borderRadius: 8, fontSize: 11, lineHeight: 1.6 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                            <span className="material-symbols-rounded" style={{ color: "var(--c-ok)", fontSize: 16 }}>check_circle</span>
                            <span style={{ color: "var(--c-text)" }}>Agent 已连接，正在自动激活...</span>
                          </div>
                          <div style={{ color: "var(--c-sec)" }}>系统将自动为你分配激活码并完成激活，请稍候。</div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div>
                      <div style={{ marginBottom: 12, fontSize: 12 }}>
                        下载 Apollo Agent 后双击运行，无需安装任何环境。Agent 启动后刷新本页即可使用智能换号。
                      </div>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
                        <a href="https://github.com/ApolloInn/ApolloInn/releases/latest/download/ApolloAgent.dmg" target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-sm" style={{ textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 4 }}>
                          <span className="material-symbols-rounded" style={{ fontSize: 14 }}>laptop_mac</span>macOS 下载
                        </a>
                        <a href="https://github.com/ApolloInn/ApolloInn/releases/latest/download/ApolloAgent.exe" target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-sm" style={{ textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 4 }}>
                          <span className="material-symbols-rounded" style={{ fontSize: 14 }}>desktop_windows</span>Windows 下载
                        </a>
                      </div>
                      <div style={{ fontSize: 10, opacity: 0.5 }}>
                        下载后运行 → 看到「等待网页端指令」后刷新本页 → 系统自动激活 → 点击「智能换号」
                      </div>
                      <div style={{ fontSize: 10, opacity: 0.4, marginTop: 4 }}>
                        <a href="https://github.com/ApolloInn/ApolloInn/releases" target="_blank" rel="noopener noreferrer" style={{ color: "inherit" }}>查看所有版本 →</a>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </div>

          {/* 反向代理配置指南 */}
          <div className="section-title">
            <span className="material-symbols-rounded">settings_suggest</span>配置反向代理（重要）
          </div>
          <div className="card">
            <div className="card-body" style={{ fontSize: 12, color: "var(--c-sec)", lineHeight: 1.9 }}>
              <div style={{ marginBottom: 8, color: "var(--c-text)", fontSize: 13 }}>
                切换账号后，请按以下步骤配置反向代理以长期稳定使用：
              </div>
              <div style={{ paddingLeft: 4 }}>
                进入 Cursor 工作区，点击右上角齿轮图标，进入 Cursor Settings<br />
                选择 Models 选项卡，展开底部"自定义 API Keys"<br />
                打开 OpenAI API Key 和 Override OpenAI Base URL 两个开关<br />
                填入你的 API Key（<code style={{ background: "rgba(0,0,0,0.06)", padding: "1px 5px", borderRadius: 4 }}>ap-xxx</code>）和接口地址：
              </div>
              <div style={{ position: "relative", margin: "8px 0 8px 4px" }}>
                <code style={{ background: "rgba(0,0,0,0.06)", padding: "6px 30px 6px 8px", borderRadius: 4, display: "block", fontSize: 11 }}>https://apolloinn.site/v1</code>
                <button className="copy-btn" style={{ position: "absolute", top: 4, right: 4 }} onClick={() => copyText("https://apolloinn.site/v1")} title="复制">
                  <span className="material-symbols-rounded" style={{ fontSize: 14 }}>content_copy</span>
                </button>
              </div>
              <div style={{ paddingLeft: 4 }}>
                在 Models 列表中添加自定义模型，如 <code style={{ background: "rgba(0,0,0,0.06)", padding: "1px 5px", borderRadius: 4 }}>kiro-opus-4-6</code>
              </div>
              <div style={{ marginTop: 10, padding: "8px 12px", background: "rgba(255,180,0,0.08)", borderRadius: 8, fontSize: 11, lineHeight: 1.6 }}>
                注意：请使用反向代理模型（kiro-xxx），不要直接使用 Cursor 自带账号的模型，以免账号透支风控。
              </div>
            </div>
          </div>

          {/* Model Combos */}
          <div className="section-title">
            <span className="material-symbols-rounded">shuffle</span>模型映射
          </div>
          <div className="card">
            <div style={{ overflowX: "auto" }}>
              {comboEntries.length ? (
                <table>
                  <thead><tr><th>映射名称</th><th>目标模型</th></tr></thead>
                  <tbody>
                    {comboEntries.map(([k, v]) => (
                      <tr key={k}>
                        <td>
                          <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                            <span className="mono">{k}</span>
                            <button className="copy-btn" onClick={() => copyText(k)} title="复制">
                              <span className="material-symbols-rounded">content_copy</span>
                            </button>
                          </span>
                        </td>
                        <td><span className="mono">{Array.isArray(v) ? v.join(", ") : v}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <div className="empty">暂无模型映射</div>}
            </div>
          </div>

          {/* Usage by date */}
          <div className="section-title">
            <span className="material-symbols-rounded">monitoring</span>用量统计
          </div>
          <div className="card">
            <div style={{ overflowX: "auto" }}>
              {dates.length ? (
                <table>
                  <thead><tr><th>日期</th><th>请求数</th><th>Prompt</th><th>Completion</th><th>总计</th></tr></thead>
                  <tbody>
                    {dates.map(([d, v]) => (
                      <tr key={d}>
                        <td>{d}</td><td>{v.requests}</td><td>{fmtNum(v.prompt)}</td>
                        <td>{fmtNum(v.completion)}</td><td style={{ fontWeight: 700 }}>{fmtNum(v.prompt + v.completion)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <div className="empty">暂无使用记录</div>}
            </div>
          </div>

          {/* Usage by model */}
          <div className="section-title">
            <span className="material-symbols-rounded">model_training</span>按模型用量
          </div>
          <div className="card">
            <div className="card-body">
              {models.length ? (
                <div className="bar-chart">
                  {models.map(([m, v]) => (
                    <div className="bar-row" key={m}>
                      <span className="bar-label">{m}</span>
                      <div className="bar-track">
                        <div className="bar-fill" style={{ width: `${((v.prompt + v.completion) / maxM * 100).toFixed(1)}%` }} />
                      </div>
                      <span className="bar-value">{fmtNum(v.prompt + v.completion)}</span>
                    </div>
                  ))}
                </div>
              ) : <div className="empty">暂无数据</div>}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
