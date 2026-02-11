import { useAppStore } from "../store/app";
import { useChatStore } from "../store/chat";
import { useSettingsStore } from "../store/settings";

export function SidebarLeft() {
  const { currentTab, leftCollapsed } = useAppStore();

  return (
    <aside className={`sidebar-left ${leftCollapsed ? "collapsed" : ""}`}>
      {currentTab === "chat" && <ChatSidebar />}
      {currentTab === "tasks" && <TasksSidebar />}
      {currentTab === "skills" && <SkillsSidebar />}
      {currentTab === "settings" && <SettingsSidebar />}
    </aside>
  );
}

function ChatSidebar() {
  const { sessions, currentSessionId, selectSession, createSession } = useChatStore();

  return (
    <>
      <div className="sidebar-section">
        <div className="section-title">
          Sessions
          <button className="section-action">
            <span className="material-symbols-rounded" style={{ fontSize: 14 }}>search</span>
          </button>
        </div>
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`session-item ${s.id === currentSessionId ? "active" : ""}`}
            onClick={() => selectSession(s.id)}
          >
            <div className="session-icon">
              <span className="material-symbols-rounded">chat_bubble</span>
            </div>
            <div className="session-info">
              <div className="session-name">{s.name}</div>
              <div className="session-meta">{s.messages.length} messages</div>
            </div>
          </div>
        ))}
        <button className="new-btn" onClick={createSession}>
          <span className="material-symbols-rounded" style={{ fontSize: 14 }}>add</span>
          New Chat
        </button>
      </div>

      <div className="sidebar-section">
        <div className="section-title">Active Agents</div>
        <div className="agent-card">
          <div className="agent-dot active" />
          <div>
            <div className="agent-name">Brain Engine</div>
            <div className="agent-status">Ready</div>
          </div>
        </div>
        <div className="agent-card">
          <div className="agent-dot idle" />
          <div>
            <div className="agent-name">Skill Router</div>
            <div className="agent-status">Standby</div>
          </div>
        </div>
      </div>
    </>
  );
}

function TasksSidebar() {
  return (
    <div className="sidebar-section">
      <div className="section-title">Task Filters</div>
      <div className="filter-pills">
        <button className="filter-pill active">All <span className="filter-pill-count">0</span></button>
        <button className="filter-pill">Running <span className="filter-pill-count">0</span></button>
        <button className="filter-pill">Completed <span className="filter-pill-count">0</span></button>
        <button className="filter-pill">Failed <span className="filter-pill-count">0</span></button>
      </div>
    </div>
  );
}

function SkillsSidebar() {
  return (
    <>
      <div className="sidebar-section">
        <div className="section-title">Categories</div>
        <div className="filter-pills">
          <button className="filter-pill active">All <span className="filter-pill-count">19</span></button>
          <button className="filter-pill">Code <span className="filter-pill-count">3</span></button>
          <button className="filter-pill">Web <span className="filter-pill-count">2</span></button>
          <button className="filter-pill">File <span className="filter-pill-count">2</span></button>
        </div>
      </div>
      <div className="sidebar-section">
        <div className="section-title">Connectors</div>
        <div className="status-item">
          <span className="status-item-dot" style={{ background: "var(--color-success)" }} /> Web Channel
          <span className="status-item-time">Active</span>
        </div>
        <div className="status-item">
          <span className="status-item-dot" style={{ background: "#d1d5db" }} /> Telegram
          <span className="status-item-time">Off</span>
        </div>
      </div>
    </>
  );
}

function SettingsSidebar() {
  const { activePanel, setActivePanel } = useSettingsStore();

  const items: { group: string; entries: { id: Parameters<typeof setActivePanel>[0]; icon: string; label: string }[] }[] = [
    {
      group: "Account & Keys",
      entries: [
        { id: "apikeys", icon: "key", label: "API Keys" },
        { id: "models", icon: "model_training", label: "Model Config" },
      ],
    },
    {
      group: "Personality",
      entries: [
        { id: "personality", icon: "face", label: "Personality" },
        { id: "memory", icon: "memory", label: "Memory & Privacy" },
      ],
    },
    {
      group: "Advanced",
      entries: [
        { id: "logs", icon: "description", label: "Logs" },
        { id: "security", icon: "shield", label: "Security" },
      ],
    },
  ];

  return (
    <div className="sidebar-section" style={{ paddingBottom: 0 }}>
      {items.map((g) => (
        <div key={g.group}>
          <div className="settings-nav-group">{g.group}</div>
          {g.entries.map((e) => (
            <button
              key={e.id}
              className={`settings-nav-item ${activePanel === e.id ? "active" : ""}`}
              onClick={() => setActivePanel(e.id)}
            >
              <span className="material-symbols-rounded">{e.icon}</span>
              {e.label}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
