import React, { useState, useRef, useEffect } from "react";
import { Send, Sparkles, Trash2, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { useLLM } from "../hooks/useLLM";
import { cn } from "../../../shared/utils/cn";

// Provider display names and colors
const PROVIDER_CONFIG: Record<
  string,
  { name: string; color: string; gradient: string }
> = {
  openai: {
    name: "OpenAI",
    color: "text-green-600",
    gradient: "from-green-500 to-emerald-600",
  },
  anthropic: {
    name: "Claude",
    color: "text-orange-600",
    gradient: "from-orange-500 to-amber-600",
  },
  gemini: {
    name: "Gemini",
    color: "text-blue-600",
    gradient: "from-blue-500 to-cyan-600",
  },
};

export function ChatInterface() {
  const {
    messages,
    isLoading,
    isStreaming,
    sendMessage,
    clearMessages,
    providers,
    selectedProvider,
    setSelectedProvider,
    models,
    selectedModel,
    setSelectedModel,
    fetchingProviders,
  } = useLLM();

  const [input, setInput] = useState("");
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [showProviderSelector, setShowProviderSelector] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Reset textarea height when input is cleared
  useEffect(() => {
    if (!input && inputRef.current) {
      inputRef.current.style.height = "2.5rem";
    }
  }, [input]);

  // Close selectors when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      setShowModelSelector(false);
      setShowProviderSelector(false);
    };
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input;
    setInput("");
    await sendMessage(message);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as React.FormEvent);
    }
  };

  const currentProviderConfig = selectedProvider
    ? PROVIDER_CONFIG[selectedProvider] || {
        name: selectedProvider,
        color: "text-gray-600",
        gradient: "from-indigo-500 to-purple-600",
      }
    : {
        name: "AI",
        color: "text-gray-600",
        gradient: "from-indigo-500 to-purple-600",
      };

  return (
    <div className="flex flex-col h-[70vh] min-h-[400px] max-h-[800px] bg-white/50 dark:bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-200/50 dark:border-gray-700/50 shadow-xl dark:shadow-black/20">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between gap-2 px-3 sm:px-4 py-3 border-b border-gray-200/50 dark:border-gray-700/50 bg-white/70 dark:bg-gray-800/70 backdrop-blur-lg rounded-t-xl">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className={cn(
              "p-1.5 bg-gradient-to-br rounded-lg flex-shrink-0",
              currentProviderConfig.gradient,
            )}
          >
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div className="hidden sm:block">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
              AI Assistant
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Powered by {currentProviderConfig.name}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Provider Selector */}
          {providers.length > 1 && (
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowProviderSelector(!showProviderSelector);
                  setShowModelSelector(false);
                }}
                disabled={fetchingProviders}
                className={cn(
                  "flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1 text-xs rounded-md transition-all font-medium",
                  "bg-gray-100/80 dark:bg-gray-700/80 hover:bg-gray-200/80 dark:hover:bg-gray-600/80",
                  currentProviderConfig.color,
                )}
              >
                <span className="truncate max-w-[80px] sm:max-w-none">
                  {currentProviderConfig.name}
                </span>
                <ChevronDown
                  className={cn(
                    "w-3 h-3 transition-transform text-gray-500 dark:text-gray-400 flex-shrink-0",
                    showProviderSelector && "rotate-180",
                  )}
                />
              </button>

              <AnimatePresence>
                {showProviderSelector && (
                  <motion.div
                    initial={{ opacity: 0, y: -8, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -8, scale: 0.96 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 mt-1 w-32 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {providers.map((provider) => {
                      const config = PROVIDER_CONFIG[provider.provider] || {
                        name: provider.name,
                        color: "text-gray-600",
                      };
                      return (
                        <button
                          key={provider.provider}
                          onClick={() => {
                            setSelectedProvider(provider.provider);
                            setShowProviderSelector(false);
                          }}
                          className={cn(
                            "w-full px-3 py-1.5 text-left text-xs hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors",
                            provider.provider === selectedProvider
                              ? "bg-gray-100 dark:bg-gray-700 font-medium"
                              : "text-gray-700 dark:text-gray-200",
                            config.color,
                          )}
                        >
                          {config.name}
                        </button>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Model Selector */}
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowModelSelector(!showModelSelector);
                setShowProviderSelector(false);
              }}
              disabled={fetchingProviders}
              className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1 text-xs bg-gray-100/80 dark:bg-gray-700/80 hover:bg-gray-200/80 dark:hover:bg-gray-600/80 rounded-md transition-all font-medium text-gray-700 dark:text-gray-200"
            >
              <span className="truncate max-w-[100px] sm:max-w-[140px]">
                {selectedModel}
              </span>
              <ChevronDown
                className={cn(
                  "w-3 h-3 transition-transform text-gray-500 dark:text-gray-400 flex-shrink-0",
                  showModelSelector && "rotate-180",
                )}
              />
            </button>

            <AnimatePresence>
              {showModelSelector && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.96 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 mt-1 w-44 sm:w-52 max-h-64 overflow-y-auto bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50"
                  onClick={(e) => e.stopPropagation()}
                >
                  {models.length > 0 ? (
                    models.map((model) => (
                      <button
                        key={model}
                        onClick={() => {
                          setSelectedModel(model);
                          setShowModelSelector(false);
                        }}
                        className={cn(
                          "w-full px-3 py-1.5 text-left text-xs hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-200",
                          model === selectedModel &&
                            "bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 font-medium",
                        )}
                      >
                        {model}
                      </button>
                    ))
                  ) : (
                    <div className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">
                      Loading models...
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Clear button */}
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="p-1.5 sm:p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100/80 dark:hover:bg-gray-700/80 rounded-md transition-all flex-shrink-0"
              title="Clear chat"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="px-3 sm:px-4 py-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-center">
              <div
                className={cn(
                  "p-3 bg-gradient-to-br rounded-xl mb-4 opacity-80",
                  currentProviderConfig.gradient,
                )}
              >
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                How can I help you today?
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 max-w-xs">
                Ask me anything using {currentProviderConfig.name}'s{" "}
                {selectedModel} model.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <AnimatePresence initial={false}>
                {messages.map((message) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                    className={cn(
                      "flex",
                      message.role === "user" ? "justify-end" : "justify-start",
                    )}
                  >
                    <div
                      className={cn(
                        "max-w-[85%] sm:max-w-[80%] px-3 sm:px-3.5 py-2 sm:py-2.5 rounded-2xl",
                        message.role === "user"
                          ? cn(
                              "bg-gradient-to-r text-white shadow-lg",
                              currentProviderConfig.gradient,
                              "shadow-indigo-500/25",
                            )
                          : "bg-gray-100/80 dark:bg-gray-800/80 text-gray-900 dark:text-gray-100",
                      )}
                    >
                      {/* Show loading dots if this is the last message, it's from assistant, and we're streaming */}
                      {message.role === "assistant" &&
                      isStreaming &&
                      messages[messages.length - 1]?.id === message.id &&
                      !message.content ? (
                        <div className="flex gap-1 py-1">
                          <motion.div
                            animate={{ opacity: [0.4, 1, 0.4] }}
                            transition={{
                              duration: 1.5,
                              repeat: Infinity,
                              ease: "easeInOut",
                            }}
                            className="w-1.5 h-1.5 bg-gray-400 rounded-full"
                          />
                          <motion.div
                            animate={{ opacity: [0.4, 1, 0.4] }}
                            transition={{
                              duration: 1.5,
                              repeat: Infinity,
                              ease: "easeInOut",
                              delay: 0.2,
                            }}
                            className="w-1.5 h-1.5 bg-gray-400 rounded-full"
                          />
                          <motion.div
                            animate={{ opacity: [0.4, 1, 0.4] }}
                            transition={{
                              duration: 1.5,
                              repeat: Infinity,
                              ease: "easeInOut",
                              delay: 0.4,
                            }}
                            className="w-1.5 h-1.5 bg-gray-400 rounded-full"
                          />
                        </div>
                      ) : (
                        <p className="text-sm whitespace-pre-wrap break-words">
                          {message.content}
                        </p>
                      )}
                      <p
                        className={cn(
                          "text-[10px] mt-1",
                          message.role === "user"
                            ? "text-white/70"
                            : "text-gray-400",
                        )}
                      >
                        {message.timestamp.toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <form
        onSubmit={handleSubmit}
        className="flex-shrink-0 px-3 sm:px-4 py-3 border-t border-gray-200/50 dark:border-gray-700/50 bg-white/70 dark:bg-gray-800/70 backdrop-blur-lg rounded-b-xl"
      >
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            disabled={isLoading}
            rows={1}
            className="flex-1 min-h-[2.5rem] px-3.5 py-2.5 bg-gray-50/80 dark:bg-gray-700/80 border border-gray-200/50 dark:border-gray-600/50 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-transparent transition-all text-sm placeholder-gray-400 leading-5 text-gray-900 dark:text-white"
            style={{
              overflow: input && input.length > 100 ? "auto" : "hidden",
              height: "2.5rem",
            }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = "2.5rem";
              const scrollHeight = target.scrollHeight;
              const maxHeight = 128; // 8rem
              const newHeight = Math.min(scrollHeight, maxHeight);
              target.style.height = `${newHeight}px`;
              // Only show scrollbar when content exceeds max height
              target.style.overflow =
                newHeight >= maxHeight ? "auto" : "hidden";
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className={cn(
              "h-10 w-10 rounded-xl transition-all flex-shrink-0 flex items-center justify-center",
              !input.trim() || isLoading
                ? "bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed"
                : cn(
                    "bg-gradient-to-r text-white hover:opacity-90 shadow-lg shadow-indigo-500/25",
                    currentProviderConfig.gradient,
                  ),
            )}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
