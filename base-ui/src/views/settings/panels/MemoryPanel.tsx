import { Toggle } from "../../../components/Toggle";

export function MemoryPanel() {
  return (
    <>
      <div className="settings-section">
        <div className="settings-section-title">Memory Settings</div>
        <Toggle label="Auto-learn new information" defaultOn />
        <Toggle label="Remember sensitive info" />
      </div>

      <div className="settings-section">
        <div className="settings-section-title">Privacy Filters</div>
        <Toggle label="Mask phone numbers" defaultOn />
        <Toggle label="Mask email addresses" defaultOn />
        <Toggle label="Mask ID numbers" defaultOn />
        <Toggle label="Mask addresses" />
      </div>

      <div className="settings-section">
        <div className="settings-section-title">Memory Management</div>
        <div className="btn-row">
          <button className="settings-btn secondary">View All Memories</button>
          <button className="settings-btn secondary">Export Memories</button>
          <button className="settings-btn secondary danger">Clear All Memories</button>
        </div>
      </div>
    </>
  );
}
