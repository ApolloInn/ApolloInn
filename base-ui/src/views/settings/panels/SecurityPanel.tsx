import { Toggle } from "../../../components/Toggle";

export function SecurityPanel() {
  return (
    <div className="settings-section">
      <div className="settings-section-title">Execution Security</div>
      <div className="settings-field">
        <label className="settings-label">Confirmation Level</label>
        <select className="settings-select" defaultValue="sensitive">
          <option value="sensitive">Sensitive operations only</option>
          <option value="all">All tool executions</option>
          <option value="never">Never (trust mode)</option>
        </select>
      </div>
      <Toggle label="Sandbox Mode" defaultOn />
      <Toggle label="Command Blacklist" defaultOn />
      <Toggle label="SSRF Protection" defaultOn />
      <Toggle label="Prompt Injection Detection" defaultOn />
    </div>
  );
}
