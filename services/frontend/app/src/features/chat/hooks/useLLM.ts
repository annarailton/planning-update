import { useState, useCallback, useEffect } from "react";
import { useAuth } from "@clerk/clerk-react";
import { toast } from "sonner";
import apiClient from "../../../shared/lib/api-client";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
}

export interface ProviderInfo {
  provider: string;
  name: string;
  available: boolean;
  models: string[];
  defaultModel: string; // camelCase from API
}

interface ProvidersResponse {
  providers: ProviderInfo[];
  defaultProvider: string | null; // camelCase from API
}

interface UseLLMReturn {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  // Provider selection
  providers: ProviderInfo[];
  selectedProvider: string | null;
  setSelectedProvider: (provider: string) => void;
  // Model selection
  models: string[];
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  // Loading states
  fetchingProviders: boolean;
}

const FALLBACK_MODELS = ["gpt-5-mini", "gpt-5.2", "gpt-4o-mini"];
const DEFAULT_MODEL = "gpt-5-mini";

export function useLLM(): UseLLMReturn {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  // Provider state
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [fetchingProviders, setFetchingProviders] = useState(false);

  // Model state
  const [models, setModels] = useState<string[]>([...FALLBACK_MODELS]);
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL);

  // Fetch available providers on mount
  useEffect(() => {
    const fetchProviders = async () => {
      if (!apiClient.isReady) return;

      setFetchingProviders(true);
      try {
        const response =
          await apiClient.get<ProvidersResponse>("/llm/providers");

        // Filter to only available providers
        const availableProviders = response.providers.filter(
          (p) => p.available,
        );
        setProviders(availableProviders);

        // Set default provider
        if (response.defaultProvider) {
          setSelectedProvider(response.defaultProvider);
          // Set models for default provider
          const defaultProviderInfo = availableProviders.find(
            (p) => p.provider === response.defaultProvider,
          );
          if (defaultProviderInfo) {
            setModels(defaultProviderInfo.models);
            setSelectedModel(defaultProviderInfo.defaultModel);
          }
        } else if (availableProviders.length > 0) {
          setSelectedProvider(availableProviders[0].provider);
          setModels(availableProviders[0].models);
          setSelectedModel(availableProviders[0].defaultModel);
        }
      } catch (error) {
        console.warn("Failed to fetch providers, using defaults:", error);
        // Create a fallback OpenAI provider
        setProviders([
          {
            provider: "openai",
            name: "OpenAI",
            available: true,
            models: FALLBACK_MODELS,
            defaultModel: DEFAULT_MODEL,
          },
        ]);
        setSelectedProvider("openai");
      } finally {
        setFetchingProviders(false);
      }
    };

    fetchProviders();
  }, []);

  // Update models when provider changes
  const handleProviderChange = useCallback(
    (provider: string) => {
      setSelectedProvider(provider);
      const providerInfo = providers.find((p) => p.provider === provider);
      if (providerInfo) {
        setModels(providerInfo.models);
        setSelectedModel(providerInfo.defaultModel);
      }
    },
    [providers],
  );

  const sendMessage = useCallback(
    async (content: string) => {
      const userMessage: Message = {
        id: Date.now().toString(),
        role: "user",
        content,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setIsStreaming(true);

      try {
        // Get fresh token for streaming request
        const token = await getToken();
        if (!token) {
          toast.error("Authentication required");
          setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
          setIsLoading(false);
          setIsStreaming(false);
          return;
        }

        const response = await apiClient.stream(
          "/llm/chat",
          {
            messages: [...messages, userMessage].map((m) => ({
              role: m.role,
              content: m.content,
            })),
            model: selectedModel,
            provider: selectedProvider,
            stream: true,
          },
          token,
        );

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "",
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);

        if (reader) {
          let buffer = "";

          let done = false;
          while (!done) {
            const result = await reader.read();
            done = result.done || false;
            if (done) break;
            const value = result.value;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const data = line.slice(6).trim();
                if (!data || data === "[DONE]") continue;

                try {
                  const parsed = JSON.parse(data);

                  // Handle start event (provider info)
                  if (parsed.type === "start") {
                    continue;
                  }

                  // Handle error event
                  if (parsed.type === "error") {
                    toast.error(parsed.error || "Streaming error");
                    continue;
                  }

                  // Handle content from various formats
                  if (parsed.type === "content" && parsed.content) {
                    assistantMessage.content += parsed.content;
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantMessage.id
                          ? { ...assistantMessage }
                          : m,
                      ),
                    );
                  }
                  // OpenAI-style delta format (used by all providers in our backend)
                  else if (parsed.choices?.[0]?.delta?.content) {
                    assistantMessage.content += parsed.choices[0].delta.content;
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantMessage.id
                          ? { ...assistantMessage }
                          : m,
                      ),
                    );
                  }
                } catch {
                  console.warn("Failed to parse SSE data:", data);
                }
              }
            }
          }
        }
      } catch (error) {
        console.error("Chat error:", error);
        toast.error("Failed to send message");
        setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
      } finally {
        setIsLoading(false);
        setIsStreaming(false);
      }
    },
    [getToken, messages, selectedModel, selectedProvider],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isLoading,
    isStreaming,
    sendMessage,
    clearMessages,
    providers,
    selectedProvider,
    setSelectedProvider: handleProviderChange,
    models,
    selectedModel,
    setSelectedModel,
    fetchingProviders,
  };
}
