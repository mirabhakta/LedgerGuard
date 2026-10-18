import { Outlet } from "react-router-dom";

import { TopBar } from "./TopBar";
import { StreamBanner } from "./StatePanels";

export function AppShell() {
  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <TopBar />
      <StreamBanner />
      <main className="flex min-h-0 grow flex-col">
        <Outlet />
      </main>
    </div>
  );
}
