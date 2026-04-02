/**
 * Architecture diagram explaining the background jobs flow.
 */

import { ArrowRight } from "lucide-react";

const FLOW_STEPS = [
  { label: "Frontend", color: "blue" },
  { label: "POST /api/jobs", color: "purple" },
  { label: "Redis Stream", color: "red" },
  { label: "Worker", color: "orange" },
  { label: "Redis Pub/Sub", color: "red" },
  { label: "SSE Stream", color: "green" },
  { label: "Frontend", color: "blue" },
] as const;

const EXPLANATIONS = [
  {
    title: "1. Job Creation",
    description:
      "Frontend POSTs to /api/jobs. Backend saves to DB and enqueues to Redis Stream.",
    code: "/api/jobs",
  },
  {
    title: "2. Worker Processing",
    description:
      "Worker consumes from Redis Stream via XREADGROUP. Publishes progress to Pub/Sub channel.",
    code: "XREADGROUP",
  },
  {
    title: "3. Real-time Updates",
    description:
      "Backend SSE endpoint subscribes to Pub/Sub. Streams events to frontend via EventSource.",
    code: "EventSource",
  },
] as const;

const colorClasses: Record<string, string> = {
  blue: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300",
  purple:
    "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300",
  red: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300",
  orange:
    "bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300",
  green: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300",
};

export function ArchitectureDiagram() {
  return (
    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
        Architecture
      </h3>

      {/* Visual Flow */}
      <div className="flex flex-wrap items-center justify-center gap-2 text-xs mb-6">
        {FLOW_STEPS.map((step, index) => (
          <span key={index}>
            <span
              className={`px-2 py-1 rounded font-medium ${colorClasses[step.color]}`}
            >
              {step.label}
            </span>
            {index < FLOW_STEPS.length - 1 && (
              <ArrowRight className="w-4 h-4 text-gray-400 inline ml-2" />
            )}
          </span>
        ))}
      </div>

      {/* Step by step */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        {EXPLANATIONS.map((item) => (
          <div key={item.title} className="space-y-1">
            <p className="font-semibold text-gray-700 dark:text-gray-300">
              {item.title}
            </p>
            <p className="text-gray-500 dark:text-gray-400">
              {item.description.split(item.code).map((part, i, arr) => (
                <span key={i}>
                  {part}
                  {i < arr.length - 1 && (
                    <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">
                      {item.code}
                    </code>
                  )}
                </span>
              ))}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
