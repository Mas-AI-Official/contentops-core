import React from "react";
import {
  AbsoluteFill,
  Img,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  staticFile,
} from "remotion";

interface DaenaPresenterProps {
  avatarSrc: string;
  line: string;
  showBubble?: boolean;
}

/**
 * Daena "presenter" composition.
 * - Still PNG of Daena with subtle breathing animation (scale oscillation)
 * - Gentle bokeh/blur background behind her
 * - Optional text bubble that appears near her with the current line
 */
export const DaenaPresenter: React.FC<DaenaPresenterProps> = ({
  avatarSrc,
  line,
  showBubble = true,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // --- Breathing animation: subtle scale oscillation ---
  const breathCycle = Math.sin((frame / fps) * Math.PI * 0.8);
  const breathScale = 1.0 + breathCycle * 0.008;

  // --- Gentle vertical bob from breathing ---
  const breathY = breathCycle * 2;

  // --- Background bokeh circles animation ---
  const bokehPhase1 = (frame / fps) * 0.3;
  const bokehPhase2 = (frame / fps) * 0.5;
  const bokehPhase3 = (frame / fps) * 0.2;

  // --- Text bubble entrance ---
  const bubbleDelay = fps * 1.0;
  const bubbleOpacity = interpolate(
    frame,
    [bubbleDelay, bubbleDelay + fps * 0.5],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const bubbleSlideY = interpolate(
    frame,
    [bubbleDelay, bubbleDelay + fps * 0.5],
    [20, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // --- Avatar fade in ---
  const avatarOpacity = interpolate(
    frame,
    [0, fps * 0.5],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#0F1419" }}>
      {/* Blurred background using the same image */}
      <AbsoluteFill
        style={{
          filter: "blur(30px) brightness(0.4)",
          transform: "scale(1.2)",
        }}
      >
        <Img
          src={staticFile(avatarSrc)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </AbsoluteFill>

      {/* Bokeh circles overlay */}
      <AbsoluteFill style={{ overflow: "hidden" }}>
        {[
          { x: 15, y: 20, size: 120, phase: bokehPhase1, opacity: 0.08 },
          { x: 75, y: 35, size: 80, phase: bokehPhase2, opacity: 0.06 },
          { x: 40, y: 70, size: 160, phase: bokehPhase3, opacity: 0.05 },
          { x: 85, y: 80, size: 60, phase: bokehPhase1 + 1, opacity: 0.07 },
          { x: 20, y: 55, size: 100, phase: bokehPhase2 + 2, opacity: 0.04 },
        ].map((circle, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${circle.x}%`,
              top: `${circle.y}%`,
              width: circle.size,
              height: circle.size,
              borderRadius: "50%",
              backgroundColor: "#D4A843",
              opacity: circle.opacity + Math.sin(circle.phase) * 0.02,
              transform: `translate(${Math.sin(circle.phase) * 10}px, ${Math.cos(circle.phase) * 8}px)`,
              filter: "blur(20px)",
            }}
          />
        ))}
      </AbsoluteFill>

      {/* Dark gradient at bottom for text */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 35%)",
        }}
      />

      {/* Daena avatar with breathing */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: "50%",
          width: "90%",
          height: "85%",
          transform: `translateX(-50%) scale(${breathScale}) translateY(${breathY}px)`,
          transformOrigin: "bottom center",
          opacity: avatarOpacity,
        }}
      >
        <Img
          src={staticFile(avatarSrc)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            objectPosition: "bottom center",
          }}
        />
      </div>

      {/* Text bubble */}
      {showBubble && (
        <div
          style={{
            position: "absolute",
            top: "12%",
            left: 40,
            right: 40,
            opacity: bubbleOpacity,
            transform: `translateY(${bubbleSlideY}px)`,
          }}
        >
          <div
            style={{
              backgroundColor: "rgba(15, 20, 25, 0.85)",
              border: "1px solid rgba(212, 168, 67, 0.3)",
              borderRadius: 20,
              padding: "24px 32px",
              backdropFilter: "blur(10px)",
            }}
          >
            <p
              style={{
                fontFamily: "Inter, Arial, sans-serif",
                fontSize: 36,
                fontWeight: 500,
                color: "#FFFFFF",
                lineHeight: 1.4,
                margin: 0,
                textAlign: "center",
              }}
            >
              {line}
            </p>
          </div>
          {/* Bubble pointer */}
          <div
            style={{
              width: 0,
              height: 0,
              borderLeft: "12px solid transparent",
              borderRight: "12px solid transparent",
              borderTop: "12px solid rgba(15, 20, 25, 0.85)",
              margin: "0 auto",
            }}
          />
        </div>
      )}

      {/* Subtle gold accent line at bottom */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          left: "50%",
          transform: "translateX(-50%)",
          width: 80,
          height: 3,
          backgroundColor: "#D4A843",
          borderRadius: 2,
          opacity: 0.6,
        }}
      />
    </AbsoluteFill>
  );
};
