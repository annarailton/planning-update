export function AgentPageHeader() {
  return (
    <div className="mb-6 text-center">
      <div className="flex items-center justify-center gap-2 mb-2">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-500 to-gray-900 dark:from-gray-400 dark:to-gray-100 bg-clip-text text-transparent">
          Agent Chat Interface
        </h1>
        <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400 rounded-full border border-green-200 dark:border-green-800">
          OpenAI Only
        </span>
      </div>
      <p className="text-gray-500 dark:text-gray-400 mt-2">
        Interact with the Agent Chat Interface backed by persistent session
        memory.
        <br />
        <span className="text-xs text-gray-400 dark:text-gray-500">
          Powered by OpenAI Agents SDK
        </span>
      </p>
    </div>
  );
}
