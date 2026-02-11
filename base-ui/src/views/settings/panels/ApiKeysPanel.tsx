export function ApiKeysPanel() {
  return (
    <>
      <div className="settings-section">
        <div className="settings-section-title">LLM Service Keys</div>
        <ApiKeyCard name="Anthropic API Key" value="sk-ant-api03-•••••••" configured />
        <ApiKeyCard name="OpenAI API Key" value="Not configured" />
        <ApiKeyCard name="DeepSeek API Key" value="Not configured" />
      </div>
      <div className="settings-section">
        <div className="settings-section-title">Third-party Services</div>
        <ApiKeyCard name="Google Calendar API" value="Not configured" />
      </div>
    </>
  );
}

function ApiKeyCard({ name, value, configured }: { name: string; value: string; configured?: boolean }) {
  return (
    <div className="api-key-card">
      <span className="material-symbols-rounded" style={{ fontSize: 20, color: "var(--color-secondary)" }}>key</span>
      <div className="api-key-info">
        <div className="api-key-name">{name}</div>
        <div className="api-key-value">{value}</div>
      </div>
      <span className={`api-key-status ${configured ? "configured" : "missing"}`}>
        {configured ? "Configured" : "Missing"}
      </span>
    </div>
  );
}
