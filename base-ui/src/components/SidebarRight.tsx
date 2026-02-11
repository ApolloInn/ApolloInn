import { useAppStore } from "../store/app";
import { useChatStore } from "../store/chat";
import { useConnectionStore } from "../store/connection";

export function SidebarRight() {
  const { currentTab, rightCollapsed } = useAppStore();

  return (
    <aside className={`sidebar-right ${rightCollapsed ? "collapsed" : ""}`}>
      {currentTab === "chat" && <ChatRight />}
      {currentTab === "tasks" && <TasksRight />}
      {currentTab === "skills" && <SkillsRight />}
      {currentTab === "settings" && <SettingsRight />}
    </aside>
  );
}

function ChatRight() {
  const messages = useChatStore((s) => {
    const sess = s.sessions.find((ss) => ss.id === s.currentSessionId);
    return sess?.messages ?? [];
  });

  const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
  const goal = lastUserMsg
    ? lastUserMsg.content.length > 30 ? lastUserMsg.content.slice(0, 30) + "..." : lastUserMsg.content
    : "Ready to assist";

  return (
    <>
      <div className="sidebar-section">
        <div className="section-title">Current Goal</div>
        <div className="status-card">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span className="material-symbols-rounded" style={{ fontSize: 16 }}>flag</span>
            <span style={{ fontSize: 12, fontWeight: 700 }}>{goal}</span>
          </div>
          <div style={{ fontSize: 9, color: "var(--color-secondary)", letterSpacing: "0.1em" }}>
            Mode: General Assistant
          </div>
        </div>
      </div>

      <div className="sidebar-section">
        <div className="section-title">
          Upcoming
          <span className="material-symbols-rounded" style={{ fontSize: 16, cursor: "pointer" }}>event</span>
        </div>
        <div className="timeline">
          <div className="timeline-item">
            <div className="timeline-dot" />
            <div className="timeline-content">
              <div className="timeline-time">NOW</div>
              <div className="timeline-title">System Online</div>
            </div>
          </div>
          <div className="timeline-item future">
            <div className="timeline-dot" />
            <div className="timeline-content">
              <div className="timeline-time">NEXT</div>
              <div className="timeline-title">Health Check</div>
            </div>
          </div>
        </div>
      </div>

      <div className="sidebar-section">
        <div className="section-title">Recent Memory</div>
        <div style={{ fontSize: 11, color: "var(--color-secondary)", padding: "4px 0" }}>
          {messages.length > 0 ? `${messages.length} messages in session` : "Session initialized"}
        </div>
      </div>
    </>
  );
}

function TasksRight() {
  return (
    <>
      <div className="sidebar-section">
        <div className="section-title">Task Queue</div>
        <div style={{ fontSize: 11, color: "var(--color-secondary)", padding: "8px 0" }}>Queue empty</div>
      </div>
      <div className="sidebar-section">
        <div className="section-title">Alerts</div>
        <div style={{ fontSize: 11, color: "var(--color-secondary)", padding: "8px 0" }}>No alerts</div>
      </div>
    </>
  );
}

function SkillsRight() {
  return (
    <>
      <div className="sidebar-section">
        <div className="section-title">Integration Status</div>
        <div className="status-item">
          <span className="status-item-dot" style={{ background: "var(--color-success)" }} />
          Web Channel <span className="status-item-time">Active</span>
        </div>
        <div className="status-item">
          <span className="status-item-dot" style={{ background: "#d1d5db" }} />
          Telegram <span className="status-item-time">Off</span>
        </div>
      </div>
      <div className="sidebar-section">
        <div className="section-title">Usage Today</div>
        <div className="status-item">
          <span style={{ fontSize: 10, color: "var(--color-secondary)" }}>Tool Calls</span>
          <span className="status-item-time">0</span>
        </div>
        <div className="status-item">
          <span style={{ fontSize: 10, color: "var(--color-secondary)" }}>Success Rate</span>
          <span className="status-item-time">—</span>
        </div>
      </div>
    </>
  );
}

function SettingsRight() {
  const { connected, latency } = useConnectionStore();

  return (
    <>
      <div className="sidebar-section">
        <div className="section-title">Connectivity</div>
        <div className="status-item">
          <span className="status-item-dot" style={{ background: connected ? "var(--color-success)" : "var(--color-error)" }} />
          Gateway API
          <span className="status-item-time">{connected && latency != null ? `${latency}ms` : "—"}</span>
        </div>
      </div>
      <div className="sidebar-section">
        <div className="section-title">Recent Errors</div>
        <div style={{ fontSize: 11, color: "var(--color-secondary)", padding: "8px 0" }}>No recent errors</div>
      </div>
    </>
  );
}
