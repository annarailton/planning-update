import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, Trash2 } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { useAgentChat } from "../hooks/useAgentChat";
import { cn } from "../../../shared/utils/cn";

export function AgentChatInterface() {
  const {
    messages,
    isLoading,
    isStreaming,
    sendMessage,
    clearMessages,
    sessionId,
  } = useAgentChat();

  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!input && inputRef.current) {
      inputRef.current.style.height = "2.5rem";
    }
  }, [input]);

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

  const shortSessionId = sessionId.slice(0, 8);

  return (
    <div
      id="agent-chat"
      className="flex flex-col h-[70vh] min-h-[400px] max-h-[800px] bg-gradient-to-br from-gray-950 via-gray-900 to-gray-800 rounded-xl border border-gray-800 shadow-2xl shadow-black/40 text-white"
    >
      <div className="flex-shrink-0 flex items-center justify-between gap-2 px-3 sm:px-4 py-3 border-b border-gray-800 bg-gray-900/80 backdrop-blur rounded-t-xl">
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2 bg-gradient-to-br from-gray-600 to-gray-500 rounded-lg flex-shrink-0 shadow-inner shadow-black/30">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">
              Mock Math Agent
            </h2>
            <p className="text-xs text-gray-400">
              Agent that answers math questions only
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="font-mono text-[10px] uppercase tracking-widest">
            Session #{shortSessionId}
          </span>
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition-all flex-shrink-0"
              title="Clear agent chat"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="px-3 sm:px-4 py-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-center text-gray-300">
              <div className="p-3 bg-white/5 rounded-xl mb-4 border border-white/10">
                <Bot className="w-8 h-8 text-gray-100" />
              </div>
              <h3 className="text-lg font-semibold mb-1">
                Agent ready for tasks
              </h3>
              <p className="text-xs text-gray-400 max-w-xs">
                Start a conversation to spin up a new agent session. This mock
                agent can only answer math questions.
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
                        "max-w-[85%] sm:max-w-[80%] px-3 sm:px-3.5 py-2 sm:py-2.5 rounded-2xl border",
                        message.role === "user"
                          ? "bg-white/10 border-white/10 text-white shadow-lg shadow-black/30"
                          : "bg-gray-800/80 border-gray-700 text-gray-100",
                      )}
                    >
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
                            ? "text-gray-300"
                            : "text-gray-500",
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

      <form
        onSubmit={handleSubmit}
        className="flex-shrink-0 px-3 sm:px-4 py-3 border-t border-gray-800 bg-gray-900/80 backdrop-blur rounded-b-xl"
      >
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask the agent to solve a math problem"
            disabled={isLoading}
            rows={1}
            className="flex-1 min-h-[2.5rem] px-3.5 py-2.5 bg-black/30 border border-gray-700 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-gray-500/50 focus:border-transparent transition-all text-sm placeholder-gray-500 leading-5 text-white"
            style={{
              overflow: input && input.length > 100 ? "auto" : "hidden",
              height: "2.5rem",
            }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = "2.5rem";
              const scrollHeight = target.scrollHeight;
              const maxHeight = 128;
              const newHeight = Math.min(scrollHeight, maxHeight);
              target.style.height = `${newHeight}px`;
              target.style.overflow =
                newHeight >= maxHeight ? "auto" : "hidden";
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className={cn(
              "h-10 w-10 rounded-xl transition-all flex-shrink-0 flex items-center justify-center border border-gray-700",
              !input.trim() || isLoading
                ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                : "bg-white/10 text-white hover:bg-white/20 shadow-lg shadow-black/40",
            )}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
