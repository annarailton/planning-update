/**
 * Hook for subscribing to workflow updates via SSE.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/clerk-react";
import { config } from "../../../shared/lib/config";
import { logger } from "../../../shared/lib/logger";

const log = logger.create("WorkflowStream");
import type {
  WorkflowStatus,
  WorkflowStreamEvent,
  UseWorkflowStreamResult,
} from "../types/workflow.types";

interface UseWorkflowStreamOptions {
  /** Whether to auto-connect on mount */
  autoConnect?: boolean;
  /** Callback when workflow completes */
  onComplete?: (result: Record<string, unknown>) => void;
  /** Callback on error */
  onError?: (error: string) => void;
  /** Callback on progress update */
  onProgress?: (progress: number, message?: string) => void;
}

/**
 * Subscribe to real-time workflow updates via Server-Sent Events.
 *
 * This hook connects to the workflow SSE endpoint and receives
 * progress updates as the Temporal workflow executes activities.
 *
 * @param workflowId - The workflow ID to subscribe to
 * @param options - Optional callbacks and settings
 * @returns Workflow status, progress, and result
 *
 * @example
 * ```tsx
 * function WorkflowProgress({ workflowId }: { workflowId: string }) {
 *   const { status, progress, message, activity } = useWorkflowStream(workflowId, {
 *     onComplete: (result) => console.log('Done!', result),
 *     onError: (error) => console.error('Failed:', error),
 *   });
 *
 *   return (
 *     <div>
 *       <ProgressBar value={progress} />
 *       <span>{activity}: {message}</span>
 *     </div>
 *   );
 * }
 * ```
 */
