import { useCallback } from "react";
import { useChatStore } from "../store/chat";

export function useSSE() {
  const { setSending, setTyping, appendStreamText, setStreamText, addToolEvent } =
    useChatStore.getState();

  const sendMessage = useCallback(async (text: string, sessionId?: string) => {
    setSending(true);
    setTyping(true);
    setStreamText("");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, sessionId }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();
          if (data === "[DONE]") continue;

          try {
            const chunk = JSON.parse(data);

            switch (chunk.type) {
              case "text":
                setTyping(false);
                appendStreamText(chunk.text);
                break;

              case "tool_call":
                // 工具调用前：先把已积累的文本保存为消息
                saveCurrentStream();
                addToolEvent({ name: chunk.name, status: "calling" });
                break;

              case "tool_result":
                addToolEvent({ name: chunk.name || "tool", status: chunk.result?.startsWith("✓") ? "success" : "error" });
                break;

              case "message_break":
                // 消息边界：把当前文本保存为独立消息，后续文本作为新消息
                saveCurrentStream();
                setTyping(true);
                break;

              case "done":
                // 保存最后剩余的 streamText（不用 fullResponse，避免重复）
                saveCurrentStream();
                setSending(false);
                setTyping(false);
                return;

              case "error":
                setTyping(false);
                useChatStore.getState().addMessage({ role: "system", content: `Error: ${chunk.message}` });
                setSending(false);
                return;
            }
          } catch {
            // ignore malformed JSON chunks
          }
        }
      }

      // Stream ended without explicit 'done' event
      saveCurrentStream();
      setSending(false);
      setTyping(false);
    } catch (err) {
      setTyping(false);
      setSending(false);
      useChatStore.getState().addMessage({
        role: "system",
        content: `Connection error: ${err instanceof Error ? err.message : "Unknown error"}`,
      });
    }
  }, []);

  return { sendMessage };
}

/** 把当前 streamText 保存为一条 aurora 消息，然后清空 streamText */
function saveCurrentStream() {
  const state = useChatStore.getState();
  const text = state.streamText;
  if (text.trim()) {
    state.addMessage({ role: "aurora", content: text });
    state.setStreamText("");
  }
}
