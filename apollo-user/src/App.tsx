import { useEffect } from "react";
import { useAuthStore } from "./store/auth";
import { api } from "./api";
import { Login } from "./views/Login";
import { Dashboard } from "./views/Dashboard";
import { Toasts } from "./components/Toasts";
import { Modal } from "./components/Modal";

export function App() {
  const { isLoggedIn, token, login, logout } = useAuthStore();

  useEffect(() => {
    if (token && !isLoggedIn) {
      api("GET", "/user/me")
        .then((r) => login(token, r.name))
        .catch(() => logout());
    }
  }, []);

  if (!isLoggedIn) return <><Login /><Toasts /><Modal /></>;

  return (
    <>
      <Dashboard />
      <Toasts />
      <Modal />
    </>
  );
}
