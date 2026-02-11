import { create } from "zustand";

interface ConnectionState {
  connected: boolean;
  latency: number | null;
  setConnected: (v: boolean) => void;
  setLatency: (ms: number | null) => void;
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  connected: false,
  latency: null,
  setConnected: (v) => set({ connected: v }),
  setLatency: (ms) => set({ latency: ms }),
}));
