import { useSSE } from "../../hooks/useSSE";
import { useChatStore } from "../../store/chat";

const SUGGESTIONS = [
  "Help me plan my day",
  "Search the web for latest AI news",
  "Write a Python script",
  "What can you do?",
];

export function ChatWelcome() {
  const { sendMessage } = useSSE();
  const addMessage = useChatStore((s) => s.addMessage);

  function handleSuggestion(text: string) {
    addMessage({ role: "user", content: text });
    sendMessage(text);
  }

  return (
    <div className="welcome-screen">
      <div className="welcome-logo">A</div>
      <div className="welcome-title">Aurora Neural Hub</div>
      <div className="welcome-subtitle">
        Your autonomous universal reasoning agent.<br />
        Ask anything, execute tasks, manage your digital life.
      </div>
      <div className="welcome-suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="suggestion-btn" onClick={() => handleSuggestion(s)}>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
