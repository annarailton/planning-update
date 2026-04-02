/**
 * Shared utilities for job status styling.
 */

import type { JobStatus } from "../types/job.types";

/**
 * Get background color class for progress bar based on job status.
 */
export function getStatusColor(status: JobStatus): string {
  switch (status) {
    case "completed":
      return "bg-green-500";
    case "failed":
      return "bg-red-500";
    case "running":
      return "bg-blue-500";
    default:
      return "bg-gray-400";
  }
}

/**
 * Get badge styling classes for status display.
 */
export function getStatusBadgeClasses(status: JobStatus): string {
  switch (status) {
    case "completed":
      return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    case "failed":
      return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    case "running":
      return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
    default:
      return "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400";
  }
}
