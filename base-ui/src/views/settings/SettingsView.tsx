import { useSettingsStore } from "../../store/settings";
import { ApiKeysPanel } from "./panels/ApiKeysPanel";
import { ModelsPanel } from "./panels/ModelsPanel";
import { PersonalityPanel } from "./panels/PersonalityPanel";
import { MemoryPanel } from "./panels/MemoryPanel";
import { LogsPanel } from "./panels/LogsPanel";
import { SecurityPanel } from "./panels/SecurityPanel";

export function SettingsView() {
  const panel = useSettingsStore((s) => s.activePanel);

  return (
    <>
      <div className="chat-header">
        <div className="chat-header-left">
          <span className="material-symbols-rounded" style={{ color: "var(--color-primary)" }}>settings</span>
          <span className="chat-header-title">System Configuration</span>
        </div>
      </div>

      <div className="settings-panel">
        {panel === "apikeys" && <ApiKeysPanel />}
        {panel === "models" && <ModelsPanel />}
        {panel === "personality" && <PersonalityPanel />}
        {panel === "memory" && <MemoryPanel />}
        {panel === "logs" && <LogsPanel />}
        {panel === "security" && <SecurityPanel />}
      </div>
    </>
  );
}
