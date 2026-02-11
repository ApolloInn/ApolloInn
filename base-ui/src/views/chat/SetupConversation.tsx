import { useState, useEffect, useRef, type ReactNode } from "react";
import { useOnboardingStore, PROVIDER_CATALOG } from "../../store/onboarding";
import type { ProviderInfo } from "../../store/onboarding";

/* ── 复用现有 message 样式的气泡 ── */
function Bubble({ children }: { children: ReactNode }) {
  return (
    <div className="message aurora" style={{ maxWidth: "88%", animation: "msgFadeIn 0.3s ease-out" }}>
      <div className="message-bubble">{children}</div>
      <div className="message-meta">Aurora Core · Setup</div>
    </div>
  );
}

function Reply({ text }: { text: string }) {
  return (
    <div className="message user" style={{ animation: "msgFadeIn 0.3s ease-out" }}>
      <div className="message-bubble">{text}</div>
      <div className="message-meta">Operator · Now</div>
    </div>
  );
}

/* ═══════════════════════════════════════════════
   主组件 — 对话式配置引导
   所有交互元素复用 welcome-suggestions / suggestion-btn
   ═══════════════════════════════════════════════ */

export function SetupConversation() {
  const step = useOnboardingStore((s) => s.step);
  const provider = useOnboardingStore((s) => s.selectedProvider);
  const apiKey = useOnboardingStore((s) => s.apiKey);
  const setApiKey = useOnboardingStore((s) => s.setApiKey);
  const apiKeyError = useOnboardingStore((s) => s.apiKeyError);
  const setApiKeyError = useOnboardingStore((s) => s.setApiKeyError);
  const validatingKey = useOnboardingStore((s) => s.validatingKey);
  const setValidatingKey = useOnboardingStore((s) => s.setValidatingKey);
  const selectedModels = useOnboardingStore((s) => s.selectedModels);
  const toggleModel = useOnboardingStore((s) => s.toggleModel);
  const selectProvider = useOnboardingStore((s) => s.selectProvider);
  const nextStep = useOnboardingStore((s) => s.nextStep);
  const setNeedsSetup = useOnboardingStore((s) => s.setNeedsSetup);
  const setSaving = useOnboardingStore((s) => s.setSaving);
  const reset = useOnboardingStore((s) => s.reset);
  const [done, setDone] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const providerInfo = PROVIDER_CATALOG.find((p) => p.id === provider);
  const isLocal = provider === "ollama";

  useEffect(() => { reset(); }, []); // eslint-disable-line
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [step, done]);

  // Auto-select recommended models when entering step 3
  useEffect(() => {
    if (step === 3 && providerInfo && selectedModels.length === 0) {
      for (const m of providerInfo.models) {
        if (m.recommended) toggleModel(m.id);
      }
    }
  }, [step]); // eslint-disable-line

  function handlePickProvider(id: string) {
    selectProvider(id);
    nextStep();
  }

  async function handleKeySubmit() {
    if (isLocal) { nextStep(); return; }
    if (!apiKey.trim()) return;
    setValidatingKey(true);
    setApiKeyError(null);
    try {
      const res = await fetch("/api/setup/test-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, apiKey }),
      });
      const data = await res.json();
      if (data.success) { nextStep(); }
      else { setApiKeyError(data.error ?? "API Key 验证失败"); }
    } catch { setApiKeyError("无法连接后端服务"); }
    finally { setValidatingKey(false); }
  }

  async function finishSetup() {
    setSaving(true);
    const state = useOnboardingStore.getState();
    try {
      const res = await fetch("/api/setup/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: state.selectedProvider,
          apiKey: state.selectedProvider === "ollama" ? undefined : state.apiKey,
          selectedModels: state.selectedModels,
          defaultModel: state.selectedModels[0],
        }),
      });
      const data = await res.json();
      if (data.success) {
        setDone(true);
        // 轮询后端就绪状态，就绪后切换到正常界面
        await pollUntilReady();
        setNeedsSetup(false);
      }
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
  }

  async function pollUntilReady() {
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      try {
        const res = await fetch("/api/setup/ready");
        const data = await res.json();
        if (data.ready) return;
      } catch { /* retry */ }
    }
    // 超时 30 秒仍未就绪，也切换（用户可手动刷新）
  }

  return (
    <div className="chat-messages">

      {/* ══════ Step 1: 选择提供方 ══════ */}
      {step === 1 && (
        <>
          <Bubble>
            <p><strong>你好！我是 AURORA</strong>，你的人工智能个人助理。</p>
            <p>在开始之前，请选择你的<strong>主要模型提供方</strong>：</p>
          </Bubble>
          <div className="welcome-suggestions" style={{ justifyContent: "flex-start", marginTop: 0, paddingLeft: 8, animation: "msgFadeIn 0.4s ease-out" }}>
            {PROVIDER_CATALOG.map((p) => (
              <button key={p.id} className="suggestion-btn" onClick={() => handlePickProvider(p.id)}>
                {p.name}
              </button>
            ))}
          </div>
        </>
      )}

      {/* ══════ Step 2: 输入 API Key ══════ */}
      {step >= 2 && providerInfo && (
        <>
          <Bubble>
            <p><strong>你好！我是 AURORA</strong>，你的人工智能个人助理。</p>
            <p>在开始之前，请选择你的<strong>主要模型提供方</strong>：</p>
          </Bubble>
          <Reply text={providerInfo.name} />
          <Bubble>
            {isLocal ? (
              <p>Ollama 本地模型无需 API Key，确认继续即可。</p>
            ) : (
              <>
                <p><strong>{providerInfo.name}</strong>，不错的选择！请输入你的 API Key：</p>
                <p style={{ fontSize: 11, color: "var(--color-secondary)", marginTop: 4 }}>
                  {providerInfo.apiKeyHint}
                </p>
              </>
            )}
          </Bubble>
          {step === 2 && (
            isLocal ? (
              <div style={{ paddingLeft: 8, animation: "msgFadeIn 0.4s ease-out" }}>
                <button className="suggestion-btn" onClick={handleKeySubmit}>
                  <span className="material-symbols-rounded" style={{ fontSize: 16, marginRight: 4 }}>check</span>
                  确认继续
                </button>
              </div>
            ) : (
              /* API Key 输入 — 复用 composer 风格 */
              <div className="composer" style={{ paddingTop: 8, paddingBottom: 8, animation: "msgFadeIn 0.4s ease-out" }}>
                <div className="composer-inner" style={{ maxWidth: 440 }}>
                  <input
                    className="composer-input"
                    type={showKey ? "text" : "password"}
                    placeholder={providerInfo.apiKeyPlaceholder}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleKeySubmit()}
                    autoComplete="off"
                    spellCheck={false}
                    style={{ fontFamily: "'SF Mono','Fira Code','Menlo',monospace", fontSize: 13 }}
                  />
                  <div className="composer-actions">
                    <button className="composer-btn" onClick={() => setShowKey(!showKey)} title={showKey ? "隐藏" : "显示"}>
                      <span className="material-symbols-rounded">{showKey ? "visibility_off" : "visibility"}</span>
                    </button>
                    <button
                      className="composer-btn send-btn"
                      disabled={!apiKey.trim() || validatingKey}
                      onClick={handleKeySubmit}
                      title="验证"
                    >
                      <span className="material-symbols-rounded">
                        {validatingKey ? "hourglass_top" : "arrow_upward"}
                      </span>
                    </button>
                  </div>
                </div>
                {apiKeyError && (
                  <div style={{ fontSize: 11, color: "var(--color-error)", marginTop: 6, paddingLeft: 20 }}>
                    {apiKeyError}
                  </div>
                )}
              </div>
            )
          )}
        </>
      )}

      {/* ══════ Step 3: 选择模型 ══════ */}
      {step >= 3 && providerInfo && !isLocal && (
        <>
          <Reply text="API Key 已验证通过 ✓" />
          <Bubble>
            <p>连接成功！选择 <strong>{providerInfo.name}</strong> 下你想启用的模型：</p>
          </Bubble>
          {!done && (
            <>
              {/* 模型选择 — 用 suggestion-btn 风格 */}
              <div className="welcome-suggestions" style={{ justifyContent: "flex-start", paddingLeft: 8, flexDirection: "column", alignItems: "flex-start", gap: 6, animation: "msgFadeIn 0.4s ease-out" }}>
                {providerInfo.models.map((m) => {
                  const on = selectedModels.includes(m.id);
                  return (
                    <button
                      key={m.id}
                      className="suggestion-btn"
                      onClick={() => toggleModel(m.id)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        width: "100%",
                        maxWidth: 440,
                        textAlign: "left",
                        borderColor: on ? "rgba(0,0,0,0.12)" : undefined,
                        background: on ? "var(--color-surface)" : undefined,
                        boxShadow: on
                          ? "0 2px 8px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)"
                          : undefined,
                      }}
                    >
                      <span className="material-symbols-rounded" style={{ fontSize: 18, color: on ? "var(--color-primary)" : "rgba(0,0,0,0.15)" }}>
                        {on ? "check_circle" : "radio_button_unchecked"}
                      </span>
                      <span style={{ flex: 1 }}>
                        <strong style={{ fontSize: 13 }}>{m.name}</strong>
                        <br />
                        <span style={{ fontSize: 11, color: "var(--color-secondary)" }}>{m.description}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
              {/* 确认按钮 */}
              <div style={{ paddingLeft: 8, marginTop: 8, display: "flex", alignItems: "center", gap: 12, animation: "msgFadeIn 0.5s ease-out" }}>
                <button
                  className="composer-btn send-btn"
                  disabled={selectedModels.length === 0}
                  onClick={finishSetup}
                  style={{ width: "auto", padding: "10px 20px", borderRadius: 14, gap: 6, fontSize: 12, fontWeight: 700, letterSpacing: "0.08em" }}
                >
                  <span className="material-symbols-rounded" style={{ fontSize: 16 }}>check</span>
                  完成配置
                </button>
                <span style={{ fontSize: 11, color: "var(--color-secondary)" }}>
                  已选 {selectedModels.length} / {providerInfo.models.length}
                </span>
              </div>
            </>
          )}
        </>
      )}

      {/* ══════ Done ══════ */}
      {done && (
        <Bubble>
          <p style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="typing-indicator" style={{ padding: "4px 8px", borderRadius: 12, display: "inline-flex", gap: 3 }}>
              <span /><span /><span />
            </span>
            配置完成！AURORA 正在初始化模型连接...
          </p>
        </Bubble>
      )}

      <div ref={endRef} />
    </div>
  );
}
