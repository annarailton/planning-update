import { useAuth } from "@clerk/clerk-react";
import { ReactNode } from "react";
import { Outlet } from "react-router-dom";
import { motion } from "motion/react";
import LandingPage from "../../../pages/LandingPage";

interface ProtectedRouteProps {
  children?: ReactNode;
  fallback?: ReactNode;
}

export default function ProtectedRoute({
  children,
  fallback,
}: ProtectedRouteProps) {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
        <motion.div
          className="fixed top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 z-50"
          initial={{ scaleX: 0, transformOrigin: "left" }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 2, ease: "easeInOut", repeat: Infinity }}
        />
      </div>
    );
  }

  if (!isSignedIn) {
    return fallback || <LandingPage />;
  }

  return children || <Outlet />;
}
