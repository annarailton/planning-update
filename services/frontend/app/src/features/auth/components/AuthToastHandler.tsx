import { ReactNode } from "react";
import { useAuthToasts } from "../hooks/useAuthToasts";
import { config } from "../../../shared/lib/config";

interface AuthToastHandlerProps {
  children: ReactNode;
}

/**
 * Wrapper component that handles authentication-related toast notifications.
 * Should be placed inside ClerkProvider but outside of routing.
 */
export function AuthToastHandler({ children }: AuthToastHandlerProps) {
  if (!config.isClerkConfigured) {
    return <>{children}</>;
  }

  // Initialize auth toasts
  useAuthToasts();

  return <>{children}</>;
}

export default AuthToastHandler;
