import { useEffect } from "react";
import { useAuthStore } from "./store/auth";
import { useAppStore } from "./store/app";
import { api } from "./api";
import { Login } from "./views/Login";
import { Header } from "./components/Header";
import { Toasts } from "./components/Toasts";
import { Modal } from "./components/Modal";
import { OverviewView } from "./views/Overview";
import { UsersView } from "./views/Users";
import { TokensView } from "./views/Tokens";
import { UsageView } from "./views/Usage";
import { ModelsView } from "./views/Models";

export function App() {
  const { isLoggedIn, adminKey, login, logout } = useAuthStore();
  const tab = useAppStore((s) => s.currentTab);

  useEffect(() => {
    if (adminKey && !isLoggedIn) {
      api("GET", "/admin/status")
        .then(() => login(adminKey))
        .catch(() => logout());
    }
  }, []);

  if (!isLoggedIn) return <Login />;

  return (
    <>
      <Header />
      <main className="main-content">
        {tab === "overview" && <OverviewView />}
        {tab === "users" && <UsersView />}
        {tab === "tokens" && <TokensView />}
        {tab === "usage" && <UsageView />}
        {tab === "models" && <ModelsView />}
      </main>
      <Toasts />
      <Modal />
    </>
  );
}
