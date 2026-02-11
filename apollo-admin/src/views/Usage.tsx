import { useEffect, useState } from "react";
import { api, fmtNum } from "../api";

export function UsageView() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api("GET", "/admin/usage").then(setData);
  }, []);

  if (!data) return <div className="empty">加载中...</div>;

  const models = Object.entries(data.by_model || {}) as [string, any][];
  const maxM = Math.max(...models.map(([, v]) => v.prompt + v.completion), 1);
  const dates = Object.entries(data.by_date || {}) as [string, any][];

  return (
    <>
      <div className="stats-grid">
        <div className="stat-card highlight">
          <div className="stat-label">总 TOKENS</div>
          <div className="stat-value">{fmtNum(data.total_tokens)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Prompt</div>
          <div className="stat-value">{fmtNum(data.total_prompt_tokens)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Completion</div>
          <div className="stat-value">{fmtNum(data.total_completion_tokens)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">总请求</div>
          <div className="stat-value">{data.total_requests}</div>
        </div>
      </div>

      <div className="section-title">
        <span className="material-symbols-rounded">model_training</span>按模型统计
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

      <div className="section-title">
        <span className="material-symbols-rounded">calendar_today</span>按日期统计
      </div>
      <div className="card">
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr><th>日期</th><th>请求数</th><th>Prompt</th><th>Completion</th><th>总计</th></tr></thead>
            <tbody>
              {dates.length ? dates.map(([dt, v]) => (
                <tr key={dt}>
                  <td>{dt}</td><td>{v.requests}</td><td>{fmtNum(v.prompt)}</td>
                  <td>{fmtNum(v.completion)}</td><td style={{ fontWeight: 700 }}>{fmtNum(v.prompt + v.completion)}</td>
                </tr>
              )) : <tr><td colSpan={5} className="empty">暂无数据</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section-title">
        <span className="material-symbols-rounded">person</span>按用户统计
      </div>
      <div className="card">
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr><th>用户</th><th>状态</th><th>已分配</th><th>余额</th><th>已用</th><th>请求数</th></tr></thead>
            <tbody>
              {(data.users || []).map((u: any) => (
                <tr key={u.user_id}>
                  <td><strong>{u.name}</strong></td>
                  <td><span className={`badge ${u.status === "active" ? "badge-ok" : "badge-err"}`}>{u.status}</span></td>
                  <td>{fmtNum(u.token_granted)}</td>
                  <td style={{ fontWeight: 700 }}>{fmtNum(u.token_balance)}</td>
                  <td>{fmtNum(u.total_tokens)}</td>
                  <td>{u.requestCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
