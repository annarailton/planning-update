/**
 * Centralized configuration for the frontend app.
 *
 * All environment variables should be read here with defaults.
 * This provides:
 * - Single source of truth for config
 * - Type safety
 * - Sensible defaults when env vars are missing
 *
 * Usage:
 *   import { config } from '@/shared/lib/config';
 *   console.log(config.logLevel);
 */

type LogLevel = "debug" | "info" | "warn" | "error" | "silent";

interface AppConfig {
  // Environment
  isDev: boolean;
  isProd: boolean;
  nodeEnv: string;

  // API
  backendUrl: string;

  // Auth
  clerkPublishableKey: string;
  isClerkConfigured: boolean;

  // Feature flags
  debug: boolean;

  // Logging
  logLevel: LogLevel;
}

function getEnv(key: string, defaultValue: string = ""): string {
  return import.meta.env[key] ?? defaultValue;
}

function getBoolEnv(key: string, defaultValue: boolean): boolean {
  const value = import.meta.env[key];
  if (value === undefined) return defaultValue;
  return value === "true" || value === "1";
}

function getLogLevel(): LogLevel {
  const level = getEnv("VITE_LOG_LEVEL");
  const validLevels: LogLevel[] = ["debug", "info", "warn", "error", "silent"];

  if (validLevels.includes(level as LogLevel)) {
    return level as LogLevel;
  }

  // Default: debug in dev, error in prod
  return import.meta.env.DEV ? "debug" : "error";
}

function isConfiguredClerkKey(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) {
    return false;
  }

  return trimmed !== "pk_test_your_clerk_publishable_key_here";
}

export const config: AppConfig = {
  // Environment
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
  nodeEnv: getEnv("NODE_ENV", "development"),

  // API - empty string means use relative URLs (Vite proxy in dev)
  backendUrl: getEnv("VITE_BACKEND_URL", ""),

  // Auth
  clerkPublishableKey: getEnv("VITE_CLERK_PUBLISHABLE_KEY", ""),
  isClerkConfigured: isConfiguredClerkKey(
    getEnv("VITE_CLERK_PUBLISHABLE_KEY", ""),
  ),

  // Feature flags
  debug: getBoolEnv("VITE_DEBUG", import.meta.env.DEV),

  // Logging
  logLevel: getLogLevel(),
};

export default config;
