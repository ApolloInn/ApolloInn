import { useEffect, useState } from "react";
import { api } from "../api";
import { useAppStore } from "../store/app";

export function ModelsView() {
  const [combos, setCombos] = useState<Record<string, any>>({});
  const toast = useAppStore((s) => s.toast);

  useEffect(() => {
    api("GET", "/admin/combos").then((c) => setCombos(c.combos || {}));
  }, []);

  const comboEntries = Object.entries(combos);

  const copy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => toast("已复制", "ok"));
  };

  return (
    <>
      <div className="section-title">
        <span className="material-symbols-rounded">shuffle</span>Combo 映射
      </div>
      <div className="card">
        <div className="card-header"><span className="card-title">Combos</span></div>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr><th>Combo 名称</th><th>映射模型</th></tr></thead>
            <tbody>
              {comboEntries.length ? comboEntries.map(([k, v]) => (
                <tr key={k}>
                  <td>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      <span className="mono">{k}</span>
                      <button className="copy-btn" onClick={() => copy(k)} title="复制">
                        <span className="material-symbols-rounded">content_copy</span>
                      </button>
                    </span>
                  </td>
                  <td><span className="mono">{Array.isArray(v) ? v.join(", ") : v}</span></td>
                </tr>
              )) : <tr><td colSpan={2} className="empty">暂无 Combo</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
