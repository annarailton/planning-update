/**
 * Types for Temporal workflow interactions.
 */

export interface WorkflowStatusResponse {
  enabled: boolean;
  message: string;
  uiUrl?: string;
}

export interface StartWorkflowRequest {
  fileId?: string;
  bucketName?: string;
  userId?: string;
}

export interface StartWorkflowResponse {
  workflowId: string;
  message: string;
}

export interface WorkflowInfo {
  workflowId: string;
  status: WorkflowStatus | null;
  startTime: string | null;
  closeTime: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
}

export type WorkflowStatus =
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELED"
  | "TERMINATED"
  | "CONTINUED_AS_NEW"
  | "TIMED_OUT";

/**
 * SSE stream event for workflow updates.
 */
export interface WorkflowStreamEvent {
  event: "connected" | "progress" | "activity" | "complete" | "error";
  workflowId: string;
  status?: WorkflowStatus;
  progress?: number;
  message?: string;
  activity?: string;
  step?: number;
  totalSteps?: number;
  result?: Record<string, unknown>;
  error?: string;
}

/**
 * Result type for useWorkflowStream hook.
 */
export interface UseWorkflowStreamResult {
  status: WorkflowStatus | null;
  progress: number;
  message: string | null;
  activity: string | null;
  step: number | null;
  totalSteps: number | null;
  result: Record<string, unknown> | null;
  error: string | null;
  isComplete: boolean;
  isError: boolean;
  isLoading: boolean;
}
