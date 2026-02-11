import { useState } from "react";
import { Toggle } from "../../../components/Toggle";

export function PersonalityPanel() {
  const [formality, setFormality] = useState(5);
  const [detail, setDetail] = useState(7);
  const [humor, setHumor] = useState(4);

  return (
    <>
      <div className="settings-section">
        <div className="settings-section-title">Name Settings</div>
        <div className="settings-field">
          <label className="settings-label">How AURORA calls you</label>
          <input type="text" className="settings-input" placeholder="Your name or nickname" />
        </div>
        <div className="settings-field">
          <label className="settings-label">How you call AURORA</label>
          <input type="text" className="settings-input" defaultValue="Aurora" />
        </div>
      </div>

      <div className="settings-section">
        <div className="settings-section-title">Expression Style</div>
        <SliderField label="Formality" value={formality} onChange={setFormality} left="Casual" right="Formal" />
        <SliderField label="Detail Level" value={detail} onChange={setDetail} left="Concise" right="Detailed" />
        <SliderField label="Humor" value={humor} onChange={setHumor} left="Serious" right="Humorous" />
      </div>

      <div className="settings-section">
        <div className="settings-section-title">Proactive Behavior</div>
        <Toggle label="Proactive Reminders" defaultOn />
        <Toggle label="Proactive Caring" defaultOn />
        <Toggle label="Curiosity Driven" defaultOn />
      </div>

      <div className="btn-row">
        <button className="settings-btn">Save Settings</button>
        <button className="settings-btn secondary">Reset to Default</button>
      </div>
    </>
  );
}

function SliderField({ label, value, onChange, left, right }: {
  label: string; value: number; onChange: (v: number) => void; left: string; right: string;
}) {
  return (
    <div className="settings-field">
      <label className="settings-label">{label}: {value}</label>
      <input type="range" className="settings-slider" min={0} max={10} value={value} onChange={(e) => onChange(Number(e.target.value))} />
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "var(--color-secondary)" }}>
        <span>{left}</span><span>{right}</span>
      </div>
    </div>
  );
}
