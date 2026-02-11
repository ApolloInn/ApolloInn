import { useChatStore } from "../../store/chat";
import { useOnboardingStore } from "../../store/onboarding";
import { ChatWelcome } from "./ChatWelcome";
import { ChatMessages } from "./ChatMessages";
import { ChatComposer } from "./ChatComposer";
import { SetupConversation } from "./SetupConversation";

export function ChatView() {
  const needsSetup = useOnboardingStore((s) => s.needsSetup);

  const messages = useChatStore((s) => {
    const sess = s.sessions.find((ss) => ss.id === s.currentSessionId);
    return sess?.messages ?? [];
  });

  const hasMessages = messages.length > 0;

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-header-left">
          <span className="material-symbols-rounded" style={{ color: "var(--color-primary)" }}>terminal</span>
          <span className="chat-header-title">System Interaction Log</span>
        </div>
      </div>

      {needsSetup ? (
        <SetupConversation />
      ) : hasMessages ? (
        <ChatMessages />
      ) : (
        <ChatWelcome />
      )}

      <ChatComposer />
    </div>
  );
}
