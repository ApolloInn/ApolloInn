import { useEffect } from "react";
import { useConnectionStore } from "../store/connection";

export function useHealthCheck(intervalMs = 30_000) {
  const { setConnected, setLatency } = useConnectionStore();

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;

    async function check() {
      try {
        const start = Date.now();
        const res = await fetch("/health");
        const ms = Date.now() - start;
        if (res.ok) {
          setConnected(true);
          setLatency(ms);
        } else {
          setConnected(false);
          setLatency(null);
        }
      } catch {
        setConnected(false);
        setLatency(null);
      }
    }

    // Initial check after a short delay
    const init = setTimeout(check, 500);
    timer = setInterval(check, intervalMs);

    return () => {
      clearTimeout(init);
      clearInterval(timer);
    };
  }, [intervalMs, setConnected, setLatency]);
}
