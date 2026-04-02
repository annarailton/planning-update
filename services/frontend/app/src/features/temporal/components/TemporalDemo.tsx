/**
 * TemporalDemo - demonstrates Temporal workflow architecture.
 *
 * Similar to JobsDemo but for Temporal workflows:
 * - WorkflowCreator: Form for starting workflows
 * - WorkflowsList: Real-time workflow tracking with polling
 * - TemporalArchitecture: Visual explanation of the flow
 */

import { useState, useCallback } from "react";
import { WorkflowCreator } from "./WorkflowCreator";
import { WorkflowsList, type WorkflowEntry } from "./WorkflowsList";
import { TemporalArchitecture } from "./TemporalArchitecture";
import { useTemporalStatus } from "../hooks/useTemporalStatus";

export function TemporalDemo() {
  const [workflows, setWorkflows] = useState<WorkflowEntry[]>([]);
  const { status } = useTemporalStatus();

  const handleWorkflowCreated = useCallback((workflowId: string) => {
    setWorkflows((prev) => [
      {
        id: workflowId,
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
          Temporal Workflows Demo
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Test durable workflow execution with automatic retries, timeouts, and
          full visibility
        </p>
      </div>

      {/* Workflow Creation Controls */}
      <WorkflowCreator onWorkflowCreated={handleWorkflowCreated} />

      {/* Active Workflows List */}
      <WorkflowsList workflows={workflows} temporalUiBaseUrl={status?.uiUrl} />

      {/* Architecture Explanation */}
      <TemporalArchitecture />

      {/* Infrastructure Note */}
      <div className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <p className="font-medium text-gray-600 dark:text-gray-300 mb-2">
          Temporal Infrastructure
        </p>
        <div className="space-y-1">
          <p>
            <strong>Local:</strong> Temporal runs automatically with{" "}
            <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">
              pnpm dev
            </code>
            . UI at{" "}
            <a
              href="http://localhost:8233"
              target="_blank"
              rel="noopener noreferrer"
              className="text-purple-600 dark:text-purple-400 hover:underline"
            >
              localhost:8233
            </a>
          </p>
          <p>
            <strong>Production:</strong> Set{" "}
            <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">
              TEMPORAL_API_KEY
            </code>{" "}
            GitHub secret for Temporal Cloud.
          </p>
          <p>
            <strong>Workflows:</strong> Defined in{" "}
            <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">
              packages/temporal/workflows/
            </code>
          </p>
          <p>
            <strong>Activities:</strong> Defined in{" "}
            <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">
              packages/temporal/activities/
            </code>
          </p>
        </div>
      </div>
    </div>
  );
}
