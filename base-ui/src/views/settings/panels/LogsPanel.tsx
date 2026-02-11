import { useState, useEffect, useRef } from "react";

interface LogEntry {
  id: number;
  level: "INFO" | "WARN" | "ERROR" | "DEBUG";
  time: string;
  message: string;
}

let logId = 0;

export function LogsPanel() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const viewerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const addLog = (level: LogEntry["level"], message: string) => {
      const time = new Date().toLocaleTimeString("en-US", { hour12: false });
      setLogs((prev) => [...prev.slice(-199), { id: ++logId, level, time, message }]);
    };

    addLog("INFO", "AURORA Web UI initialized");
    addLog("INFO", "Stitch Design System v2.0 loaded");
    addLog("INFO", "React + Vite frontend active");
  }, []);

  useEffect(() => {
    viewerRef.current?.scrollTo({ top: viewerRef.current.scrollHeight });
  }, [logs]);

  return (
    <div className="settings-section">
      <div className="settings-section-title">System Logs</div>
      <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
        <button className="filter-pill active" style={{ padding: "4px 12px", fontSize: 9, borderRadius: 8, width: "auto" }}>ALL</button>
        <button className="filter-pill" style={{ padding: "4px 12px", fontSize: 9, borderRadius: 8, width: "auto" }}>INFO</button>
        <button className="filter-pill" style={{ padding: "4px 12px", fontSize: 9, borderRadius: 8, width: "auto" }}>WARN</button>
        <button className="filter-pill" style={{ padding: "4px 12px", fontSize: 9, borderRadius: 8, width: "auto" }}>ERROR</button>
      </div>
      <div className="log-viewer" ref={viewerRef}>
        {logs.map((l) => (
          <div key={l.id} className="log-line">
            <span className="log-time">{l.time}</span>
            <span className={`log-tag log-${l.level.toLowerCase()}`}>[{l.level}]</span>
            {" "}{l.message}
          </div>
        ))}
      </div>
      <div className="btn-row" style={{ marginTop: 12 }}>
        <button className="settings-btn secondary" onClick={() => setLogs([])}>Clear Logs</button>
        <button className="settings-btn secondary">Export Logs</button>
      </div>
    </div>
  );
}
