/**
 * Workflow service for Temporal API interactions.
 */

import apiClient from "../../../shared/lib/api-client";
import type {
  WorkflowStatusResponse,
  StartWorkflowRequest,
  StartWorkflowResponse,
  WorkflowInfo,
} from "../types/workflow.types";

class WorkflowService {
  /**
   * Check if Temporal is enabled and connected.
   */
  async getStatus(): Promise<WorkflowStatusResponse> {
    return apiClient.get<WorkflowStatusResponse>("/workflows/status");
  }

  /**
   * Start a file processing workflow.
   */
  async startProcessFileWorkflow(
    request: StartWorkflowRequest,
  ): Promise<StartWorkflowResponse> {
    return apiClient.post<StartWorkflowResponse>(
      "/workflows/process-file",
      request,
    );
  }

  /**
   * Get workflow information and status.
   */
  async getWorkflow(workflowId: string): Promise<WorkflowInfo> {
    return apiClient.get<WorkflowInfo>(`/workflows/${workflowId}`);
  }
}

export const workflowService = new WorkflowService();
