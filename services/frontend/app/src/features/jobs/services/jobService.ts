/**
 * Job service for API interactions.
 */

import apiClient from "../../../shared/lib/api-client";
import type {
  CreateJobRequest,
  CreateJobResponse,
  Job,
} from "../types/job.types";

class JobService {
  /**
   * Create a new background job.
   */
  async createJob(request: CreateJobRequest): Promise<CreateJobResponse> {
    return apiClient.post<CreateJobResponse>("/jobs", request);
  }

  /**
   * Get job status and details.
   */
  async getJob(jobId: string): Promise<Job> {
    return apiClient.get<Job>(`/jobs/${jobId}`);
  }
}

export const jobService = new JobService();
