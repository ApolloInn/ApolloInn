import { useState } from "react";
import { useAuthStore } from "../store/auth";
import { useAppStore } from "../store/app";
import { api } from "../api";

export function Login() {
  const [input, setInput] = useState("");
  const login = useAuthStore((s) => s.login);
  const toast = useAppStore((s) => s.toast);

  const handleLogin = async () => {
    if (!input.trim()) return;
    useAuthStore.setState({ token: input.trim() });
    try {
      const me = await api("GET", "/user/me");
      login(input.trim(), me.name);
    } catch {
      useAuthStore.setState({ token: "" });
      toast("Token 无效", "err");
    }
  };

  return (
    <div className="login-wrap">
      <div className="login-box">
        <div className="login-logo"><span>A</span></div>
        <div className="login-title">Apollo Gateway</div>
        <div className="login-sub">用户面板</div>
        <input
          className="login-input"
          type="password"
          placeholder="输入 apollo-xxx Token..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleLogin()}
          autoFocus
        />
        <button className="login-btn" onClick={handleLogin}>登 录</button>
      </div>
    </div>
  );
}
