/**
 * Hook to check Temporal status.
 */

import { useState, useEffect, useRef } from "react";
import { workflowService } from "../services/workflowService";
import type { WorkflowStatusResponse } from "../types/workflow.types";

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

export function useTemporalStatus() {
  const [status, setStatus] = useState<WorkflowStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const retryCountRef = useRef(0);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const result = await workflowService.getStatus();
        setStatus(result);
        setError(null);
        retryCountRef.current = 0;
      } catch (err) {
        // Retry on 429 (rate limit) or 503 (cold start)
        const is429or503 =
          err instanceof Error &&
          (err.message.includes("429") || err.message.includes("503"));

        if (is429or503 && retryCountRef.current < MAX_RETRIES) {
          retryCountRef.current += 1;
          const delay = RETRY_DELAY_MS * Math.pow(2, retryCountRef.current - 1);
          setTimeout(checkStatus, delay);
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Failed to check Temporal status",
        );
        setStatus({ enabled: false, message: "Failed to connect" });
      } finally {
        if (
          retryCountRef.current === 0 ||
          retryCountRef.current >= MAX_RETRIES
        ) {
          setIsLoading(false);
        }
      }
    };

    checkStatus();
  }, []);

  return { status, isLoading, error, isEnabled: status?.enabled ?? false };
}
