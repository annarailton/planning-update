import type { AxiosRequestConfig } from "axios";
import apiClient from "../../../shared/lib/api-client";
import type {
  PlanningApplicationsQuery,
  PlanningApplicationsResponse,
} from "../types/planning.types";

class PlanningService {
  async listWeeklyApplications(
    query: PlanningApplicationsQuery,
    config?: AxiosRequestConfig,
  ): Promise<PlanningApplicationsResponse> {
    return apiClient.get<PlanningApplicationsResponse>("/planning-applications", {
      ...config,
      params: {
        ward: query.ward,
        week_beginning: query.weekBeginning,
        date_type: query.dateType,
      },
    });
  }
}

export const planningService = new PlanningService();
