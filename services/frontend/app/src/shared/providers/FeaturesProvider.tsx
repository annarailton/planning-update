import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { logger } from "../lib/logger";

const log = logger.create("FeaturesProvider");

/**
 * Feature flags returned from the backend (categorized structure)
 */
export interface Features {
  infrastructure: {
    redis: boolean;
    worker: boolean;
    temporal: boolean;
  };
  llm: {
    openai: boolean;
    anthropic: boolean;
    gemini: boolean;
  };
  integrations: {
    langfuse: boolean;
  };
}

/**
 * Default features (all disabled) - used while loading
 */
const DEFAULT_FEATURES: Features = {
  infrastructure: {
    redis: false,
    worker: false,
    temporal: false,
  },
  llm: {
    openai: false,
    anthropic: false,
    gemini: false,
  },
  integrations: {
    langfuse: false,
  },
};

/**
 * Flat feature key for backwards compatibility and component filtering
 * Maps to the infrastructure category in Features
 */
export type FeatureKey = "redis" | "worker" | "temporal";

interface FeaturesContextValue {
  features: Features;
  loading: boolean;
  error: Error | null;
  // Infrastructure
  isRedisEnabled: boolean;
  isWorkerEnabled: boolean;
  isTemporalEnabled: boolean;
  // LLM providers
  hasOpenAI: boolean;
  hasAnthropic: boolean;
  hasGemini: boolean;
  // Integrations
  isLangfuseEnabled: boolean;
  /**
   * Check if a feature is enabled by key (for component filtering)
   * Supports flat keys like 'redis' which map to infrastructure.redis
   */
  isFeatureEnabled: (key: FeatureKey) => boolean;
}

const FeaturesContext = createContext<FeaturesContextValue | null>(null);

interface FeaturesProviderProps {
  children: ReactNode;
}

export function FeaturesProvider({ children }: FeaturesProviderProps) {
  const [features, setFeatures] = useState<Features>(DEFAULT_FEATURES);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const abortController = new AbortController();
    const maxWaitTime = 30000; // 30 seconds max wait
    const pollInterval = 500; // Check every 500ms

    async function waitForBackend(): Promise<boolean> {
      const startTime = Date.now();
      while (
        !abortController.signal.aborted &&
        Date.now() - startTime < maxWaitTime
      ) {
        try {
          const response = await fetch("/api/health", {
            signal: abortController.signal,
            cache: "no-store",
          });
          if (response.ok) {
            return true;
          }
        } catch {
          // If aborted, exit immediately
          if (abortController.signal.aborted) return false;
          // Otherwise silently ignore - backend not ready yet
        }
        await new Promise((r) => setTimeout(r, pollInterval));
      }
      return false;
    }

    async function loadFeatures() {
      // Wait for backend to be healthy first
      const backendReady = await waitForBackend();

      if (abortController.signal.aborted) return;

      if (!backendReady) {
        log.warn("Backend not available after timeout, using default features");
        setError(new Error("Backend not available"));
        setLoading(false);
        return;
      }

      // Backend is healthy, now fetch features with retry
      const maxRetries = 3;
      let lastError: Error | null = null;

      for (
        let attempt = 1;
        attempt <= maxRetries && !abortController.signal.aborted;
        attempt++
      ) {
        try {
          const response = await fetch("/api/features", {
            signal: abortController.signal,
          });
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          const data: Features = await response.json();
          if (!abortController.signal.aborted) {
            setFeatures(data);
            log.info("Features loaded", data);
            setLoading(false);
          }
          return; // Success
        } catch (err) {
          // If aborted, exit immediately
          if (abortController.signal.aborted) return;
          lastError =
            err instanceof Error ? err : new Error("Failed to load features");
          if (attempt < maxRetries) {
            log.debug(`Features fetch failed, retry ${attempt}/${maxRetries}`);
            await new Promise((r) => setTimeout(r, 500 * attempt)); // 500ms, 1s, 1.5s
          }
        }
      }

      // All retries failed
      if (!abortController.signal.aborted) {
        log.warn(
          "Failed to load features after retries, using defaults",
          lastError,
        );
        setError(lastError);
        setLoading(false);
      }
    }

    loadFeatures();

    return () => {
      abortController.abort();
    };
  }, []);

  // Helper to check if a feature is enabled by flat key
  const isFeatureEnabled = (key: FeatureKey): boolean => {
    return features.infrastructure[key] ?? false;
  };

  const value: FeaturesContextValue = {
    features,
    loading,
    error,
    // Infrastructure
    isRedisEnabled: features.infrastructure.redis,
    isWorkerEnabled: features.infrastructure.worker,
    isTemporalEnabled: features.infrastructure.temporal,
    // LLM providers
    hasOpenAI: features.llm.openai,
    hasAnthropic: features.llm.anthropic,
    hasGemini: features.llm.gemini,
    // Integrations
    isLangfuseEnabled: features.integrations.langfuse,
    // Helper
    isFeatureEnabled,
  };

  return (
    <FeaturesContext.Provider value={value}>
      {children}
    </FeaturesContext.Provider>
  );
}

/**
 * Hook to access feature flags from context
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useFeatures(): FeaturesContextValue {
  const context = useContext(FeaturesContext);
  if (!context) {
    throw new Error("useFeatures must be used within a FeaturesProvider");
  }
  return context;
}

/**
 * Clear the features cache (useful for testing)
 * Note: This doesn't affect the context state, only for backwards compatibility
 */
// eslint-disable-next-line react-refresh/only-export-components
export function clearFeaturesCache() {
  // No-op in context-based implementation
  // The context state is managed by React
}

export default FeaturesProvider;
