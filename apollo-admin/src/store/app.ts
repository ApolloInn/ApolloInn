import { create } from "zustand";

export type Tab = "overview" | "users" | "tokens" | "usage" | "models";

interface AppState {
  currentTab: Tab;
  setTab: (tab: Tab) => void;
  toasts: { id: number; msg: string; type: string }[];
  toast: (msg: string, type?: string) => void;
}

let toastId = 0;

export const useAppStore = create<AppState>((set, get) => ({
  currentTab: "overview",
  setTab: (tab) => set({ currentTab: tab }),
  toasts: [],
  toast: (msg, type = "") => {
    const id = ++toastId;
    set({ toasts: [...get().toasts, { id, msg, type }] });
    setTimeout(() => set({ toasts: get().toasts.filter((t) => t.id !== id) }), 3000);
  },
}));
