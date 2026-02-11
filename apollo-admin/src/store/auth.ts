import { create } from "zustand";

interface AuthState {
  adminKey: string;
  isLoggedIn: boolean;
  login: (key: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  adminKey: localStorage.getItem("apollo_admin_key") || "",
  isLoggedIn: false,
  login: (key) => {
    localStorage.setItem("apollo_admin_key", key);
    set({ adminKey: key, isLoggedIn: true });
  },
  logout: () => {
    localStorage.removeItem("apollo_admin_key");
    set({ adminKey: "", isLoggedIn: false });
  },
}));
