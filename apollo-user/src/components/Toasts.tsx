import { useAppStore } from "../store/app";

export function Toasts() {
  const toasts = useAppStore((s) => s.toasts);
  if (!toasts.length) return null;
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.type === "ok" ? "toast-ok" : t.type === "err" ? "toast-err" : ""}`}>
          {t.msg}
        </div>
      ))}
    </div>
  );
}
