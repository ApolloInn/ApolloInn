import { create } from "zustand";

interface AuthState {
  token: string;
  isLoggedIn: boolean;
  userName: string;
  login: (token: string, name: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("apollo_user_token") || "",
  isLoggedIn: false,
  userName: "",
  login: (token, name) => {
    localStorage.setItem("apollo_user_token", token);
    set({ token, isLoggedIn: true, userName: name });
  },
  logout: () => {
    localStorage.removeItem("apollo_user_token");
    set({ token: "", isLoggedIn: false, userName: "" });
  },
}));
