import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import type { ChatMessage as ChatMessageType } from "../../store/chat";

function formatTime(ts: number) {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const { role, content, timestamp } = message;
  const sender = role === "aurora" ? "Aurora Core" : role === "user" ? "Operator" : "";
  const time = formatTime(timestamp);

  if (role === "system") {
    return (
      <div className="message system">
        <div className="message-bubble">{content}</div>
      </div>
    );
  }

  return (
    <div className={`message ${role}`}>
      <div className="message-bubble">
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
          {content}
        </ReactMarkdown>
      </div>
      <div className="message-meta">{sender} · {time}</div>
    </div>
  );
}
