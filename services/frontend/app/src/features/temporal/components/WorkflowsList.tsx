/**
 * WorkflowsList - displays a list of active workflows with status tracking.
 */

import { AnimatePresence } from "motion/react";
import { WorkflowTracker } from "./WorkflowTracker";

interface WorkflowEntry {
  id: string;
  startedAt: Date;
}

interface WorkflowsListProps {
  workflows: WorkflowEntry[];
  temporalUiBaseUrl?: string;
}

export function WorkflowsList({
  workflows,
  temporalUiBaseUrl,
}: WorkflowsListProps) {
  return (
    <div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Workflows ({workflows.length})
      </h3>

      {workflows.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-4">
          <AnimatePresence mode="popLayout">
            {workflows.map((workflow) => (
              <WorkflowTracker
                key={workflow.id}
                workflowId={workflow.id}
                temporalUiBaseUrl={temporalUiBaseUrl}
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-dashed border-gray-300 dark:border-gray-700">
      <p className="text-gray-500 dark:text-gray-400">
        No workflows yet. Start one above to see Temporal in action!
      </p>
    </div>
  );
}

export type { WorkflowEntry };
