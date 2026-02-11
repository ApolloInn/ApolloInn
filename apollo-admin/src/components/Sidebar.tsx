import { useAppStore, Tab } from "../store/app";

const navItems: { id: Tab; icon: string; label: string }[] = [
  { id: "overview", icon: "dashboard", label: "总览" },
  { id: "users", icon: "group", label: "用户管理" },
  { id: "tokens", icon: "key", label: "凭证池" },
  { id: "usage", icon: "monitoring", label: "用量监控" },
  { id: "models", icon: "model_training", label: "模型配置" },
];

export function Sidebar() {
  const { currentTab, setTab } = useAppStore();

  return (
    <aside className="sidebar">
      <div className="nav-section">
        <div className="nav-label">导航</div>
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${currentTab === item.id ? "active" : ""}`}
            onClick={() => setTab(item.id)}
          >
            <span className="material-symbols-rounded">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </div>
    </aside>
  );
}
