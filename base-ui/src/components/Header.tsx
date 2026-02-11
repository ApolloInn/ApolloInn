import { useAppStore, type TabId } from "../store/app";
import { useConnectionStore } from "../store/connection";

const TABS: { id: TabId; icon: string; label: string }[] = [
  { id: "chat", icon: "chat", label: "Neural Hub" },
  { id: "tasks", icon: "task_alt", label: "Operations" },
  { id: "skills", icon: "psychology", label: "Skills" },
  { id: "settings", icon: "settings", label: "Config" },
];

export function Header() {
  const { currentTab, switchTab, toggleLeft, toggleRight } = useAppStore();
  const { connected, latency } = useConnectionStore();

  return (
    <header className="header">
      <div className="header-logo">
        <div className="logo-mark">A</div>
        <div className="logo-text">Aurora <span>Command</span></div>
      </div>

      <nav className="header-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${currentTab === t.id ? "active" : ""}`}
            onClick={() => switchTab(t.id)}
          >
            <span className="material-symbols-rounded">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </nav>

      <div className="header-right">
        <div className="header-status">
          <span className={`status-dot ${connected ? "online" : ""}`} />
          <span>{connected ? `${latency ?? "—"}ms` : "Offline"}</span>
        </div>
        <button className="header-icon-btn" title="Notifications">
          <span className="material-symbols-rounded">notifications</span>
        </button>
        <button className="header-icon-btn" title="Toggle Sidebars" onClick={() => { toggleLeft(); toggleRight(); }}>
          <span className="material-symbols-rounded">view_sidebar</span>
        </button>
      </div>
    </header>
  );
}
