import { ReactNode } from "react";
import { Outlet } from "react-router-dom";
import AppHeader from "./AppHeader";

interface AppLayoutProps {
  children?: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 transition-colors duration-300">
      <AppHeader />
      <main className="bg-gray-50 dark:bg-slate-950 pt-20">
        {children || <Outlet />}
      </main>
    </div>
  );
}
