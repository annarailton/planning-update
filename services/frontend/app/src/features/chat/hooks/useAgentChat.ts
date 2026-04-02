import { useState, useCallback, useRef } from "react";
import { useAuth } from "@clerk/clerk-react";
import { toast } from "sonner";
import apiClient from "../../../shared/lib/api-client";
import { Message } from "./useLLM";

interface UseAgentChatReturn {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  sessionId: string;
}

const generateSessionId = () => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

export function useAgentChat(): UseAgentChatReturn {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId] = useState(() => generateSessionId());
  const messagesRef = useRef<Message[]>([]);

  const syncMessages = useCallback(
    (updater: (prev: Message[]) => Message[]) => {
      const next = updater(messagesRef.current);
      messagesRef.current = next;
      setMessages(next);
      return next;
    },
    [],
  );

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed) return;

      let assistantMessageId: string | null = null;
      let assistantMessageRef: Message | null = null;
      const userMessage: Message = {
        id: Date.now().toString(),
        role: "user",
        content: trimmed,
        timestamp: new Date(),
      };

      syncMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setIsStreaming(true);

      try {
        const token = await getToken();
        if (!token) {
          toast.error("Authentication required");
          syncMessages((prev) =>
            prev.filter((msg) => msg.id !== userMessage.id),
          );
          setIsLoading(false);
          setIsStreaming(false);
          return;
        }

        const messagePayload = messagesRef.current.map((message) => ({
          role: message.role,
          content: message.content,
        }));

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "",
          timestamp: new Date(),
        };
        assistantMessageId = assistantMessage.id;
        assistantMessageRef = assistantMessage;
        syncMessages((prev) => [...prev, assistantMessage]);

        const response = await apiClient.stream(
          "/agent/invoke_agent",
          {
            messages: messagePayload,
            stream: true,
            session_id: sessionId,
          },
          token,
        );

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (reader) {
          let buffer = "";
          let done = false;

          while (!done) {
            const result = await reader.read();
            done = result.done || false;
            if (done) break;

            buffer += decoder.decode(result.value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (!line.startsWith("data: ")) continue;

              const data = line.slice(6).trim();
              if (!data || data === "[DONE]") continue;

              try {
                const parsed = JSON.parse(data);
                let contentDelta = "";

                if (parsed.type === "content" && parsed.content) {
                  contentDelta = parsed.content;
                } else if (parsed.choices?.[0]?.delta?.content) {
                  contentDelta = parsed.choices[0].delta.content;
                }

                if (contentDelta && assistantMessageRef) {
                  assistantMessageRef.content += contentDelta;
                  syncMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessageRef?.id
                        ? { ...assistantMessageRef }
                        : msg,
                    ),
                  );
                }
              } catch (err) {
                console.warn("Failed to parse SSE data:", data, err);
              }
            }
          }
        }
      } catch (error) {
        console.error("Agent chat error:", error);
        toast.error("Failed to send agent message");
        syncMessages((prev) =>
          prev.filter(
            (msg) => msg.id !== userMessage.id && msg.id !== assistantMessageId,
          ),
        );
      } finally {
        setIsLoading(false);
        setIsStreaming(false);
      }
    },
    [getToken, sessionId, syncMessages],
  );

  const clearMessages = useCallback(() => {
    syncMessages(() => []);
  }, [syncMessages]);

  return {
    messages,
    isLoading,
    isStreaming,
    sendMessage,
    clearMessages,
    sessionId,
  };
}
