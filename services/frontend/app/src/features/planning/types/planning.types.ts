export type PlanningApplicationDateType = "validated" | "decided";

export interface PlanningFilterOption {
  value: string;
  label: string;
}

export interface PlanningApplicationSummary {
  applicationId: string;
  location: string;
  ward: string | null;
  summary: string;
  detailUrl: string;
}

export interface PlanningApplicationsFilters {
  ward: string | null;
  weekBeginning: string;
  dateType: PlanningApplicationDateType;
}

export interface PlanningApplicationsAvailableFilters {
  wards: PlanningFilterOption[];
  weeks: string[];
}

export interface PlanningApplicationsResponse {
  applications: PlanningApplicationSummary[];
  totalCount: number;
  filters: PlanningApplicationsFilters;
  availableFilters: PlanningApplicationsAvailableFilters;
}

export interface PlanningApplicationsQuery {
  ward?: string;
  weekBeginning?: string;
  dateType?: PlanningApplicationDateType;
}
