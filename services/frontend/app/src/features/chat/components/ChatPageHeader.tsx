export function ChatPageHeader() {
  return (
    <div className="mb-6 text-center">
      <div className="flex items-center justify-center gap-2 mb-2">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
          AI Chat Interface
        </h1>
        <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-400 rounded-full border border-indigo-200 dark:border-indigo-800">
          Multi-Provider
        </span>
      </div>
      <p className="text-gray-600 dark:text-gray-400 mt-2">
        Chat with AI using streaming responses. Supports OpenAI, Anthropic, and
        Gemini.
      </p>
    </div>
  );
}
