/**
 * Setup Page — 用户首次打开时的配置页面。
 *
 * 这个文件会被注入到 9router 的初始化流程中。
 * 用户只需填写 usertoken，其他全部自动完成。
 */

"use client";

import { useState, useEffect } from "react";
import { autoSetup } from "./auto-setup";

// 默认网关地址（部署时替换）
const DEFAULT_GATEWAY_URL = "https://gw.example.com";

export default function SetupPage({ onComplete }) {
  const [usertoken, setUsertoken] = useState("");
  const [gatewayUrl, setGatewayUrl] = useState(DEFAULT_GATEWAY_URL);
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [error, setError] = useState("");

  // 检查是否已配置
  useEffect(() => {
    const saved = localStorage.getItem("kiro_usertoken");
    if (saved) {
      setUsertoken(saved);
      // 已配置过，直接跳过
      onComplete?.();
    }
  }, [onComplete]);

  const handleSetup = async () => {
    if (!usertoken.trim()) {
      setError("请输入 UserToken");
      return;
    }

    setStatus("loading");
    setError("");

    const result = await autoSetup(
      window.location.origin,
      gatewayUrl,
      usertoken.trim()
    );

    if (result.success) {
      localStorage.setItem("kiro_usertoken", usertoken.trim());
      localStorage.setItem("kiro_gateway_url", gatewayUrl);
      setStatus("success");
      setTimeout(() => onComplete?.(), 1500);
    } else {
      setStatus("error");
      setError(result.error || "配置失败");
    }
  };

  if (status === "success") {
    return (
      <div style={{ textAlign: "center", padding: "100px 20px" }}>
        <h2>✅ 配置完成</h2>
        <p style={{ color: "#8b949e", marginTop: 8 }}>正在跳转...</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 420, margin: "80px auto", padding: 20 }}>
      <h2 style={{ marginBottom: 8 }}>🔧 初始配置</h2>
      <p style={{ color: "#8b949e", fontSize: 14, marginBottom: 24 }}>
        输入管理员给你的 UserToken，其他配置会自动完成。
      </p>

      <label style={{ fontSize: 13, color: "#8b949e" }}>网关地址</label>
      <input
        value={gatewayUrl}
        onChange={(e) => setGatewayUrl(e.target.value)}
        placeholder="https://gw.example.com"
        style={{
          width: "100%", padding: "8px 12px", marginBottom: 12,
          background: "#0d1117", border: "1px solid #30363d",
          borderRadius: 6, color: "#e1e4e8", fontFamily: "monospace",
        }}
      />

      <label style={{ fontSize: 13, color: "#8b949e" }}>UserToken</label>
      <input
        value={usertoken}
        onChange={(e) => setUsertoken(e.target.value)}
        placeholder="sk-xxxx"
        type="password"
        style={{
          width: "100%", padding: "8px 12px", marginBottom: 16,
          background: "#0d1117", border: "1px solid #30363d",
          borderRadius: 6, color: "#e1e4e8", fontFamily: "monospace",
        }}
      />

      {error && (
        <p style={{ color: "#f85149", fontSize: 13, marginBottom: 12 }}>{error}</p>
      )}

      <button
        onClick={handleSetup}
        disabled={status === "loading"}
        style={{
          width: "100%", padding: "10px", border: "none",
          borderRadius: 6, background: "#238636", color: "#fff",
          fontSize: 14, fontWeight: 500, cursor: "pointer",
        }}
      >
        {status === "loading" ? "配置中..." : "开始配置"}
      </button>

      <p style={{ color: "#484f58", fontSize: 12, marginTop: 16, textAlign: "center" }}>
        配置完成后，使用 9router 公网地址 + 你的 API Key + 模型名即可调用
      </p>
    </div>
  );
}
