/**
 * Hook to poll workflow status.
 */

import { useState, useEffect, useCallback } from "react";
import { workflowService } from "../services/workflowService";
import type { WorkflowInfo, WorkflowStatus } from "../types/workflow.types";

interface UseWorkflowStatusOptions {
  pollInterval?: number;
  onComplete?: (result: Record<string, unknown> | null) => void;
  onError?: (error: string) => void;
}

export function useWorkflowStatus(
  workflowId: string,
  options: UseWorkflowStatusOptions = {},
) {
  const { pollInterval = 1000, onComplete, onError } = options;

  const [info, setInfo] = useState<WorkflowInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isTerminal = useCallback((status: WorkflowStatus | null): boolean => {
    if (!status) return false;
    return [
      "COMPLETED",
      "FAILED",
      "CANCELED",
      "TERMINATED",
      "TIMED_OUT",
    ].includes(status);
  }, []);

  useEffect(() => {
    let mounted = true;
    let timeoutId: ReturnType<typeof setTimeout>;

    const poll = async () => {
      if (!mounted) return;

      try {
        const result = await workflowService.getWorkflow(workflowId);
        if (!mounted) return;

        setInfo(result);
        setError(null);
        setIsLoading(false);

        // Call callbacks
        if (result.status === "COMPLETED" && onComplete) {
          onComplete(result.result);
        } else if (result.status === "FAILED" && onError) {
          onError(result.error || "Workflow failed");
        }

        // Continue polling if not terminal
        if (!isTerminal(result.status)) {
          timeoutId = setTimeout(poll, pollInterval);
        }
      } catch (err) {
        if (!mounted) return;
        const errorMessage =
          err instanceof Error ? err.message : "Failed to get workflow status";
        setError(errorMessage);
        setIsLoading(false);
        // Retry on error
        timeoutId = setTimeout(poll, pollInterval * 2);
      }
    };

    poll();

    return () => {
      mounted = false;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [workflowId, pollInterval, isTerminal, onComplete, onError]);

  return {
    info,
    status: info?.status ?? null,
    result: info?.result ?? null,
    isLoading,
    error,
    isComplete: info?.status === "COMPLETED",
    isFailed: info?.status === "FAILED",
    isRunning: info?.status === "RUNNING",
  };
}
