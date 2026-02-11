import { useAuthStore } from "../store/auth";
import { useAppStore, Tab } from "../store/app";

const tabs: { id: Tab; icon: string; label: string }[] = [
  { id: "overview", icon: "dashboard", label: "总览" },
  { id: "users", icon: "group", label: "用户" },
  { id: "tokens", icon: "key", label: "凭证" },
  { id: "usage", icon: "monitoring", label: "用量" },
  { id: "models", icon: "model_training", label: "模型" },
];

export function Header() {
  const { currentTab, setTab } = useAppStore();
  const logout = useAuthStore((s) => s.logout);

  return (
    <header className="header">
      <div className="header-logo">
        <div className="logo-mark">A</div>
        <div className="logo-text">APOLLO <span>ADMIN</span></div>
      </div>
      <nav className="header-tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${currentTab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            <span className="material-symbols-rounded">{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </nav>
      <div className="header-right">
        <div className="pill"><span className="dot" />ADMIN</div>
        <button className="btn-logout" onClick={logout}>退出</button>
      </div>
    </header>
  );
}
