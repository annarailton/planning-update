/**
 * Hook for subscribing to job updates via SSE.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/clerk-react";
import type {
  JobStatus,
  JobStreamEvent,
  UseJobStreamResult,
} from "../types/job.types";

interface UseJobStreamOptions {
  /** Whether to auto-connect on mount */
  autoConnect?: boolean;
  /** Callback when job completes */
  onComplete?: (result: Record<string, unknown>) => void;
  /** Callback on error */
  onError?: (error: string) => void;
  /** Callback on progress update */
  onProgress?: (progress: number, message?: string) => void;
}

/**
 * Subscribe to real-time job updates via Server-Sent Events.
 *
 * @param jobId - The job ID to subscribe to
 * @param options - Optional callbacks and settings
 * @returns Job status, progress, and result
 *
 * @example
 * ```tsx
 * function JobProgress({ jobId }: { jobId: string }) {
 *   const { status, progress, result, error } = useJobStream(jobId, {
 *     onComplete: (result) => console.log('Done!', result),
 *     onError: (error) => console.error('Failed:', error),
 *   });
 *
 *   return (
 *     <div>
 *       <ProgressBar value={progress} />
 *       <span>{status}</span>
 *     </div>
 *   );
 * }
 * ```
 */
export function useJobStream(
  jobId: string | null,
  options: UseJobStreamOptions = {},
): UseJobStreamResult {
  const { autoConnect = true, onComplete, onError, onProgress } = options;
  const { getToken } = useAuth();

  // Store callbacks in refs to avoid destabilizing connect()
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  const onProgressRef = useRef(onProgress);
  onCompleteRef.current = onComplete;
  onErrorRef.current = onError;
  onProgressRef.current = onProgress;

  const [status, setStatus] = useState<JobStatus>("pending");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isTerminalRef = useRef(false); // Track if job reached terminal state

  const connect = useCallback(async () => {
    // Don't reconnect if job already completed/failed
    if (isTerminalRef.current) return;
    if (!jobId) return;

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

      // Build SSE URL with auth (use relative URL to go through proxy)
      const url = `/api/jobs/${jobId}/stream`;

      // Note: EventSource doesn't support custom headers natively
      // We'll use a workaround with fetch + ReadableStream for auth
      // For now, using query param (less secure but works with EventSource)
      const eventSource = new EventSource(
        `${url}?token=${encodeURIComponent(token)}`,
      );
      eventSourceRef.current = eventSource;

      eventSource.addEventListener("connected", (event) => {
        const data: JobStreamEvent = JSON.parse(event.data);
        setStatus(data.status || "pending");
        setProgress(data.progress || 0);
        // If job is already in terminal state, mark it
        if (data.status === "completed" || data.status === "failed") {
          isTerminalRef.current = true;
        }
      });

      eventSource.addEventListener("progress", (event) => {
        const data: JobStreamEvent = JSON.parse(event.data);
        setProgress(data.progress || 0);
        setMessage(data.message || null);
        setStatus("running");
        onProgressRef.current?.(data.progress || 0, data.message);
      });

      eventSource.addEventListener("complete", (event) => {
        const data: JobStreamEvent = JSON.parse(event.data);
        isTerminalRef.current = true; // Mark as terminal - don't reconnect
        setStatus("completed");
        setProgress(100);
        setResult(data.result || null);
        onCompleteRef.current?.(data.result || {});
        eventSource.close();
      });

      eventSource.addEventListener("error", (event) => {
        // Check if this is a custom error event or connection error
        if (event instanceof MessageEvent) {
          const data: JobStreamEvent = JSON.parse(event.data);
          isTerminalRef.current = true; // Mark as terminal - don't reconnect
          setStatus("failed");
          setError(data.error || "Unknown error");
          onErrorRef.current?.(data.error || "Unknown error");
          eventSource.close();
        } else {
          // Connection error - could be temporary
          console.error("SSE connection error");
          // Don't set error state immediately - might reconnect
        }
      });

      eventSource.onerror = () => {
        // Connection lost - try to reconnect after delay (only if not terminal)
        if (
          eventSource.readyState === EventSource.CLOSED &&
          !isTerminalRef.current
        ) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 3000);
        }
      };
    } catch (err) {
      console.error("Failed to connect to job stream:", err);
      setError(err instanceof Error ? err.message : "Connection failed");
    }
  }, [jobId, getToken]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && jobId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, jobId, connect, disconnect]);

  return {
    status,
    progress,
    message,
    result,
    error,
    isComplete: status === "completed",
    isError: status === "failed",
    isLoading: status === "pending" || status === "running",
  };
}
