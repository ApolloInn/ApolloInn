import type { ToolEvent } from "../../store/chat";

export function ToolEventBubble({ event }: { event: ToolEvent }) {
  const statusText = event.status === "calling" ? "Executing..." : event.status === "success" ? "Completed" : "Failed";

  return (
    <div className={`tool-event ${event.status === "success" ? "success" : event.status === "error" ? "error" : ""}`}>
      <span className="tool-name">{event.name}</span>
      {" — "}
      <span className={event.status === "success" ? "tool-status" : ""}>{statusText}</span>
    </div>
  );
}
