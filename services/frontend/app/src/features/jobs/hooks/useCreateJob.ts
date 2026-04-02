/**
 * Hook for creating background jobs.
 */

import { useCallback, useState } from "react";
import { jobService } from "../services/jobService";
import type { CreateJobRequest, CreateJobResponse } from "../types/job.types";

interface UseCreateJobResult {
  createJob: (request: CreateJobRequest) => Promise<CreateJobResponse>;
  isLoading: boolean;
  error: string | null;
  lastJob: CreateJobResponse | null;
}

/**
 * Create background jobs.
 *
 * @example
 * ```tsx
 * function ProcessButton({ fileId }: { fileId: string }) {
 *   const { createJob, isLoading, lastJob } = useCreateJob();
 *
 *   const handleClick = async () => {
 *     const response = await createJob({
 *       jobType: 'process_file',
 *       payload: { fileId },
 *     });
 *     console.log('Job created:', response.jobId);
 *   };
 *
 *   return (
 *     <button onClick={handleClick} disabled={isLoading}>
 *       Process File
 *     </button>
 *   );
 * }
 * ```
 */
export function useCreateJob(): UseCreateJobResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastJob, setLastJob] = useState<CreateJobResponse | null>(null);

  const createJob = useCallback(
    async (request: CreateJobRequest): Promise<CreateJobResponse> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await jobService.createJob(request);
        setLastJob(response);
        return response;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to create job";
        setError(errorMessage);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return {
    createJob,
    isLoading,
    error,
    lastJob,
  };
}
