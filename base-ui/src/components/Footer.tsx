import { useConnectionStore } from "../store/connection";

export function Footer() {
  const { connected, latency } = useConnectionStore();

  return (
    <footer className="footer">
      <div className="footer-left">
        <span>
          <span className={`footer-dot ${connected ? "green" : "dark"}`} />
          Latency {connected && latency != null ? `${latency}ms` : "—"}
        </span>
        <span>
          <span className="footer-dot dark" />
          Secure Node
        </span>
      </div>
      <div>AURORA v0.4.0 · Systems Nominal</div>
    </footer>
  );
}
