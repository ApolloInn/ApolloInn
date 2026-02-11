import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ChatMessage {
  id: string;
  role: "user" | "aurora" | "system";
  content: string;
  timestamp: number;
}

export interface ToolEvent {
  id: string;
  name: string;
  status: "calling" | "success" | "error";
  timestamp: number;
}

export interface Session {
  id: string;
  name: string;
  messages: ChatMessage[];
  toolEvents: ToolEvent[];
  createdAt: number;
}

interface ChatState {
  sessions: Session[];
  currentSessionId: string;
  sending: boolean;
  typing: boolean;
  streamText: string;

  currentSession: () => Session | undefined;
  createSession: () => void;
  selectSession: (id: string) => void;
  addMessage: (msg: Omit<ChatMessage, "id" | "timestamp">) => void;
  addToolEvent: (evt: Omit<ToolEvent, "id" | "timestamp">) => void;
  setSending: (v: boolean) => void;
  setTyping: (v: boolean) => void;
  setStreamText: (text: string) => void;
  appendStreamText: (chunk: string) => void;
  finalizeStream: (fullText?: string) => void;
  updateSessionName: (id: string, name: string) => void;
}

const makeId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

const defaultSession: Session = {
  id: "default",
  name: "New Conversation",
  messages: [],
  toolEvents: [],
  createdAt: Date.now(),
};

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [defaultSession],
      currentSessionId: "default",
      sending: false,
      typing: false,
      streamText: "",

      currentSession: () => get().sessions.find((s) => s.id === get().currentSessionId),

      createSession: () => {
        const id = makeId();
        const session: Session = { id, name: "New Conversation", messages: [], toolEvents: [], createdAt: Date.now() };
        set((s) => ({
          sessions: [session, ...s.sessions],
          currentSessionId: id,
          streamText: "",
          typing: false,
        }));
      },

      selectSession: (id) => set({ currentSessionId: id, streamText: "", typing: false }),

      addMessage: (msg) => {
        const fullMsg: ChatMessage = { ...msg, id: makeId(), timestamp: Date.now() };
        set((s) => ({
          sessions: s.sessions.map((sess) =>
            sess.id === s.currentSessionId
              ? { ...sess, messages: [...sess.messages, fullMsg] }
              : sess
          ),
        }));
      },

      addToolEvent: (evt) => {
        const full: ToolEvent = { ...evt, id: makeId(), timestamp: Date.now() };
        set((s) => ({
          sessions: s.sessions.map((sess) =>
            sess.id === s.currentSessionId
              ? { ...sess, toolEvents: [...sess.toolEvents, full] }
              : sess
          ),
        }));
      },

      setSending: (v) => set({ sending: v }),
      setTyping: (v) => set({ typing: v }),
      setStreamText: (text) => set({ streamText: text }),
      appendStreamText: (chunk) => set((s) => ({ streamText: s.streamText + chunk })),

      finalizeStream: (fullText) => {
        const text = fullText || get().streamText;
        if (text) {
          get().addMessage({ role: "aurora", content: text });
        }
        set({ streamText: "", typing: false, sending: false });
      },

      updateSessionName: (id, name) =>
        set((s) => ({
          sessions: s.sessions.map((sess) => (sess.id === id ? { ...sess, name } : sess)),
        })),
    }),
    {
      name: "aurora-chat",
      // 只持久化 sessions 和 currentSessionId，不存临时状态
      partialize: (state) => ({
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
      }),
    },
  ),
);
