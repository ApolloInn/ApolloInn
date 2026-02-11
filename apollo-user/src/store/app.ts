import { create } from "zustand";

interface AppState {
  toasts: { id: number; msg: string; type: string }[];
  toast: (msg: string, type?: string) => void;
}

let toastId = 0;

export const useAppStore = create<AppState>((set, get) => ({
  toasts: [],
  toast: (msg, type = "") => {
    const id = ++toastId;
    set({ toasts: [...get().toasts, { id, msg, type }] });
    setTimeout(() => set({ toasts: get().toasts.filter((t) => t.id !== id) }), 3000);
  },
}));
