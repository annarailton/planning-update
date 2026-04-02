/**
 * WorkflowTracker - displays status for a single Temporal workflow with SSE streaming.
 */

import { useState, useCallback, useEffect } from "react";
import { motion } from "motion/react";
import {
  CheckCircle,
  XCircle,
  Loader2,
  Clock,
  ExternalLink,
  Radio,
} from "lucide-react";
import { useWorkflowStream } from "../hooks/useWorkflowStream";
import { cn } from "../../../shared/utils/cn";
import type { WorkflowStatus } from "../types/workflow.types";

interface EventLogEntry {
  timestamp: Date;
  event: string;
  data: string;
}

interface WorkflowTrackerProps {
  workflowId: string;
  temporalUiBaseUrl?: string;
}

function StatusIcon({ status }: { status: WorkflowStatus | null }) {
  switch (status) {
    case "COMPLETED":
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    case "FAILED":
    case "CANCELED":
    case "TERMINATED":
    case "TIMED_OUT":
      return <XCircle className="w-5 h-5 text-red-500" />;
    case "RUNNING":
      return <Loader2 className="w-5 h-5 text-purple-500 animate-spin" />;
    default:
      return <Clock className="w-5 h-5 text-gray-400" />;
  }
}

function getStatusColor(status: WorkflowStatus | null): string {
  switch (status) {
    case "COMPLETED":
      return "bg-green-500";
    case "FAILED":
    case "CANCELED":
    case "TERMINATED":
    case "TIMED_OUT":
      return "bg-red-500";
    case "RUNNING":
      return "bg-purple-500";
    default:
      return "bg-gray-400";
  }
}

function getStatusBadgeClasses(status: WorkflowStatus | null): string {
  switch (status) {
    case "COMPLETED":
      return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    case "FAILED":
    case "CANCELED":
    case "TERMINATED":
    case "TIMED_OUT":
      return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    case "RUNNING":
      return "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400";
    default:
      return "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400";
  }
}

export function WorkflowTracker({
  workflowId,
  temporalUiBaseUrl,
}: WorkflowTrackerProps) {
  const [eventLog, setEventLog] = useState<EventLogEntry[]>([]);

  const logEvent = useCallback((event: string, data: string) => {
    setEventLog((prev) => [...prev, { timestamp: new Date(), event, data }]);
  }, []);

  const {
    status,
    progress,
    message,
    activity,
    step,
    totalSteps,
    result,
    error,
    isComplete,
    isError,
    isLoading,
  } = useWorkflowStream(workflowId, {
    onComplete: (res) => {
      logEvent("complete", JSON.stringify(res));
    },
    onError: (err) => {
      logEvent("error", err);
    },
    onProgress: (prog, msg) => {
      logEvent("progress", `${prog}% - ${msg || ""}`);
    },
  });

  // Log status changes
  useEffect(() => {
    if (status) {
      logEvent("status", status);
    }
  }, [status, logEvent]);

  // Log activity changes
  useEffect(() => {
    if (activity) {
      logEvent("activity", activity);
    }
  }, [activity, logEvent]);

  // Initial log entry
  useEffect(() => {
    logEvent("connected", `Streaming workflow ${workflowId.slice(0, 20)}...`);
  }, [workflowId, logEvent]);

  // Use passed base URL or fallback to localhost for development
  const temporalUiUrl = temporalUiBaseUrl
    ? `${temporalUiBaseUrl}/workflows/${workflowId}`
    : `http://localhost:8233/namespaces/default/workflows/${workflowId}`;

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
            ProcessFileWorkflow
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "px-2 py-1 text-xs font-medium rounded-full",
              getStatusBadgeClasses(status),
            )}
          >
            {status || "PENDING"}
          </span>
          <a
            href={temporalUiUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-purple-500 transition-colors"
            title="View in Temporal UI"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* Current activity - only show spinner if still running */}
      {activity && !isComplete && !isError && (
        <div className="mb-2 text-sm text-purple-600 dark:text-purple-400 flex items-center gap-2">
          <Loader2 className="w-3 h-3 animate-spin" />
          <span>{message || activity}</span>
          {step && totalSteps && (
            <span className="text-gray-500 dark:text-gray-400">
              (Step {step}/{totalSteps})
            </span>
          )}
        </div>
      )}

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
          {isComplete
            ? "Workflow completed!"
            : isError
              ? "Workflow failed"
              : isLoading
                ? message || "Processing..."
                : "Starting..."}
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

      {/* Event Log */}
      <EventLog entries={eventLog} />

      <p className="text-xs text-gray-400 dark:text-gray-500 mt-2 font-mono">
        ID: {workflowId}
      </p>
    </motion.div>
  );
}

function EventLog({ entries }: { entries: EventLogEntry[] }) {
  return (
    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-2 mb-2">
        <Radio className="w-3 h-3 text-purple-500" />
        <p className="text-xs font-medium text-gray-600 dark:text-gray-400">
          Real-time Events (SSE)
        </p>
      </div>
      <div className="bg-gray-900 dark:bg-black rounded-lg p-2 font-mono text-xs max-h-32 overflow-auto">
        {entries.length === 0 ? (
          <span className="text-gray-500">Connecting to stream...</span>
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
                  entry.event === "status" && "text-yellow-400",
                  entry.event === "activity" && "text-blue-400",
                  entry.event === "progress" && "text-purple-400",
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
