/**
 * Architecture diagram explaining Temporal workflow execution with SSE streaming.
 */

import { Radio } from "lucide-react";

export function TemporalArchitecture() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        How Temporal + SSE Streaming Works
      </h3>

      {/* Main Flow Diagram */}
      <div className="mb-6">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 text-center">
          Workflow Execution Flow
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2 text-sm">
          <FlowStep label="Frontend" color="blue" />
          <Arrow />
          <FlowStep label="Backend API" color="green" />
          <Arrow />
          <FlowStep label="Temporal Server" color="purple" />
          <Arrow />
          <FlowStep label="Worker" color="orange" />
          <Arrow />
          <FlowStep label="Activities" color="pink" />
        </div>
      </div>

      {/* Streaming Flow Diagram */}
      <div className="mb-6 p-3 bg-gradient-to-r from-purple-50 to-red-50 dark:from-purple-900/20 dark:to-red-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
        <div className="flex items-center gap-2 mb-2">
          <Radio className="w-4 h-4 text-red-500" />
          <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
            Real-time Progress Streaming
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2 text-sm">
          <FlowStep label="Activities" color="pink" />
          <Arrow label="publish" />
          <FlowStep label="Redis Pub/Sub" color="red" />
          <Arrow label="subscribe" />
          <FlowStep label="Backend SSE" color="green" />
          <Arrow label="stream" />
          <FlowStep label="Frontend" color="blue" />
        </div>
      </div>

      {/* Explanation */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
        <div className="space-y-3">
          <ExplanationItem
            number={1}
            title="Start Workflow"
            description="Frontend calls POST /api/workflows/process-file"
          />
          <ExplanationItem
            number={2}
            title="Connect SSE"
            description="Frontend opens SSE stream to /api/workflows/{id}/stream"
          />
          <ExplanationItem
            number={3}
            title="Backend Schedules"
            description="Backend uses Temporal client to start workflow"
          />
          <ExplanationItem
            number={4}
            title="Worker Executes"
            description="Worker polls task queue, runs workflow code"
          />
        </div>
        <div className="space-y-3">
          <ExplanationItem
            number={5}
            title="Activities Publish"
            description="Each activity publishes progress to Redis Pub/Sub"
            highlight
          />
          <ExplanationItem
            number={6}
            title="SSE Streams"
            description="Backend subscribes to Redis, streams events to frontend"
            highlight
          />
          <ExplanationItem
            number={7}
            title="Real-time Updates"
            description="Frontend receives progress, activity names, step counts"
            highlight
          />
          <ExplanationItem
            number={8}
            title="Result Stored"
            description="Final result persisted in Temporal, queryable via API"
          />
        </div>
      </div>

      {/* Key Benefits */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Why Temporal + Redis SSE?
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
          <BenefitCard
            title="Durable Execution"
            description="Workflows survive crashes and restarts"
          />
          <BenefitCard
            title="Built-in Retries"
            description="Automatic retry policies per activity"
          />
          <BenefitCard
            title="Real-time Progress"
            description="SSE streams updates as activities run"
          />
          <BenefitCard
            title="Full Visibility"
            description="Temporal UI + live frontend updates"
          />
        </div>
      </div>
    </div>
  );
}

function FlowStep({ label, color }: { label: string; color: string }) {
  const colorClasses: Record<string, string> = {
    blue: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
    green:
      "bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800",
    purple:
      "bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800",
    orange:
      "bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800",
    pink: "bg-pink-100 text-pink-700 border-pink-200 dark:bg-pink-900/30 dark:text-pink-400 dark:border-pink-800",
    red: "bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
  };

  return (
    <div
      className={`px-3 py-1.5 rounded-lg border ${colorClasses[color]} font-medium`}
    >
      {label}
    </div>
  );
}

function Arrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-gray-400 dark:text-gray-600">→</span>
      {label && (
        <span className="text-[10px] text-gray-400 dark:text-gray-500">
          {label}
        </span>
      )}
    </div>
  );
}

function ExplanationItem({
  number,
  title,
  description,
  highlight,
}: {
  number: number;
  title: string;
  description: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`flex gap-3 ${highlight ? "bg-purple-50 dark:bg-purple-900/20 -mx-2 px-2 py-1 rounded-lg" : ""}`}
    >
      <div
        className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
          highlight
            ? "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400"
            : "bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400"
        }`}
      >
        {number}
      </div>
      <div>
        <p className="font-medium text-gray-900 dark:text-gray-100">{title}</p>
        <p className="text-gray-500 dark:text-gray-400">{description}</p>
      </div>
    </div>
  );
}

function BenefitCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
      <p className="font-medium text-gray-900 dark:text-gray-100 mb-1">
        {title}
      </p>
      <p className="text-gray-500 dark:text-gray-400">{description}</p>
    </div>
  );
}
