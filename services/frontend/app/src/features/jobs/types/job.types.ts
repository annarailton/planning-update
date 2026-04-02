/**
 * Job-related TypeScript types.
 */

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface Job {
  id: string;
  jobType: string;
  status: JobStatus;
  payload?: Record<string, unknown>;
  result?: Record<string, unknown>;
  errorMessage?: string;
  attempts: number;
  maxAttempts: number;
  createdAt: string;
  updatedAt: string;
}

export interface CreateJobRequest {
  jobType: string;
  payload?: Record<string, unknown>;
  priority?: number;
}

export interface CreateJobResponse {
  jobId: string;
  status: JobStatus;
  message: string;
}

export interface JobStreamEvent {
  event: "connected" | "progress" | "complete" | "error";
  jobId: string;
  progress?: number;
  message?: string;
  result?: Record<string, unknown>;
  error?: string;
  status?: JobStatus;
}

export interface UseJobStreamResult {
  status: JobStatus;
  progress: number;
  message: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  isComplete: boolean;
  isError: boolean;
  isLoading: boolean;
}
