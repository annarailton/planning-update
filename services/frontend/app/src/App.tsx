import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { lazy, Suspense } from "react";
import { ChatPage } from "./pages/ChatPage";
import { AgentPage } from "./pages/AgentPage";
import { RealtimeAgentPage } from "./pages/RealtimeAgentPage";
import HomePage from "./pages/HomePage";
import ComponentShowcasePage from "./pages/ComponentShowcasePage";
import { FileUploadPage } from "./pages/FileUploadPage";
import { LoginPage } from "./pages/LoginPage";
import ClerkProvider from "./shared/providers/ClerkProvider";
import ProtectedRoute from "./features/auth/components/ProtectedRoute";
import AuthToastHandler from "./features/auth/components/AuthToastHandler";
import AppLayout from "./shared/components/layout/AppLayout";
import useApiClient from "./shared/hooks/useApiClient";
import { ThemeProvider } from "./shared/providers/ThemeProvider";
import {
  FeaturesProvider,
  useFeatures,
} from "./shared/providers/FeaturesProvider";

// Lazy load feature-flagged pages
const JobsPage = lazy(() =>
  import("./pages/JobsPage").then((m) => ({ default: m.JobsPage })),
);
const TemporalJobPage = lazy(() => import("./pages/TemporalJobPage"));

function AppContent() {
  // Initialize API client with Clerk authentication
  useApiClient();
  const { isRedisEnabled, isTemporalEnabled } = useFeatures();

  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/components" element={<ComponentShowcasePage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/agent" element={<AgentPage />} />
            <Route path="/realtime" element={<RealtimeAgentPage />} />
            <Route path="/file-upload" element={<FileUploadPage />} />
            {/* Feature-flagged routes */}
            <Route
              path="/jobs"
              element={
                isRedisEnabled ? (
                  <Suspense fallback={<div className="p-6">Loading...</div>}>
                    <JobsPage />
                  </Suspense>
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="/temporal-job"
              element={
                isTemporalEnabled ? (
                  <Suspense fallback={<div className="p-6">Loading...</div>}>
                    <TemporalJobPage />
                  </Suspense>
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
          </Route>
        </Route>
      </Routes>
      <Toaster
        position="top-right"
        richColors
        closeButton
        toastOptions={{
          duration: 4000,
          style: {
            borderRadius: "12px",
            padding: "16px",
            fontSize: "14px",
          },
        }}
      />
    </BrowserRouter>
  );
}

function App() {
  return (
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
      <ClerkProvider>
        <AuthToastHandler>
          <FeaturesProvider>
            <AppContent />
          </FeaturesProvider>
        </AuthToastHandler>
      </ClerkProvider>
    </ThemeProvider>
  );
}

export default App;
