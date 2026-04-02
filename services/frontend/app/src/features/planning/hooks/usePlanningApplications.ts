import { useEffect, useState } from "react";
import { planningService } from "../services/planningService";
import type {
  PlanningApplicationsQuery,
  PlanningApplicationsResponse,
} from "../types/planning.types";
import { logger } from "../../../shared/lib/logger";

const log = logger.create("PlanningApplications");

const DEFAULT_QUERY: PlanningApplicationsQuery = {
  ward: "Hinksey Park",
};

interface UsePlanningApplicationsResult {
  data: PlanningApplicationsResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function usePlanningApplications(
  query: PlanningApplicationsQuery = DEFAULT_QUERY,
): UsePlanningApplicationsResult {
  const [data, setData] = useState<PlanningApplicationsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchApplications() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await planningService.listWeeklyApplications(query, {
          signal: controller.signal,
        });
        setData(response);
      } catch (err) {
        if (controller.signal.aborted) {
          return;
        }

        const errorMessage =
          err instanceof Error
            ? err.message
            : "Failed to load planning applications";
        log.error("Failed to fetch planning applications", err);
        setError(errorMessage);
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    fetchApplications();

    return () => {
      controller.abort();
    };
  }, [query]);

  return {
    data,
    isLoading,
    error,
  };
}
