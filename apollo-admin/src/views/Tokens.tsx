import { useEffect, useState, useCallback } from "react";
import { api, fmtNum } from "../api";
import { useAppStore } from "../store/app";
import { confirm, prompt } from "../components/Modal";

export function TokensView() {
  const [tokens, setTokens] = useState<any[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [jsonInput, setJsonInput] = useState("");
  const [testResults, setTestResults] = useState<Record<string, any>>({});
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [tokenUsage, setTokenUsage] = useState<Record<string, any>>({});
  // 提取状态
  const [extracting, setExtracting] = useState<Record<string, boolean>>({});
  // Cursor 激活码
  const [promaxKeys, setPromaxKeys] = useState<any[]>([]);
  const [showPromaxAdd, setShowPromaxAdd] = useState(false);
  const [promaxApiKey, setPromaxApiKey] = useState("");
  const [promaxNote, setPromaxNote] = useState("");
  const toast = useAppStore((s) => s.toast);

  const load = useCallback(async () => {
    const [r, u, p] = await Promise.all([
      api("GET", "/admin/tokens"),
      api("GET", "/admin/tokens/usage/all"),
      api("GET", "/admin/promax-keys"),
    ]);
    setTokens(r.tokens || []);
    setTokenUsage(u.usage || {});
    setPromaxKeys(p.keys || []);
  }, []);

  useEffect(() => { load(); }, [load]);

  // ── Kiro 凭证操作 ──
  const remove = async (tid: string) => {
    const ok = await confirm("删除凭证", "确定删除该凭证？删除后无法恢复。");
    if (!ok) return;
    await api("DELETE", `/admin/tokens/${tid}`);
    toast("已删除", "ok");
    load();
  };

  const addToken = async () => {
    if (!jsonInput.trim()) { toast("请粘贴凭证 JSON", "err"); return; }
    try {
      const data = JSON.parse(jsonInput.trim());
      await api("POST", "/admin/tokens", data);
      toast("凭证添加成功", "ok");
      setJsonInput(""); setShowAdd(false); load();
    } catch (e: any) {
      toast("添加失败: " + (e.message || "JSON 格式错误"), "err");
    }
  };

  const loadFromFile = () => {
    const input = document.createElement("input");
    input.type = "file"; input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      setJsonInput(await file.text());
    };
    input.click();
  };

  const testToken = async (tid: string) => {
    setTesting((p) => ({ ...p, [tid]: true }));
    try {
      const r = await api("POST", `/admin/tokens/${tid}/test`);
      setTestResults((p) => ({ ...p, [tid]: r }));
      toast(r.valid ? "凭证有效" : "凭证无效: " + r.error, r.valid ? "ok" : "err");
    } catch (e: any) {
      setTestResults((p) => ({ ...p, [tid]: { valid: false, error: e.message } }));
      toast("测试失败: " + e.message, "err");
    } finally {
      setTesting((p) => ({ ...p, [tid]: false }));
    }
  };

  // ── Cursor 激活码操作 ──
  const addPromaxKey = async () => {
    if (!promaxApiKey.trim()) { toast("请输入激活码", "err"); return; }
    try {
      await api("POST", "/admin/promax-keys", { api_key: promaxApiKey.trim(), note: promaxNote.trim() });
      toast("激活码添加成功", "ok");
      setPromaxApiKey(""); setPromaxNote(""); setShowPromaxAdd(false); load();
    } catch (e: any) { toast("添加失败: " + e.message, "err"); }
  };

  const removePromaxKey = async (kid: string) => {
    const ok = await confirm("删除激活码", "确定删除？");
    if (!ok) return;
    await api("DELETE", `/admin/promax-keys/${kid}`);
    toast("已删除", "ok"); load();
  };

  const assignPromaxKey = async (kid: string, current: string) => {
    const name = await prompt("分配给用户（留空取消分配）：", current);
    if (name === null) return;
    await api("PUT", `/admin/promax-keys/${kid}/assign`, { user_name: name });
    toast(name ? `已分配给 ${name}` : "已取消分配", "ok"); load();
  };

  // ── 本机提取 ──
  const extractKiro = async () => {
    setExtracting((p) => ({ ...p, kiro: true }));
    try {
      const r = await api("POST", "/admin/extract/kiro");
      toast(`已提取 Kiro 凭证: ${r.region} · ${r.authMethod}`, "ok");
      load();
    } catch (e: any) { toast("提取失败: " + e.message, "err"); }
    finally { setExtracting((p) => ({ ...p, kiro: false })); }
  };

  // ── JSX ──
  return (
    <>
      {/* ═══ Kiro 凭证 ═══ */}
      <div className="section-title">
        <span className="material-symbols-rounded">key</span>Kiro 凭证
      </div>
      <div className="card">
        <div className="card-header">
          <span className="card-title">Kiro 凭证池</span>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-ghost btn-sm" onClick={extractKiro} disabled={extracting.kiro}>
              <span className="material-symbols-rounded">download</span>
              {extracting.kiro ? "提取中..." : "提取本机 Kiro 配置"}
            </button>
            <button className="btn btn-ghost btn-sm" onClick={loadFromFile}>
              <span className="material-symbols-rounded">upload_file</span>从文件导入
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => setShowAdd(true)}>
              <span className="material-symbols-rounded">add</span>手动添加
            </button>
          </div>
        </div>
        <div className="card-body">
          {showAdd && (
            <div style={{ marginBottom: 16, padding: 16, background: "rgba(0,0,0,0.02)", borderRadius: 12 }}>
              <textarea
                className="form-input"
                style={{ width: "100%", minHeight: 100, fontFamily: "'SF Mono','Fira Code',monospace", fontSize: 11 }}
                placeholder='粘贴凭证 JSON（含 refreshToken、region 等字段）'
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
              />
              <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                <button className="btn btn-primary btn-sm" onClick={addToken}>保存</button>
                <button className="btn btn-ghost btn-sm" onClick={() => { setShowAdd(false); setJsonInput(""); }}>取消</button>
              </div>
            </div>
          )}
          {tokens.length ? (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>认证方式</th>
                  <th>Region</th>
                  <th>状态</th>
                  <th>用量</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {tokens.map((t: any) => {
                  const u = tokenUsage[t.id];
                  const tr = testResults[t.id];
                  return (
                    <tr key={t.id}>
                      <td>
                        <span className="mono">{t.id?.slice(0, 8)}</span>
                        <button className="copy-btn" onClick={() => { navigator.clipboard.writeText(t.id); toast("已复制", "ok"); }}>
                          <span className="material-symbols-rounded">content_copy</span>
                        </button>
                      </td>
                      <td>{t.authMethod || "—"}</td>
                      <td>{t.region || "—"}</td>
                      <td><span className={`badge ${t.status === "active" ? "badge-ok" : "badge-err"}`}>{t.status}</span></td>
                      <td>{u ? `${fmtNum(u.total_tokens)} tok · ${u.requests} req` : "—"}</td>
                      <td>
                        <div style={{ display: "flex", gap: 6 }}>
                          <button className="btn btn-ghost btn-sm" onClick={() => testToken(t.id)} disabled={testing[t.id]}>
                            {testing[t.id] ? "测试中..." : "测试"}
                          </button>
                          <button className="btn btn-danger btn-sm" onClick={() => remove(t.id)}>删除</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : <div className="empty">暂无 Kiro 凭证</div>}
        </div>
      </div>

      {/* 测试结果展示 */}
      {Object.keys(testResults).length > 0 && (
        <>
          <div className="section-title">
            <span className="material-symbols-rounded">science</span>测试结果
          </div>
          <div className="card">
            <div className="card-body">
              {Object.entries(testResults).map(([tid, r]: [string, any]) => (
                <div key={tid} style={{ marginBottom: 12, padding: 12, background: r.valid ? "rgba(34,197,94,0.05)" : "rgba(239,68,68,0.05)", borderRadius: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span className="mono">{tid.slice(0, 8)}</span>
                    <span className={`badge ${r.valid ? "badge-ok" : "badge-err"}`}>{r.valid ? "有效" : "无效"}</span>
                    {r.auth_type && <span style={{ fontSize: 10, color: "var(--c-sec)" }}>{r.auth_type}</span>}
                  </div>
                  {r.valid && r.models_count > 0 && (
                    <div style={{ fontSize: 11, color: "var(--c-sec)" }}>可用模型: {r.models_count} 个</div>
                  )}
                  {r.error && <div style={{ fontSize: 11, color: "var(--c-err)" }}>{r.error}</div>}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* 凭证用量图表 */}
      {Object.keys(tokenUsage).length > 0 && (() => {
        const entries = Object.entries(tokenUsage).filter(([, v]: [string, any]) => v.total_tokens > 0);
        if (!entries.length) return null;
        const maxTok = Math.max(...entries.map(([, v]: [string, any]) => v.total_tokens), 1);
        return (
          <>
            <div className="section-title">
              <span className="material-symbols-rounded">bar_chart</span>凭证用量
            </div>
            <div className="card">
              <div className="card-body">
                <div className="bar-chart">
                  {entries.map(([tid, v]: [string, any]) => (
                    <div className="bar-row" key={tid}>
                      <span className="bar-label mono">{tid.slice(0, 8)}</span>
                      <div className="bar-track">
                        <div className="bar-fill" style={{ width: `${(v.total_tokens / maxTok * 100).toFixed(1)}%` }} />
                      </div>
                      <span className="bar-value">{fmtNum(v.total_tokens)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        );
      })()}

      {/* ═══ Cursor 激活码 ═══ */}
      <div className="section-title">
        <span className="material-symbols-rounded">vpn_key</span>Cursor 激活码
      </div>
      <div className="card">
        <div className="card-header">
          <span className="card-title">激活码管理</span>
          <button className="btn btn-primary btn-sm" onClick={() => setShowPromaxAdd(true)}>
            <span className="material-symbols-rounded">add</span>添加激活码
          </button>
        </div>
        <div className="card-body">
          {showPromaxAdd && (
            <div style={{ marginBottom: 16, padding: 16, background: "rgba(0,0,0,0.02)", borderRadius: 12 }}>
              <div className="form-row">
                <div className="form-group" style={{ flex: 2 }}>
                  <label className="form-label">API Key</label>
                  <input className="form-input" style={{ fontFamily: "'SF Mono','Fira Code',monospace", fontSize: 11 }} value={promaxApiKey} onChange={(e) => setPromaxApiKey(e.target.value)} placeholder="API-XXXXXXXXXXXX" />
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label">备注</label>
                  <input className="form-input" value={promaxNote} onChange={(e) => setPromaxNote(e.target.value)} placeholder="可选" />
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                <button className="btn btn-primary btn-sm" onClick={addPromaxKey}>保存</button>
                <button className="btn btn-ghost btn-sm" onClick={() => { setShowPromaxAdd(false); setPromaxApiKey(""); setPromaxNote(""); }}>取消</button>
              </div>
            </div>
          )}
          {promaxKeys.length ? (
            <table>
              <thead>
                <tr>
                  <th>API Key</th>
                  <th>分配给</th>
                  <th>备注</th>
                  <th>使用次数</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {promaxKeys.map((pk: any) => (
                  <tr key={pk.id}>
                    <td>
                      <span className="mono">{pk.api_key}</span>
                      <button className="copy-btn" onClick={() => { navigator.clipboard.writeText(pk.api_key); toast("已复制", "ok"); }}>
                        <span className="material-symbols-rounded">content_copy</span>
                      </button>
                    </td>
                    <td>
                      <span style={{ cursor: "pointer", textDecoration: "underline dotted", color: pk.assigned_user ? "var(--c-primary)" : "var(--c-sec)" }}
                        onClick={() => assignPromaxKey(pk.id, pk.assigned_user || "")}>
                        {pk.assigned_user || "未分配"}
                      </span>
                    </td>
                    <td style={{ fontSize: 11, color: "var(--c-sec)" }}>{pk.note || "—"}</td>
                    <td>{pk.useCount || 0}</td>
                    <td>
                      <button className="btn btn-danger btn-sm" onClick={() => removePromaxKey(pk.id)}>删除</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <div className="empty">暂无激活码，点击上方"添加"按钮</div>}
        </div>
      </div>
    </>
  );
}
