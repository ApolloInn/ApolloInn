import { useState } from "react";

export function ModelsPanel() {
  const [temp, setTemp] = useState(0.7);

  return (
    <>
      <div className="settings-section">
        <div className="settings-section-title">Model Selection</div>
        <div className="settings-field">
          <label className="settings-label">Primary Model</label>
          <select className="settings-select" defaultValue="Claude 3.5 Sonnet">
            <option>Claude 3.5 Sonnet</option>
            <option>Claude 3 Opus</option>
            <option>GPT-4o</option>
            <option>DeepSeek V3</option>
          </select>
        </div>
        <div className="settings-field">
          <label className="settings-label">Fallback Model</label>
          <select className="settings-select" defaultValue="GPT-4o-mini">
            <option>GPT-4o-mini</option>
            <option>Claude 3.5 Haiku</option>
            <option>DeepSeek V3</option>
          </select>
        </div>
      </div>
      <div className="settings-section">
        <div className="settings-section-title">Parameters</div>
        <div className="settings-field">
          <label className="settings-label">Temperature: {temp}</label>
          <input type="range" className="settings-slider" min={0} max={2} step={0.1} value={temp} onChange={(e) => setTemp(Number(e.target.value))} />
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "var(--color-secondary)", letterSpacing: "0.1em" }}>
            <span>Deterministic</span><span>Creative</span>
          </div>
        </div>
        <div className="settings-field">
          <label className="settings-label">Max Tokens</label>
          <input type="number" className="settings-input" defaultValue={4096} min={256} max={32768} />
        </div>
      </div>
      <div className="btn-row">
        <button className="settings-btn">Save Config</button>
        <button className="settings-btn secondary">Reset</button>
      </div>
    </>
  );
}
