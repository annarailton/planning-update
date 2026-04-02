import { motion } from "motion/react";
import { ArrowLeft, Radio, Zap, Volume2 } from "lucide-react";
import { Link } from "react-router-dom";

export function RealtimePageHeader() {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6"
    >
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Home
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg shadow-lg">
              <Radio className="w-5 h-5 text-white" />
            </div>
            Realtime Voice Agent
            <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400 rounded-full border border-green-200 dark:border-green-800">
              OpenAI Only
            </span>
          </h1>
          <p className="text-gray-600 dark:text-gray-300 max-w-2xl">
            Voice-enabled AI agent powered by OpenAI's Realtime API. Speak
            naturally or type messages for a conversational AI experience with
            low latency.
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded-full text-xs font-medium border border-transparent dark:border-emerald-700/50">
          <Zap className="w-3 h-3" />
          Low Latency
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 rounded-full text-xs font-medium border border-transparent dark:border-teal-700/50">
          <Volume2 className="w-3 h-3" />
          Voice & Text
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-cyan-50 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300 rounded-full text-xs font-medium border border-transparent dark:border-cyan-700/50">
          <Radio className="w-3 h-3" />
          WebSocket Streaming
        </div>
      </div>
    </motion.div>
  );
}
