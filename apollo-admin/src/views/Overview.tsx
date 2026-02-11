import { useEffect, useState } from "react";
import { api, fmtNum } from "../api";

export function OverviewView() {
  const [status, setStatus] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);

  useEffect(() => {
    Promise.all([api("GET", "/admin/status"), api("GET", "/admin/usage")]).then(
      ([s, u]) => { setStatus(s); setUsage(u); }
    );
  }, []);

  if (!status || !usage) return <div className="empty">加载中...</div>;

  const today = new Date().toISOString().slice(0, 10);
  const todayData = usage.by_date?.[today] || { prompt: 0, completion: 0, requests: 0 };
  const maxTok = Math.max(...(usage.users || []).map((u: any) => u.total_tokens), 1);

  return (
    <>
      <div className="stats-grid">
        <div className="stat-card highlight">
          <div className="stat-label">总 TOKENS 消耗</div>
          <div className="stat-value">{fmtNum(usage.total_tokens)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">总请求数</div>
          <div className="stat-value">{usage.total_requests}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">活跃用户</div>
          <div className="stat-value">{status.active_users}</div>
          <div className="stat-sub">共 {status.users} 个用户</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">活跃凭证</div>
          <div className="stat-value">{status.active_tokens}</div>
          <div className="stat-sub">共 {status.tokens} 个凭证</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">模型映射</div>
          <div className="stat-value">{status.combos}</div>
          <div className="stat-sub">{status.combos} combos</div>
        </div>
      </div>

      <div className="section-title">
        <span className="material-symbols-rounded">monitoring</span>今日用量
      </div>
      <div className="card">
        <div className="card-body">
          {todayData.requests > 0 ? (
            <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
              <div><div className="stat-label">请求数</div><div style={{ fontSize: 20, fontWeight: 800 }}>{todayData.requests}</div></div>
              <div><div className="stat-label">Prompt</div><div style={{ fontSize: 20, fontWeight: 800 }}>{fmtNum(todayData.prompt)}</div></div>
              <div><div className="stat-label">Completion</div><div style={{ fontSize: 20, fontWeight: 800 }}>{fmtNum(todayData.completion)}</div></div>
              <div><div className="stat-label">总计</div><div style={{ fontSize: 20, fontWeight: 800 }}>{fmtNum(todayData.prompt + todayData.completion)}</div></div>
            </div>
          ) : <div className="empty">今日暂无请求</div>}
        </div>
      </div>

      <div className="section-title">
        <span className="material-symbols-rounded">leaderboard</span>用户排行
      </div>
      <div className="card">
        <div className="card-body">
          {usage.users?.length ? (
            <div className="bar-chart">
              {usage.users.slice(0, 10).map((u: any) => (
                <div className="bar-row" key={u.user_id}>
                  <span className="bar-label">{u.name}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${(u.total_tokens / maxTok * 100).toFixed(1)}%` }} />
                  </div>
                  <span className="bar-value">{fmtNum(u.total_tokens)}</span>
                </div>
              ))}
            </div>
          ) : <div className="empty">暂无数据</div>}
        </div>
      </div>
    </>
  );
}
