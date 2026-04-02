import { useState, useCallback, useRef, useEffect } from "react";
import { useAuth } from "@clerk/clerk-react";
import { toast } from "sonner";

// Types for realtime events
interface RealtimeEvent {
  type: string;
  agent?: string;
  tool?: string;
  output?: string;
  audio?: string;
  error?: string;
  history?: HistoryItem[];
  item?: HistoryItem;
  from?: string;
  to?: string;
}

interface HistoryItem {
  id?: string;
  type?: string;
  role?: string;
  content?: ContentPart[];
}

interface ContentPart {
  type: string;
  text?: string;
  transcript?: string;
  audio?: string;
}

export interface TranscriptMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface UseRealtimeAgentReturn {
  // Connection state
  isConnected: boolean;
  isConnecting: boolean;
  connectionError: string | null;

  // Audio state
  isRecording: boolean;
  isSpeaking: boolean;

  // Transcript
  messages: TranscriptMessage[];
  currentAgentName: string;

  // Actions
  connect: () => Promise<void>;
  disconnect: () => void;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  sendTextMessage: (text: string) => void;
  interrupt: () => void;
  clearMessages: () => void;

  // Session
  sessionId: string;
}

const generateSessionId = () => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

// Get WebSocket URL based on environment
const getWebSocketUrl = (sessionId: string): string => {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || "";

  if (backendUrl) {
    // Production: convert HTTP URL to WebSocket URL
    const wsUrl = backendUrl.replace(/^http/, "ws");
    return `${wsUrl}/api/realtime/ws/${sessionId}`;
  }

  // Local development: use current host with ws protocol
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/api/realtime/ws/${sessionId}`;
};

// Audio player class that handles playback in a non-blocking way
class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private gainNode: GainNode | null = null;
  private scheduledTime = 0;
  private isPlaying = false;
  private onPlayingChange: (playing: boolean) => void;
  private checkInterval: number | null = null;

  constructor(onPlayingChange: (playing: boolean) => void) {
    this.onPlayingChange = onPlayingChange;
  }

  private ensureContext() {
    if (!this.audioContext || this.audioContext.state === "closed") {
      this.audioContext = new AudioContext({ sampleRate: 24000 });
      this.gainNode = this.audioContext.createGain();
      this.gainNode.connect(this.audioContext.destination);
      this.scheduledTime = this.audioContext.currentTime;
    }
    if (this.audioContext.state === "suspended") {
      this.audioContext.resume();
    }
    return this.audioContext;
  }

  // Decode base64 to ArrayBuffer without blocking - uses fetch API
  private async decodeBase64(base64: string): Promise<ArrayBuffer> {
    const response = await fetch(
      `data:application/octet-stream;base64,${base64}`,
    );
    return response.arrayBuffer();
  }

  async playAudio(base64Audio: string) {
    try {
      const ctx = this.ensureContext();

      // Decode base64 using fetch (non-blocking)
      const arrayBuffer = await this.decodeBase64(base64Audio);
      const int16Array = new Int16Array(arrayBuffer);

      // Convert to float32 for Web Audio
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768;
      }

      // Create audio buffer
      const audioBuffer = ctx.createBuffer(1, float32Array.length, 24000);
      audioBuffer.getChannelData(0).set(float32Array);

      // Create and schedule source
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.gainNode!);

      // Schedule playback
      const startTime = Math.max(ctx.currentTime + 0.05, this.scheduledTime);
      source.start(startTime);
      this.scheduledTime = startTime + audioBuffer.duration;

      // Update playing state
      if (!this.isPlaying) {
        this.isPlaying = true;
        this.onPlayingChange(true);
        this.startPlayingCheck();
      }
    } catch (error) {
      console.error("Error playing audio:", error);
    }
  }

  private startPlayingCheck() {
    if (this.checkInterval) return;

    this.checkInterval = window.setInterval(() => {
      if (
        this.audioContext &&
        this.audioContext.currentTime >= this.scheduledTime - 0.1
      ) {
        this.isPlaying = false;
        this.onPlayingChange(false);
        if (this.checkInterval) {
          clearInterval(this.checkInterval);
          this.checkInterval = null;
        }
      }
    }, 100);
  }

  interrupt() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }

    if (this.audioContext && this.audioContext.state !== "closed") {
      // Fade out quickly to avoid clicks
      if (this.gainNode) {
        this.gainNode.gain.setValueAtTime(
          this.gainNode.gain.value,
          this.audioContext.currentTime,
        );
        this.gainNode.gain.linearRampToValueAtTime(
          0,
          this.audioContext.currentTime + 0.05,
        );
      }

      // Close and reset after fade
      setTimeout(() => {
        if (this.audioContext && this.audioContext.state !== "closed") {
          this.audioContext.close();
        }
        this.audioContext = null;
        this.gainNode = null;
        this.scheduledTime = 0;
      }, 60);
    }

    this.isPlaying = false;
    this.onPlayingChange(false);
  }

  destroy() {
    this.interrupt();
  }
}

export function useRealtimeAgent(): UseRealtimeAgentReturn {
  const { getToken } = useAuth();

  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Audio state
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  // Messages
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [currentAgentName, setCurrentAgentName] = useState("Assistant");

  // Session
  const [sessionId] = useState(() => generateSessionId());

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const audioPlayerRef = useRef<AudioPlayer | null>(null);

  // Initialize audio player
  useEffect(() => {
    audioPlayerRef.current = new AudioPlayer(setIsSpeaking);
    return () => {
      audioPlayerRef.current?.destroy();
    };
  }, []);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data: RealtimeEvent = JSON.parse(event.data);

      switch (data.type) {
        case "agent_start":
          if (data.agent) {
            setCurrentAgentName(data.agent);
          }
          break;

        case "audio":
          if (data.audio && audioPlayerRef.current) {
            // Queue audio for playback - this is now non-blocking
            audioPlayerRef.current.playAudio(data.audio);
          }
          break;

        case "audio_end":
          // Agent finished speaking this segment
          break;

        case "audio_interrupted":
          // Interrupt playback
          audioPlayerRef.current?.interrupt();
          break;

        case "tool_start":
          console.log(`Tool started: ${data.tool}`);
          break;

        case "tool_end":
          console.log(`Tool ended: ${data.tool} - ${data.output}`);
          break;

        case "handoff":
          if (data.to) {
            setCurrentAgentName(data.to);
            toast.info(`Transferred to ${data.to}`);
          }
          break;

        case "history_updated":
          // Full history update - replace all messages
          if (data.history) {
            const newMessages: TranscriptMessage[] = [];
            for (const item of data.history) {
              if (item.role && item.content) {
                const textContent = item.content
                  .filter(
                    (c: ContentPart) =>
                      c.type === "text" || c.type === "input_text",
                  )
                  .map((c: ContentPart) => c.text || "")
                  .join("");

                const transcript = item.content
                  .filter((c: ContentPart) => c.transcript)
                  .map((c: ContentPart) => c.transcript || "")
                  .join("");

                const content = textContent || transcript;
                if (content) {
                  newMessages.push({
                    id: item.id || `msg-${Date.now()}-${Math.random()}`,
                    role: item.role as "user" | "assistant",
                    content,
                    timestamp: new Date(),
                  });
                }
              }
            }
            if (newMessages.length > 0) {
              setMessages(newMessages);
            }
          }
          break;

        case "history_added":
          // Single item added - append or update streaming message
          if (data.item) {
            const item = data.item;
            if (item.role && item.content) {
              const textContent = item.content
                .filter(
                  (c: ContentPart) =>
                    c.type === "text" || c.type === "input_text",
                )
                .map((c: ContentPart) => c.text || "")
                .join("");

              const transcript = item.content
                .filter((c: ContentPart) => c.transcript)
                .map((c: ContentPart) => c.transcript || "")
                .join("");

              const content = textContent || transcript;
              if (content) {
                const msgId = item.id || `msg-${Date.now()}`;
                setMessages((prev) => {
                  // Check if this message already exists (update it)
                  const existingIndex = prev.findIndex((m) => m.id === msgId);
                  if (existingIndex >= 0) {
                    const updated = [...prev];
                    updated[existingIndex] = {
                      ...updated[existingIndex],
                      content,
                    };
                    return updated;
                  }
                  // New message - append
                  return [
                    ...prev,
                    {
                      id: msgId,
                      role: item.role as "user" | "assistant",
                      content,
                      timestamp: new Date(),
                    },
                  ];
                });
              }
            }
          }
          break;

        case "error":
          console.error("Realtime error:", data.error);
          toast.error(data.error || "An error occurred");
          break;
      }
    } catch (error) {
      console.error("Error parsing WebSocket message:", error);
    }
  }, []);

  // Connect to WebSocket
  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsConnecting(true);
    setConnectionError(null);

    try {
      const token = await getToken();
      if (!token) {
        throw new Error("Authentication required");
      }

      const wsUrl = getWebSocketUrl(sessionId);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
        toast.success("Connected to realtime agent");
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        setIsRecording(false);
        audioPlayerRef.current?.interrupt();

        if (event.code !== 1000) {
          const reason = event.reason || "Connection closed";
          setConnectionError(reason);
          toast.error(`Disconnected: ${reason}`);
        }
      };

      ws.onerror = () => {
        setConnectionError("WebSocket error");
        setIsConnecting(false);
      };

      ws.onmessage = handleMessage;

      wsRef.current = ws;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to connect";
      setConnectionError(message);
      setIsConnecting(false);
      toast.error(message);
    }
  }, [getToken, sessionId, handleMessage]);

  // Disconnect
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, "User disconnected");
      wsRef.current = null;
    }

    // Stop recording if active
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    // Close recording audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    // Stop playback
    audioPlayerRef.current?.interrupt();

    setIsConnected(false);
    setIsRecording(false);
  }, []);

  // Start recording
  const startRecording = useCallback(async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      toast.error("Not connected");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 24000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      mediaStreamRef.current = stream;

      // Create audio context for processing
      const audioContext = new AudioContext({ sampleRate: 24000 });
      audioContextRef.current = audioContext;

      // Load audio worklet for processing
      await audioContext.audioWorklet.addModule(
        URL.createObjectURL(
          new Blob(
            [
              `
              class AudioProcessor extends AudioWorkletProcessor {
                constructor() {
                  super();
                }

                process(inputs) {
                  const input = inputs[0];
                  if (input && input[0]) {
                    const samples = input[0];
                    // Convert Float32 to Int16
                    const int16 = new Int16Array(samples.length);
                    for (let i = 0; i < samples.length; i++) {
                      const s = Math.max(-1, Math.min(1, samples[i]));
                      int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                    }
                    this.port.postMessage(Array.from(int16));
                  }
                  return true;
                }
              }
              registerProcessor('audio-processor', AudioProcessor);
            `,
            ],
            { type: "application/javascript" },
          ),
        ),
      );

      const source = audioContext.createMediaStreamSource(stream);
      const workletNode = new AudioWorkletNode(audioContext, "audio-processor");

      workletNode.port.onmessage = (event) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({
              type: "audio",
              data: event.data,
            }),
          );
        }
      };

      source.connect(workletNode);
      // Don't connect to destination - we don't want to hear ourselves
      workletNodeRef.current = workletNode;

      setIsRecording(true);
    } catch (error) {
      console.error("Error starting recording:", error);
      toast.error("Failed to access microphone");
    }
  }, []);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Audio commitment is handled automatically by server-side VAD

    setIsRecording(false);
  }, []);

  // Send text message
  const sendTextMessage = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      toast.error("Not connected");
      return;
    }

    const trimmed = text.trim();
    if (!trimmed) return;

    // Add user message to transcript immediately
    const userMessage: TranscriptMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    wsRef.current.send(
      JSON.stringify({
        type: "text",
        text: trimmed,
      }),
    );
  }, []);

  // Interrupt agent
  const interrupt = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "interrupt" }));
    }

    audioPlayerRef.current?.interrupt();
  }, []);

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
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
  };
}
