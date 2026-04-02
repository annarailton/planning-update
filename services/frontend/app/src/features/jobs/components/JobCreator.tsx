/**
 * Job creator panel with forms for different job types.
 */

import { useState, useCallback } from "react";
import { Play, Loader2, Timer, Zap } from "lucide-react";
import { useCreateJob } from "../hooks/useCreateJob";
import { cn } from "../../../shared/utils/cn";

interface JobCreatorProps {
  onJobCreated: (jobId: string, jobType: string) => void;
}

export function JobCreator({ onJobCreated }: JobCreatorProps) {
  const { createJob, isLoading } = useCreateJob();
  const [duration, setDuration] = useState(5);
  const [steps, setSteps] = useState(5);

  const handleStartSlowTask = useCallback(async () => {
    try {
      const response = await createJob({
        jobType: "slow_task",
        payload: { duration, steps },
      });
      onJobCreated(response.jobId, "slow_task");
    } catch (err) {
      console.error("Failed to create job:", err);
    }
  }, [createJob, duration, steps, onJobCreated]);

  const handleStartEchoTask = useCallback(async () => {
    try {
      const response = await createJob({
        jobType: "echo",
        payload: { message: "Hello from the frontend!", timestamp: Date.now() },
      });
      onJobCreated(response.jobId, "echo");
    } catch (err) {
      console.error("Failed to create job:", err);
    }
  }, [createJob, onJobCreated]);

  return (
    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Start a Job
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Slow Task */}
        <SlowTaskForm
          duration={duration}
          steps={steps}
          onDurationChange={setDuration}
          onStepsChange={setSteps}
          onSubmit={handleStartSlowTask}
          isLoading={isLoading}
        />

        {/* Echo Task */}
        <EchoTaskForm onSubmit={handleStartEchoTask} isLoading={isLoading} />
      </div>
    </div>
  );
}

interface SlowTaskFormProps {
  duration: number;
  steps: number;
  onDurationChange: (value: number) => void;
  onStepsChange: (value: number) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

function SlowTaskForm({
  duration,
  steps,
  onDurationChange,
  onStepsChange,
  onSubmit,
  isLoading,
}: SlowTaskFormProps) {
  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        <Timer className="w-4 h-4 text-blue-500" />
        Slow Task
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
        Simulates a long-running job with multiple steps. Watch the SSE stream
        show each progress update as the worker publishes to Redis Pub/Sub.
      </p>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
            Duration (sec)
          </label>
          <input
            type="number"
            min={1}
            max={30}
            value={duration}
            onChange={(e) => onDurationChange(Number(e.target.value))}
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
            Steps
          </label>
          <input
            type="number"
            min={1}
            max={20}
            value={steps}
            onChange={(e) => onStepsChange(Number(e.target.value))}
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          />
        </div>
      </div>

      <SubmitButton
        onClick={onSubmit}
        isLoading={isLoading}
        label="Start Slow Task"
        gradient="from-blue-500 to-indigo-600"
        hoverGradient="from-blue-600 to-indigo-700"
      />
    </div>
  );
}

interface EchoTaskFormProps {
  onSubmit: () => void;
  isLoading: boolean;
}

function EchoTaskForm({ onSubmit, isLoading }: EchoTaskFormProps) {
  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        <Zap className="w-4 h-4 text-green-500" />
        Echo Task
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
        Instant round-trip through the full pipeline: Frontend &rarr; Backend
        &rarr; Redis Stream &rarr; Worker &rarr; Redis Pub/Sub &rarr; SSE &rarr;
        Frontend. Returns the payload immediately.
      </p>

      <SubmitButton
        onClick={onSubmit}
        isLoading={isLoading}
        label="Start Echo Task"
        gradient="from-green-500 to-emerald-600"
        hoverGradient="from-green-600 to-emerald-700"
      />
    </div>
  );
}

interface SubmitButtonProps {
  onClick: () => void;
  isLoading: boolean;
  label: string;
  gradient: string;
  hoverGradient: string;
}

function SubmitButton({
  onClick,
  isLoading,
  label,
  gradient,
  hoverGradient,
}: SubmitButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={isLoading}
      className={cn(
        "mt-auto w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all",
        `bg-gradient-to-r ${gradient} text-white`,
        `hover:${hoverGradient}`,
        "disabled:opacity-50 disabled:cursor-not-allowed",
      )}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Play className="w-4 h-4" />
      )}
      {label}
    </button>
  );
}
