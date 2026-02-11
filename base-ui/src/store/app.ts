import { create } from "zustand";

export type TabId = "chat" | "tasks" | "skills" | "settings";

interface AppState {
  currentTab: TabId;
  leftCollapsed: boolean;
  rightCollapsed: boolean;
  switchTab: (tab: TabId) => void;
  toggleLeft: () => void;
  toggleRight: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentTab: "chat",
  leftCollapsed: false,
  rightCollapsed: false,
  switchTab: (tab) => set({ currentTab: tab }),
  toggleLeft: () => set((s) => ({ leftCollapsed: !s.leftCollapsed })),
  toggleRight: () => set((s) => ({ rightCollapsed: !s.rightCollapsed })),
}));
