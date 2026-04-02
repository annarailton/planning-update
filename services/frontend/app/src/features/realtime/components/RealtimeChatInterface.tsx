import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  Bot,
  Trash2,
  StopCircle,
} from "lucide-react";
import { useRealtimeAgent, TranscriptMessage } from "../hooks/useRealtimeAgent";
import { AudioWaveform, AudioVisualizer } from "./AudioVisualizer";
import { cn } from "../../../shared/utils/cn";

// Memoized message component to prevent unnecessary re-renders
const MessageBubble = React.memo(function MessageBubble({
  message,
}: {
  message: TranscriptMessage;
}) {
  return (
    <div
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
            : "bg-teal-800/80 border-teal-700 text-teal-100",
        )}
      >
        <p className="text-sm whitespace-pre-wrap break-words">
          {message.content}
        </p>
        <p
          className={cn(
            "text-[10px] mt-1 opacity-60",
            message.role === "user" ? "text-teal-200" : "text-teal-400",
          )}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
});

export function RealtimeChatInterface() {
  const {
    isConnected,
    isConnecting,
    connectionError,
    isRecording,
    isSpeaking,
    messages,
    currentAgentName,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    sendTextMessage,
    interrupt,
    clearMessages,
    sessionId,
  } = useRealtimeAgent();

  const [input, setInput] = useState("");
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const lastMessageCountRef = useRef(0);

  // Scroll to bottom only when new messages are added, not when content updates
  useEffect(() => {
    const messageCount = messages.length;
    if (messageCount > lastMessageCountRef.current) {
      // New message added - scroll to bottom
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop =
          messagesContainerRef.current.scrollHeight;
      }
    }
    lastMessageCountRef.current = messageCount;
  }, [messages.length]);

  useEffect(() => {
    if (!input && inputRef.current) {
      inputRef.current.style.height = "2.5rem";
    }
  }, [input]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!input.trim() || !isConnected) return;

      const message = input;
      setInput("");
      sendTextMessage(message);
    },
    [input, isConnected, sendTextMessage],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e as unknown as React.FormEvent);
      }
    },
    [handleSubmit],
  );

  const handleMicClick = useCallback(async () => {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  }, [isRecording, stopRecording, startRecording]);

  const handleConnectionClick = useCallback(async () => {
    if (isConnected) {
      disconnect();
    } else {
      await connect();
    }
  }, [isConnected, disconnect, connect]);

  const shortSessionId = sessionId.slice(0, 8);

  return (
    <div
      id="realtime-chat"
      className="flex flex-col h-[70vh] min-h-[400px] max-h-[800px] bg-gradient-to-br from-emerald-950 via-teal-900 to-cyan-900 rounded-xl border border-teal-800 shadow-2xl shadow-black/40 text-white"
    >
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between gap-2 px-3 sm:px-4 py-3 border-b border-teal-800 bg-teal-900/80 backdrop-blur rounded-t-xl">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={cn(
              "p-2 rounded-lg flex-shrink-0 shadow-inner shadow-black/30 transition-colors duration-300",
              isConnected
                ? "bg-gradient-to-br from-emerald-500 to-teal-600"
                : "bg-gradient-to-br from-gray-600 to-gray-700",
            )}
          >
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              {currentAgentName}
              <div className="w-12 h-4 flex items-center">
                {isSpeaking && (
                  <AudioVisualizer isActive={isSpeaking} barCount={4} />
                )}
              </div>
            </h2>
            <p className="text-xs text-teal-300">
              {isConnected
                ? "Voice-enabled realtime agent"
                : "Click connect to start"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-teal-300">
          <span className="font-mono text-[10px] uppercase tracking-widest">
            Session #{shortSessionId}
          </span>

          {/* Connection status indicator */}
          <div
            className={cn(
              "w-2 h-2 rounded-full transition-colors duration-300",
              isConnected
                ? "bg-emerald-400"
                : isConnecting
                  ? "bg-yellow-400 animate-pulse"
                  : "bg-gray-500",
            )}
          />

          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="p-1.5 text-teal-300 hover:text-white hover:bg-white/10 rounded-md transition-colors flex-shrink-0"
              title="Clear chat"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Messages area */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto min-h-0"
      >
        <div className="px-3 sm:px-4 py-4">
          {!isConnected && messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-center text-teal-200">
              <div className="p-3 bg-white/5 rounded-xl mb-4 border border-white/10">
                <Bot className="w-8 h-8 text-teal-100" />
              </div>
              <h3 className="text-lg font-semibold mb-1">
                Realtime Voice Agent
              </h3>
              <p className="text-xs text-teal-300 max-w-xs mb-4">
                Connect to start a voice conversation with the AI agent. You can
                speak naturally or type messages.
              </p>
              {connectionError && (
                <p className="text-xs text-red-400 mb-4">{connectionError}</p>
              )}
              <button
                onClick={handleConnectionClick}
                disabled={isConnecting}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors",
                  isConnecting
                    ? "bg-yellow-600/50 text-yellow-200 cursor-wait"
                    : "bg-emerald-600 hover:bg-emerald-500 text-white",
                )}
              >
                <Phone className="w-4 h-4" />
                {isConnecting ? "Connecting..." : "Connect"}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 px-3 sm:px-4 py-3 border-t border-teal-800 bg-teal-900/80 backdrop-blur rounded-b-xl">
        {/* Connection controls */}
        {isConnected && (
          <div className="flex items-center justify-center gap-4 mb-3">
            {/* Microphone button */}
            <button
              onClick={handleMicClick}
              className={cn(
                "p-3 rounded-full shadow-lg relative transition-colors duration-200",
                isRecording
                  ? "bg-teal-600 text-white ring-2 ring-emerald-400 ring-offset-2 ring-offset-teal-900"
                  : "bg-gray-600 hover:bg-gray-500 text-white",
              )}
              title={
                isRecording
                  ? "Mic is ON - click to mute"
                  : "Mic is OFF - click to unmute"
              }
            >
              {isRecording ? (
                <Mic className="w-5 h-5" />
              ) : (
                <MicOff className="w-5 h-5" />
              )}
              {isRecording && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full animate-pulse" />
              )}
            </button>

            {/* Status indicator - fixed width container */}
            <button
              onClick={isSpeaking ? interrupt : undefined}
              disabled={!isSpeaking}
              className={cn(
                "flex items-center justify-center gap-2 w-36 h-10 rounded-full border transition-colors duration-300",
                isSpeaking
                  ? "bg-emerald-500/20 border-emerald-500/30 hover:bg-red-500/30 hover:border-red-500/50 cursor-pointer group"
                  : "bg-gray-700/50 border-gray-600/30 cursor-default",
              )}
              title={isSpeaking ? "Click to interrupt" : undefined}
            >
              {isSpeaking ? (
                <>
                  <AudioWaveform
                    isActive={true}
                    className="!bg-transparent !p-0"
                  />
                  <StopCircle className="w-4 h-4 text-emerald-400 group-hover:text-red-400 transition-colors" />
                </>
              ) : (
                <span className="text-xs text-gray-400">Ready</span>
              )}
            </button>

            {/* Disconnect button */}
            <button
              onClick={handleConnectionClick}
              className="p-2 rounded-full bg-red-600/80 hover:bg-red-500 text-white transition-colors duration-200"
              title="Disconnect"
            >
              <PhoneOff className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Text input */}
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isConnected
                ? "Type a message or use voice..."
                : "Connect to start chatting"
            }
            disabled={!isConnected}
            rows={1}
            className={cn(
              "flex-1 min-h-[2.5rem] px-3.5 py-2.5 bg-black/30 border border-teal-700 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-transparent text-sm placeholder-teal-400 leading-5 text-white",
              !isConnected && "opacity-50 cursor-not-allowed",
            )}
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
            disabled={!input.trim() || !isConnected}
            className={cn(
              "h-10 w-10 rounded-xl flex-shrink-0 flex items-center justify-center border border-teal-700 transition-colors duration-200",
              !input.trim() || !isConnected
                ? "bg-teal-800 text-teal-500 cursor-not-allowed"
                : "bg-white/10 text-white hover:bg-white/20 shadow-lg shadow-black/40",
            )}
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