export function useWorkflowStream(
  workflowId: string | null,
  options: UseWorkflowStreamOptions = {},
): UseWorkflowStreamResult {
  const { autoConnect = true, onComplete, onError, onProgress } = options;
  const { getToken } = useAuth();

  // Store callbacks in refs to avoid destabilizing connect()
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  const onProgressRef = useRef(onProgress);
  onCompleteRef.current = onComplete;
  onErrorRef.current = onError;
  onProgressRef.current = onProgress;

  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [activity, setActivity] = useState<string | null>(null);
  const [step, setStep] = useState<number | null>(null);
  const [totalSteps, setTotalSteps] = useState<number | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const connectionTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const reconnectCountRef = useRef(0);
  const isTerminalRef = useRef(false); // Track if workflow reached terminal state

  const MAX_RECONNECT_ATTEMPTS = 5;
  const CONNECTION_TIMEOUT_MS = 30000; // 30 seconds - if no message received, reconnect

  const isTerminalStatus = (s: WorkflowStatus | undefined): boolean => {
    if (!s) return false;
    return [
      "COMPLETED",
      "FAILED",
      "CANCELED",
      "TERMINATED",
      "TIMED_OUT",
    ].includes(s);
  };

  const safeJsonParse = (data: string): WorkflowStreamEvent | null => {
    try {
      return JSON.parse(data);
    } catch (e) {
      log.error("Failed to parse SSE event data:", e);
      return null;
    }
  };

  // Reset connection timeout whenever we receive a message
  const resetConnectionTimeout = useCallback(() => {
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
    }
    // Only set timeout if not in terminal state
    if (!isTerminalRef.current) {
      connectionTimeoutRef.current = setTimeout(() => {
        log.warn("SSE connection timeout - no message received, reconnecting");
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          // Trigger reconnection via onerror handler
        }
      }, CONNECTION_TIMEOUT_MS);
    }
  }, []);

  const connect = useCallback(async () => {
    // Don't reconnect if workflow already completed/failed
    if (isTerminalRef.current) return;
    if (!workflowId) return;

    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    try {
      // Get auth token for the request
      const token = await getToken();
      if (!token) {
        setError("Authentication required");
        return;
      }

      // Build SSE URL with auth
      const url = `${config.backendUrl}/api/workflows/${workflowId}/stream`;

      // Note: EventSource doesn't support custom headers natively
      // Using query param for auth (standard pattern for SSE)
      const eventSource = new EventSource(
        `${url}?token=${encodeURIComponent(token)}`,
      );
      eventSourceRef.current = eventSource;

      eventSource.addEventListener("connected", (event) => {
        const data = safeJsonParse((event as MessageEvent).data);
        if (!data) return;
        reconnectCountRef.current = 0; // Reset retry count on successful connection
        resetConnectionTimeout(); // Start/reset connection timeout
        setStatus(data.status || "RUNNING");
        setProgress(data.progress || 0);
        // If workflow is already in terminal state, mark it
        if (isTerminalStatus(data.status)) {
          isTerminalRef.current = true;
          if (connectionTimeoutRef.current)
            clearTimeout(connectionTimeoutRef.current);
        }
      });

      eventSource.addEventListener("progress", (event) => {
        const data = safeJsonParse((event as MessageEvent).data);
        if (!data) return;
        resetConnectionTimeout(); // Reset timeout on activity
        setProgress(data.progress || 0);
        setMessage(data.message || null);
        setActivity(data.activity || null);
        if (data.step !== undefined) setStep(data.step);
        if (data.totalSteps !== undefined) setTotalSteps(data.totalSteps);
        setStatus("RUNNING");
        onProgressRef.current?.(data.progress || 0, data.message);
      });

      eventSource.addEventListener("activity", (event) => {
        const data = safeJsonParse((event as MessageEvent).data);
        if (!data) return;
        resetConnectionTimeout(); // Reset timeout on activity
        setActivity(data.activity || null);
        setMessage(data.message || null);
        if (data.step !== undefined) setStep(data.step);
        if (data.totalSteps !== undefined) setTotalSteps(data.totalSteps);
      });

      eventSource.addEventListener("complete", (event) => {
        const data = safeJsonParse((event as MessageEvent).data);
        if (!data) return;
        isTerminalRef.current = true; // Mark as terminal - don't reconnect
        if (connectionTimeoutRef.current)
          clearTimeout(connectionTimeoutRef.current);
        setStatus("COMPLETED");
        setProgress(100);
        setResult(data.result || null);
        setMessage("Workflow completed successfully");
        onCompleteRef.current?.(data.result || {});
        eventSource.close();
      });

      eventSource.addEventListener("error", (event) => {
        // Check if this is a custom error event or connection error
        if (event instanceof MessageEvent) {
          const data = safeJsonParse(event.data);
          if (!data) return;
          isTerminalRef.current = true; // Mark as terminal - don't reconnect
          if (connectionTimeoutRef.current)
            clearTimeout(connectionTimeoutRef.current);
          setStatus(data.status || "FAILED");
          setError(data.error || "Unknown error");
          setMessage(data.message || null);
          onErrorRef.current?.(data.error || "Unknown error");
          eventSource.close();
        } else {
          // Connection error - could be temporary
          log.error("SSE connection error");
          // Don't set error state immediately - might reconnect
        }
      });

      eventSource.onerror = () => {
        // Connection lost - try to reconnect after delay (only if not terminal)
        if (
          eventSource.readyState === EventSource.CLOSED &&
          !isTerminalRef.current
        ) {
          reconnectCountRef.current += 1;
          if (reconnectCountRef.current > MAX_RECONNECT_ATTEMPTS) {
            setError(
              `Connection failed after ${MAX_RECONNECT_ATTEMPTS} attempts`,
            );
            return;
          }
          // Exponential backoff: 1s, 2s, 4s, 8s, 16s
          const delay = Math.min(
            1000 * Math.pow(2, reconnectCountRef.current - 1),
            16000,
          );
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (err) {
      log.error("Failed to connect to workflow stream:", err);
      setError(err instanceof Error ? err.message : "Connection failed");
    }
  }, [workflowId, getToken, resetConnectionTimeout]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
      connectionTimeoutRef.current = null;
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && workflowId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, workflowId, connect, disconnect]);

  return {
    status,
    progress,
    message,
    activity,
    step,
    totalSteps,
    result,
    error,
    isComplete: status === "COMPLETED",
    isError:
      status === "FAILED" ||
      status === "CANCELED" ||
      status === "TERMINATED" ||
      status === "TIMED_OUT",
    isLoading: !status || status === "RUNNING",
  };
}
