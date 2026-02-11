import { useEffect, useState, useCallback } from "react";
import { api, fmtNum, fmtDate } from "../api";
import { useAppStore } from "../store/app";
import { confirm, prompt, alert, select } from "../components/Modal";

export function UsersView() {
  const [users, setUsers] = useState<any[]>([]);
  const [tokens, setTokens] = useState<any[]>([]);
  const [usageMap, setUsageMap] = useState<Record<string, any>>({});
  const [newName, setNewName] = useState("");
  const [newTokenId, setNewTokenId] = useState("");
  const toast = useAppStore((s) => s.toast);

  const load = useCallback(async () => {
    const [u, usage, t] = await Promise.all([
      api("GET", "/admin/users"),
      api("GET", "/admin/usage"),
      api("GET", "/admin/tokens"),
    ]);
    setUsers(u.users || []);
    setTokens(t.tokens || []);
    const map: Record<string, any> = {};
    (usage.users || []).forEach((x: any) => (map[x.user_id] = x));
    setUsageMap(map);
  }, []);

  useEffect(() => { load(); }, [load]);

  const createUser = async () => {
    if (!newName.trim()) return toast("请输入用户名", "err");
    const { user } = await api("POST", "/admin/users", {
      name: newName.trim(),
      assigned_token_id: newTokenId,
    });
    toast(`用户 ${user.name} 创建成功`, "ok");
    setNewName("");
    setNewTokenId("");
    load();
  };

  const grant = async (uid: string, name: string) => {
    const amount = await prompt(`给 ${name} 充值 tokens 数量：`);
    if (!amount) return;
    const n = parseInt(amount);
    if (isNaN(n) || n === 0) return toast("请输入有效数字", "err");
    try {
      const r = await api("POST", `/admin/users/${uid}/grant`, { amount: n });
      toast(`${name} 充值 ${fmtNum(n)}，余额 ${fmtNum(r.token_balance)}`, "ok");
      load();
    } catch { toast("充值失败", "err"); }
  };

  const toggle = async (uid: string, current: string) => {
    const next = current === "active" ? "suspended" : "active";
    const ok = await confirm(
      `${next === "suspended" ? "暂停" : "恢复"}用户`,
      `确定要${next === "suspended" ? "暂停" : "恢复"}该用户吗？`
    );
    if (!ok) return;
    await api("PUT", `/admin/users/${uid}/status`, { status: next });
    toast(`用户已${next === "active" ? "恢复" : "暂停"}`, "ok");
    load();
  };

  const showToken = async (uid: string) => {
    const r = await api("GET", `/admin/users/${uid}/token`);
    await alert("用户 Token", r.usertoken);
  };

  const remove = async (uid: string) => {
    const ok = await confirm("删除用户", "确定删除该用户？此操作不可恢复。");
    if (!ok) return;
    await api("DELETE", `/admin/users/${uid}`);
    toast("已删除", "ok");
    load();
  };

  const changeToken = async (uid: string, name: string, current: string) => {
    const options = [
      { value: "", label: "全局轮询（不绑定）" },
      ...tokens.map((t) => ({
        value: t.id,
        label: `${t.id} (${t.region || "?"})${t.id === current ? " ← 当前" : ""}`,
      })),
    ];
    const chosen = await select(`为 ${name} 选择凭证`, options, current);
    if (chosen === null) return;
    try {
      await api("PUT", `/admin/users/${uid}/token`, { token_id: chosen });
      toast(`${name} 凭证已${chosen ? "绑定为 " + chosen : "取消绑定"}`, "ok");
      load();
    } catch (e: any) { toast("分配失败: " + e.message, "err"); }
  };

  const tokenLabel = (tid: string) => {
    if (!tid) return "全局轮询";
    const t = tokens.find((x) => x.id === tid);
    return t ? `${tid.slice(0, 8)} (${t.region})` : tid.slice(0, 8);
  };

  return (
    <>
      <div className="form-row">
        <div className="form-group">
          <span className="form-label">用户名</span>
          <input className="form-input" placeholder="输入用户名..." value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && createUser()} />
        </div>
        <div className="form-group">
          <span className="form-label">绑定凭证</span>
          <select className="form-input" value={newTokenId} onChange={(e) => setNewTokenId(e.target.value)}>
            <option value="">全局轮询</option>
            {tokens.map((t) => (
              <option key={t.id} value={t.id}>{t.id} ({t.region})</option>
            ))}
          </select>
        </div>
        <button className="btn btn-primary" onClick={createUser}>
          <span className="material-symbols-rounded">person_add</span>创建用户
        </button>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">用户列表</span>
          <button className="btn btn-ghost btn-sm" onClick={load}>
            <span className="material-symbols-rounded">refresh</span>刷新
          </button>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr><th>用户名</th><th>状态</th><th>绑定凭证</th><th>余额</th><th>已用</th><th>请求数</th><th>Keys</th><th>操作</th></tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const ud = usageMap[u.id] || {};
                return (
                  <tr key={u.id}>
                    <td><strong>{u.name}</strong><br /><span className="mono">{u.id}</span></td>
                    <td><span className={`badge ${u.status === "active" ? "badge-ok" : "badge-err"}`}>{u.status}</span></td>
                    <td>
                      <button className="btn btn-ghost btn-sm" onClick={() => changeToken(u.id, u.name, u.assigned_token_id || "")}>
                        <span className="material-symbols-rounded" style={{ fontSize: 14 }}>swap_horiz</span>
                        <span style={{ fontSize: 10 }}>{tokenLabel(u.assigned_token_id)}</span>
                      </button>
                    </td>
                    <td style={{ fontWeight: 700 }}>{fmtNum(ud.token_balance || 0)}</td>
                    <td>{fmtNum(ud.total_tokens || 0)}</td>
                    <td>{u.requestCount || 0}</td>
                    <td>{u.apikeys_count || 0}</td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      <button className="btn btn-primary btn-sm" onClick={() => grant(u.id, u.name)}>
                        <span className="material-symbols-rounded">toll</span>充值
                      </button>{" "}
                      <button className="btn btn-ghost btn-sm" onClick={() => toggle(u.id, u.status)}>
                        <span className="material-symbols-rounded">{u.status === "active" ? "pause" : "play_arrow"}</span>
                      </button>{" "}
                      <button className="btn btn-ghost btn-sm" onClick={() => showToken(u.id)}>
                        <span className="material-symbols-rounded">key</span>
                      </button>{" "}
                      <button className="btn btn-danger btn-sm" onClick={() => remove(u.id)}>
                        <span className="material-symbols-rounded">delete</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
