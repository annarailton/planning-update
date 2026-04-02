/**
 * Hook to start a Temporal workflow.
 */

import { useState, useCallback } from "react";
import { workflowService } from "../services/workflowService";
import type {
  StartWorkflowRequest,
  StartWorkflowResponse,
} from "../types/workflow.types";

export function useStartWorkflow() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startWorkflow = useCallback(
    async (request: StartWorkflowRequest): Promise<StartWorkflowResponse> => {
      setIsLoading(true);
      setError(null);

      try {
        const response =
          await workflowService.startProcessFileWorkflow(request);
        return response;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to start workflow";
        setError(errorMessage);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return { startWorkflow, isLoading, error };
}
