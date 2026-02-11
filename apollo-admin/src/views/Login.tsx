import { useState } from "react";
import { useAuthStore } from "../store/auth";
import { useAppStore } from "../store/app";
import { api } from "../api";

export function Login() {
  const [key, setKey] = useState("");
  const login = useAuthStore((s) => s.login);
  const toast = useAppStore((s) => s.toast);

  const handleLogin = async () => {
    if (!key.trim()) return;
    // Temporarily set key for the API call
    useAuthStore.setState({ adminKey: key.trim() });
    try {
      await api("GET", "/admin/status");
      login(key.trim());
    } catch {
      useAuthStore.setState({ adminKey: "" });
      toast("Admin Key 无效", "err");
    }
  };

  return (
    <div className="login-wrap">
      <div className="login-box">
        <div className="login-logo"><span>A</span></div>
        <div className="login-title">Apollo Gateway</div>
        <div className="login-sub">管理员控制台</div>
        <input
          className="login-input"
          type="password"
          placeholder="输入 Admin Key..."
          value={key}
          onChange={(e) => setKey(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleLogin()}
          autoFocus
        />
        <button className="login-btn" onClick={handleLogin}>登 录</button>
      </div>
    </div>
  );
}
