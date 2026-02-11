import { useEffect, useRef } from "react";
import { useChatStore } from "../../store/chat";
import { ChatMessage } from "./ChatMessage";
import { ToolEventBubble } from "./ToolEvent";
import { TypingIndicator } from "./TypingIndicator";
import { StreamingMessage } from "./StreamingMessage";
import type { ToolEvent } from "../../store/chat";

const TOOL_SCROLL_THRESHOLD = 3;

/** 连续工具事件：超过 3 个时变成固定高度滚动窗口 */
function ToolEventGroup({ events }: { events: ToolEvent[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // 新事件进来时自动滚到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  if (events.length <= TOOL_SCROLL_THRESHOLD) {
    return (
      <>
        {events.map((e) => (
          <ToolEventBubble key={e.id} event={e} />
        ))}
      </>
    );
  }

  return (
    <div className="tool-scroll-container" ref={scrollRef}>
      {events.map((e) => (
        <ToolEventBubble key={e.id} event={e} />
      ))}
      <div className="tool-scroll-header">
        <span className="material-symbols-rounded" style={{ fontSize: 14 }}>terminal</span>
        工具调用记录 ({events.length})
      </div>
    </div>
  );
}

export function ChatMessages() {
  const bottomRef = useRef<HTMLDivElement>(null);

  const session = useChatStore((s) => s.sessions.find((ss) => ss.id === s.currentSessionId));
  const typing = useChatStore((s) => s.typing);
  const streamText = useChatStore((s) => s.streamText);
  const messages = session?.messages ?? [];
  const toolEvents = session?.toolEvents ?? [];

  const items = [
    ...messages.map((m) => ({ type: "message" as const, data: m, ts: m.timestamp })),
    ...toolEvents.map((t) => ({ type: "tool" as const, data: t, ts: t.timestamp })),
  ].sort((a, b) => a.ts - b.ts);

  // 将连续的 tool 事件分组
  type DisplayItem =
    | { kind: "message"; data: typeof messages[0] }
    | { kind: "tool-group"; events: ToolEvent[] };

  const grouped: DisplayItem[] = [];
  for (const item of items) {
    if (item.type === "message") {
      grouped.push({ kind: "message", data: item.data });
    } else {
      const last = grouped[grouped.length - 1];
      if (last?.kind === "tool-group") {
        last.events.push(item.data);
      } else {
        grouped.push({ kind: "tool-group", events: [item.data] });
      }
    }
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [items.length, streamText, typing]);

  return (
    <div className="chat-messages">
      {grouped.map((item, idx) =>
        item.kind === "message" ? (
          <ChatMessage key={item.data.id} message={item.data} />
        ) : (
          <ToolEventGroup key={`tg-${idx}`} events={item.events} />
        )
      )}

      {streamText && <StreamingMessage text={streamText} />}
      {typing && !streamText && <TypingIndicator />}

      <div ref={bottomRef} />
    </div>
  );
}
