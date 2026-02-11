import { useEffect } from "react";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { SidebarLeft } from "./components/SidebarLeft";
import { SidebarRight } from "./components/SidebarRight";
import { ChatView } from "./views/chat/ChatView";
import { TasksView } from "./views/tasks/TasksView";
import { SkillsView } from "./views/skills/SkillsView";
import { SettingsView } from "./views/settings/SettingsView";
import { useAppStore } from "./store/app";
import { useOnboardingStore } from "./store/onboarding";
import { useHealthCheck } from "./hooks/useHealth";

export function App() {
  const tab = useAppStore((s) => s.currentTab);
  const setNeedsSetup = useOnboardingStore((s) => s.setNeedsSetup);
  useHealthCheck();

  // Check if setup is needed on first load
  useEffect(() => {
    async function checkSetup() {
      try {
        const res = await fetch("/api/setup/status");
        if (res.ok) {
          const data = await res.json();
          setNeedsSetup(!data.configured);
        } else {
          setNeedsSetup(true);
        }
      } catch {
        setNeedsSetup(true);
      }
    }
    checkSetup();
  }, [setNeedsSetup]);

  // Always show normal UI — setup handled inside ChatView as a conversation
  return (
    <>
      <Header />
      <main className="main-layout">
        <SidebarLeft />
        <div className="main-center">
          {tab === "chat" && <ChatView />}
          {tab === "tasks" && <TasksView />}
          {tab === "skills" && <SkillsView />}
          {tab === "settings" && <SettingsView />}
        </div>
        <SidebarRight />
      </main>
      <Footer />
    </>
  );
}
