import { create } from "zustand";

export type SettingsPanel = "apikeys" | "models" | "personality" | "style" | "memory" | "privacy" | "logs" | "security";

interface SettingsState {
  activePanel: SettingsPanel;
  setActivePanel: (panel: SettingsPanel) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  activePanel: "apikeys",
  setActivePanel: (panel) => set({ activePanel: panel }),
}));
