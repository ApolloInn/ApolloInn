import { useState } from "react";

export function Toggle({ label, defaultOn = false }: { label: string; defaultOn?: boolean }) {
  const [on, setOn] = useState(defaultOn);

  return (
    <div className="toggle-row">
      <span className="toggle-label">{label}</span>
      <button className={`toggle ${on ? "on" : ""}`} onClick={() => setOn(!on)} />
    </div>
  );
}
