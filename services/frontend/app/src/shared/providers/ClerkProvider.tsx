import { ClerkProvider as ClerkReactProvider } from "@clerk/clerk-react";
import { ReactNode } from "react";
import { config } from "../lib/config";

interface ClerkProviderProps {
  children: ReactNode;
}

const PUBLISHABLE_KEY = config.clerkPublishableKey;

if (!config.isClerkConfigured) {
  console.warn(
    "Clerk is not configured. Local dev will run without authentication until a real VITE_CLERK_PUBLISHABLE_KEY is set.",
  );
}

export function ClerkProvider({ children }: ClerkProviderProps) {
  if (!config.isClerkConfigured) {
    // Return app without Clerk if key is not configured
    return <>{children}</>;
  }

  return (
    <ClerkReactProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">
      {children}
    </ClerkReactProvider>
  );
}

export default ClerkProvider;
