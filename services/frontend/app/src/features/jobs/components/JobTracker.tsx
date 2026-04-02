/**
 * JobTracker - displays real-time progress for a single job with SSE event log.
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { motion } from "motion/react";
import { CheckCircle, XCircle, Loader2, Radio } from "lucide-react";
import { useJobStream } from "../hooks/useJobStream";
import { cn } from "../../../shared/utils/cn";
import { getStatusColor, getStatusBadgeClasses } from "./jobStatusUtils";
import type { JobStatus } from "../types/job.types";

interface EventLogEntry {
  timestamp: Date;
  event: string;
  data: string;
}

interface JobTrackerProps {
  jobId: string;
  jobType: string;
}

function StatusIcon({ status }: { status: JobStatus }) {
  switch (status) {
    case "completed":
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    case "failed":
      return <XCircle className="w-5 h-5 text-red-500" />;
    case "running":
      return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
    default:
      return <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />;
  }
}

export function JobTracker({ jobId, jobType }: JobTrackerProps) {
  const [eventLog, setEventLog] = useState<EventLogEntry[]>([]);
  const hasLoggedConnection = useRef(false);

  const logEvent = useCallback((event: string, data: string) => {
    setEventLog((prev) => [...prev, { timestamp: new Date(), event, data }]);
  }, []);

  const { status, progress, message, result, error, isComplete, isError } =
    useJobStream(jobId, {
      onProgress: (p, msg) => {
        logEvent("progress", `${p}% - ${msg || "processing"}`);
      },
      onComplete: (res) => {
        logEvent("complete", JSON.stringify(res));
      },
      onError: (err) => {
        logEvent("error", err);
      },
    });

  // Log initial connection (only once)
  useEffect(() => {
    if (!hasLoggedConnection.current) {
      hasLoggedConnection.current = true;
      logEvent(
        "connected",
        `Subscribed to SSE stream for job ${jobId.slice(0, 8)}...`,
      );
    }
  }, [jobId, logEvent]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 shadow-sm"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <StatusIcon status={status} />
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {jobType}
          </span>
        </div>
        <span
          className={cn(
            "px-2 py-1 text-xs font-medium rounded-full",
            getStatusBadgeClasses(status),
          )}
        >
          {status}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-2">
        <motion.div
          className={cn("h-full rounded-full", getStatusColor(status))}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        />
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-500 dark:text-gray-400">
          {message ||
            (isComplete ? "Complete!" : isError ? error : "Processing...")}
        </span>
        <span className="font-mono text-gray-600 dark:text-gray-300">
          {progress}%
        </span>
      </div>

      {/* Result display */}
      {isComplete && result && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700"
        >
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
            Result:
          </p>
          <pre className="text-xs bg-gray-100 dark:bg-gray-950 p-2 rounded-lg overflow-auto max-h-32 text-gray-800 dark:text-gray-200">
            {JSON.stringify(result, null, 2)}
          </pre>
        </motion.div>
      )}

      {/* Error display */}
      {isError && error && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="mt-3 pt-3 border-t border-red-200 dark:border-red-800"
        >
          <p className="text-xs text-red-600 dark:text-red-400">
            Error: {error}
          </p>
        </motion.div>
      )}

      {/* Live Event Log */}
      <EventLog entries={eventLog} />

      <p className="text-xs text-gray-400 dark:text-gray-500 mt-2 font-mono">
        ID: {jobId}
      </p>
    </motion.div>
  );
}

function EventLog({ entries }: { entries: EventLogEntry[] }) {
  return (
    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-2 mb-2">
        <Radio className="w-3 h-3 text-green-500 animate-pulse" />
        <p className="text-xs font-medium text-gray-600 dark:text-gray-400">
          SSE Event Stream
        </p>
      </div>
      <div className="bg-gray-900 dark:bg-black rounded-lg p-2 font-mono text-xs max-h-32 overflow-auto">
        {entries.length === 0 ? (
          <span className="text-gray-500">Waiting for events...</span>
        ) : (
          entries.map((entry, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-gray-500 shrink-0">
                {entry.timestamp.toLocaleTimeString()}
              </span>
              <span
                className={cn(
                  "shrink-0",
                  entry.event === "connected" && "text-cyan-400",
                  entry.event === "progress" && "text-yellow-400",
                  entry.event === "complete" && "text-green-400",
                  entry.event === "error" && "text-red-400",
                )}
              >
                [{entry.event}]
              </span>
              <span className="text-gray-300 truncate">{entry.data}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
