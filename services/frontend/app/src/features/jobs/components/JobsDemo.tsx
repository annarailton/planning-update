/**
 * JobsDemo - demonstrates the worker architecture with real-time progress.
 *
 * Thin orchestration layer that composes:
 * - JobCreator: Forms for creating different job types
 * - JobsList: Real-time job tracking with SSE
 * - ArchitectureDiagram: Visual explanation of the flow
 */

import { useState, useCallback } from "react";
import { JobCreator } from "./JobCreator";
import { JobsList, type JobEntry } from "./JobsList";
import { ArchitectureDiagram } from "./ArchitectureDiagram";

export function JobsDemo() {
  const [jobs, setJobs] = useState<JobEntry[]>([]);

  const handleJobCreated = useCallback((jobId: string, jobType: string) => {
    setJobs((prev) => [
      {
        id: jobId,
        type: jobType,
        startedAt: new Date(),
      },
      ...prev,
    ]);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Background Jobs Demo
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Test the worker architecture with real-time progress streaming via
          Redis + SSE
        </p>
      </div>

      {/* Job Creation Controls */}
      <JobCreator onJobCreated={handleJobCreated} />

      {/* Active Jobs List */}
      <JobsList jobs={jobs} />

      {/* Architecture Explanation */}
      <ArchitectureDiagram />

      {/* Infrastructure Note */}
      <div className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <p className="font-medium text-gray-600 dark:text-gray-300 mb-1">
          Tomoro Infrastructure (Cloud Run)
        </p>
        <p>
          If deployed on Tomoro infrastructure, job timeout defaults to{" "}
          <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">
            15 min
          </code>{" "}
          (max{" "}
          <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">
            60 min
          </code>
          ).
        </p>
        <p className="mt-1">
          Configure via{" "}
          <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">
            terraform/services/worker/variables.tf
          </code>
        </p>
      </div>
    </div>
  );
}
