/**
 * Workflow creator panel for starting Temporal workflows.
 */

import { useState, useCallback } from "react";
import {
  Play,
  Loader2,
  FileBox,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { useStartWorkflow } from "../hooks/useStartWorkflow";
import { useTemporalStatus } from "../hooks/useTemporalStatus";
import { cn } from "../../../shared/utils/cn";

interface WorkflowCreatorProps {
  onWorkflowCreated: (workflowId: string) => void;
}

export function WorkflowCreator({ onWorkflowCreated }: WorkflowCreatorProps) {
  const { startWorkflow, isLoading } = useStartWorkflow();
  const { status, isEnabled, isLoading: statusLoading } = useTemporalStatus();
  const [bucketName, setBucketName] = useState("demo-bucket");

  const handleStartWorkflow = useCallback(async () => {
    try {
      const response = await startWorkflow({
        bucketName: bucketName,
      });
      onWorkflowCreated(response.workflowId);
    } catch (err) {
      console.error("Failed to start workflow:", err);
    }
  }, [startWorkflow, bucketName, onWorkflowCreated]);

  return (
    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
      {/* Temporal Status */}
      <TemporalStatusBanner
        isLoading={statusLoading}
        isEnabled={isEnabled}
        message={status?.message}
      />

      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 mt-4">
        Start a Workflow
      </h3>

      <div className="grid grid-cols-1 gap-6">
        {/* Process File Workflow */}
        <ProcessFileWorkflowForm
          bucketName={bucketName}
          onBucketNameChange={setBucketName}
          onSubmit={handleStartWorkflow}
          isLoading={isLoading}
          disabled={!isEnabled}
        />
      </div>
    </div>
  );
}

interface TemporalStatusBannerProps {
  isLoading: boolean;
  isEnabled: boolean;
  message?: string;
}

function TemporalStatusBanner({
  isLoading,
  isEnabled,
  message,
}: TemporalStatusBannerProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
        <Loader2 className="w-4 h-4 animate-spin" />
        Checking Temporal status...
      </div>
    );
  }

  if (!isEnabled) {
    return (
      <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-lg px-3 py-2">
        <AlertCircle className="w-4 h-4" />
        <span>
          Temporal is not available. Make sure it's running with{" "}
          <code className="bg-amber-100 dark:bg-amber-900/40 px-1 rounded">
            pnpm dev
          </code>
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 rounded-lg px-3 py-2">
      <CheckCircle2 className="w-4 h-4" />
      <span>{message || "Temporal is connected"}</span>
    </div>
  );
}

interface ProcessFileWorkflowFormProps {
  bucketName: string;
  onBucketNameChange: (value: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  disabled: boolean;
}

function ProcessFileWorkflowForm({
  bucketName,
  onBucketNameChange,
  onSubmit,
  isLoading,
  disabled,
}: ProcessFileWorkflowFormProps) {
  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        <FileBox className="w-4 h-4 text-purple-500" />
        Process File Workflow
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
        Demonstrates a durable workflow with 5 activities: Download → Hash →
        Metadata → Thumbnail → Update Status. Each activity is independently
        retryable with configurable timeouts.
      </p>

      <div className="mb-4">
        <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
          Bucket Name
        </label>
        <input
          type="text"
          value={bucketName}
          onChange={(e) => onBucketNameChange(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          placeholder="demo-bucket"
        />
      </div>

      <button
        onClick={onSubmit}
        disabled={isLoading || disabled}
        className={cn(
          "w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all",
          "bg-gradient-to-r from-purple-500 to-indigo-600 text-white",
          "hover:from-purple-600 hover:to-indigo-700",
          "disabled:opacity-50 disabled:cursor-not-allowed",
        )}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Play className="w-4 h-4" />
        )}
        Start Workflow
      </button>
    </div>
  );
}
