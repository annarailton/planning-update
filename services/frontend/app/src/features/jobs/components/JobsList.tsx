/**
 * JobsList - displays a list of active jobs with real-time tracking.
 */

import { AnimatePresence } from "motion/react";
import { JobTracker } from "./JobTracker";

interface JobEntry {
  id: string;
  type: string;
  startedAt: Date;
}

interface JobsListProps {
  jobs: JobEntry[];
}

export function JobsList({ jobs }: JobsListProps) {
  return (
    <div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Jobs ({jobs.length})
      </h3>

      {jobs.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-4">
          <AnimatePresence mode="popLayout">
            {jobs.map((job) => (
              <JobTracker key={job.id} jobId={job.id} jobType={job.type} />
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
        No jobs yet. Start one above to see real-time progress!
      </p>
    </div>
  );
}

export type { JobEntry };
