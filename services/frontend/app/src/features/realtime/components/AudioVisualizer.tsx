import { cn } from "../../../shared/utils/cn";

interface AudioVisualizerProps {
  isActive: boolean;
  className?: string;
  barCount?: number;
}

// Small visualizer for header - uses CSS animations for smoothness
export function AudioVisualizer({
  isActive,
  className,
  barCount = 5,
}: AudioVisualizerProps) {
  return (
    <div
      className={cn("flex items-center justify-center gap-0.5 h-4", className)}
    >
      {Array.from({ length: barCount }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "w-1 rounded-full transition-all duration-300",
            isActive ? "bg-emerald-400" : "bg-gray-500",
          )}
          style={{
            height: isActive ? undefined : "4px",
            animation: isActive ? `audioBar 1s ease-in-out infinite` : "none",
            animationDelay: `${i * 0.15}s`,
          }}
        />
      ))}
      <style>{`
        @keyframes audioBar {
          0%, 100% { height: 4px; }
          50% { height: 14px; }
        }
      `}</style>
    </div>
  );
}

// Larger version for the main speaking indicator - uses CSS for smooth performance
export function AudioWaveform({
  isActive,
  className,
}: {
  isActive: boolean;
  className?: string;
}) {
  const bars = 5;

  return (
    <div
      className={cn(
        "flex items-center justify-center gap-[3px] h-5 transition-opacity duration-300",
        isActive ? "opacity-100" : "opacity-50",
        className,
      )}
    >
      {Array.from({ length: bars }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "w-[3px] rounded-full transition-colors duration-300",
            isActive ? "bg-emerald-400" : "bg-gray-500",
          )}
          style={{
            height: isActive ? undefined : "4px",
            animation: isActive
              ? `waveBar${i} 1.2s ease-in-out infinite`
              : "none",
            animationDelay: `${i * 0.1}s`,
          }}
        />
      ))}
      <style>{`
        ${Array.from({ length: bars })
          .map((_, i) => {
            const maxHeight = 4 + Math.sin((i / (bars - 1)) * Math.PI) * 14;
            return `
            @keyframes waveBar${i} {
              0%, 100% { height: 4px; }
              50% { height: ${maxHeight}px; }
            }
          `;
          })
          .join("")}
      `}</style>
    </div>
  );
}
