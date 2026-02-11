import { useRef, useCallback, type KeyboardEvent, type FormEvent } from "react";
import { useChatStore } from "../../store/chat";
import { useSSE } from "../../hooks/useSSE";

export function ChatComposer() {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sending = useChatStore((s) => s.sending);
  const addMessage = useChatStore((s) => s.addMessage);
  const updateSessionName = useChatStore((s) => s.updateSessionName);
  const currentSessionId = useChatStore((s) => s.currentSessionId);
  const sessions = useChatStore((s) => s.sessions);
  const { sendMessage } = useSSE();

  const handleSend = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    const text = el.value.trim();
    if (!text || sending) return;

    addMessage({ role: "user", content: text });

    // Update session name from first message
    const session = sessions.find((s) => s.id === currentSessionId);
    if (session && session.name === "New Conversation") {
      updateSessionName(currentSessionId, text.length > 30 ? text.slice(0, 30) + "..." : text);
    }

    sendMessage(text, currentSessionId);
    el.value = "";
    el.style.height = "auto";
  }, [sending, addMessage, sendMessage, currentSessionId, sessions, updateSessionName]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const handleInput = useCallback((e: FormEvent<HTMLTextAreaElement>) => {
    const el = e.currentTarget;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }, []);

  return (
    <div className="composer">
      <div className="composer-inner">
        <textarea
          ref={textareaRef}
          className="composer-input"
          placeholder="Initiate sequence or query system..."
          rows={1}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
        />
        <div className="composer-actions">
          <button className="composer-btn" title="Voice Input">
            <span className="material-symbols-rounded">mic</span>
          </button>
          <button
            className="composer-btn send-btn"
            disabled={sending}
            onClick={handleSend}
            title="Send"
          >
            <span className="material-symbols-rounded">arrow_upward</span>
          </button>
        </div>
      </div>
      <div className="composer-hint">Enter to send · Shift+Enter for new line · Cmd+B toggle sidebar</div>
    </div>
  );
}
