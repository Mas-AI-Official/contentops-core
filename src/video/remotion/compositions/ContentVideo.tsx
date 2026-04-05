import React from "react";
import {
  AbsoluteFill,
  Img,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  staticFile,
  Sequence,
  Audio,
} from "remotion";

// --- Types ---

interface SubtitleEntry {
  text: string;
  startFrame: number;
  endFrame: number;
}

interface ScriptData {
  hook: string;
  body: string;
  cta: string;
  subtitles: SubtitleEntry[];
}

interface ContentVideoProps {
  scriptData: ScriptData;
  audioSrc: string;
  avatarSrc: string;
  lifestyleImages: string[];
  platform: "reels" | "tiktok" | "shorts";
}

// --- Sub-components ---

const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      background:
        "radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.65) 100%)",
    }}
  />
);

const BottomGradient: React.FC = () => (
  <AbsoluteFill
    style={{
      background:
        "linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 30%)",
    }}
  />
);

interface ProgressBarProps {
  progress: number;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ progress }) => (
  <div
    style={{
      position: "absolute",
      bottom: 0,
      left: 0,
      width: "100%",
      height: 4,
      backgroundColor: "rgba(255,255,255,0.15)",
    }}
  >
    <div
      style={{
        width: `${progress * 100}%`,
        height: "100%",
        backgroundColor: "#2DD4BF",
        borderRadius: "0 2px 2px 0",
        transition: "none",
      }}
    />
  </div>
);

interface SubtitleDisplayProps {
  subtitles: SubtitleEntry[];
  frame: number;
}

const SubtitleDisplay: React.FC<SubtitleDisplayProps> = ({
  subtitles,
  frame,
}) => {
  const active = subtitles.find(
    (s) => frame >= s.startFrame && frame < s.endFrame
  );
  if (!active) return null;

  const localProgress = interpolate(
    frame,
    [active.startFrame, active.startFrame + 5],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        position: "absolute",
        bottom: 120,
        left: "50%",
        transform: `translateX(-50%) translateY(${(1 - localProgress) * 10}px)`,
        opacity: localProgress,
      }}
    >
      <div
        style={{
          backgroundColor: "rgba(0,0,0,0.75)",
          borderRadius: 12,
          padding: "12px 28px",
          backdropFilter: "blur(8px)",
        }}
      >
        <span
          style={{
            fontFamily: "Inter, Arial, sans-serif",
            fontSize: 42,
            fontWeight: 700,
            color: "#FFFFFF",
            textTransform: "uppercase",
            letterSpacing: 1,
          }}
        >
          {active.text}
        </span>
      </div>
    </div>
  );
};

interface KenBurnsImageProps {
  src: string;
  frame: number;
  totalFrames: number;
  direction?: "left" | "right";
}

const KenBurnsImage: React.FC<KenBurnsImageProps> = ({
  src,
  frame,
  totalFrames,
  direction = "left",
}) => {
  const scale = interpolate(frame, [0, totalFrames], [1.0, 1.12], {
    extrapolateRight: "clamp",
  });
  const panX = interpolate(
    frame,
    [0, totalFrames],
    [0, direction === "left" ? -20 : 20],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{ transform: `scale(${scale}) translateX(${panX}px)` }}
    >
      <Img
        src={staticFile(src)}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
    </AbsoluteFill>
  );
};

// --- Avatar wrapper with entrance/exit ---

interface AvatarOverlayProps {
  avatarSrc: string;
  mode: "corner" | "large" | "center";
  enterFrame: number;
  exitFrame: number;
  frame: number;
  fps: number;
  width: number;
}

const AvatarOverlay: React.FC<AvatarOverlayProps> = ({
  avatarSrc,
  mode,
  enterFrame,
  exitFrame,
  frame,
  fps,
  width,
}) => {
  const enterDuration = fps * 0.5;
  const exitDuration = fps * 0.4;

  // Entrance: slide in from right + spring scale
  const slideIn = interpolate(
    frame,
    [enterFrame, enterFrame + enterDuration],
    [300, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const enterSpring = spring({
    frame: Math.max(0, frame - enterFrame),
    fps,
    config: { damping: 14, stiffness: 90, mass: 0.7 },
  });

  // Exit: fade + slide down
  const exitOpacity = interpolate(
    frame,
    [exitFrame, exitFrame + exitDuration],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const exitSlideDown = interpolate(
    frame,
    [exitFrame, exitFrame + exitDuration],
    [0, 60],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Visibility
  if (frame < enterFrame || frame > exitFrame + exitDuration) return null;

  const isCorner = mode === "corner";
  const isCenter = mode === "center";

  const containerStyle: React.CSSProperties = {
    position: "absolute",
    bottom: 0,
    transform: `translateX(${slideIn}px) translateY(${exitSlideDown}px) scale(${0.9 + enterSpring * 0.1})`,
    opacity: exitOpacity,
    transformOrigin: "bottom center",
    ...(isCorner
      ? { right: 0, width: "40%", height: "50%" }
      : isCenter
        ? { left: "5%", width: "90%", height: "80%" }
        : { left: "5%", width: "90%", height: "75%" }),
  };

  return (
    <div style={containerStyle}>
      <Img
        src={staticFile(avatarSrc)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "contain",
          objectPosition: isCorner ? "bottom right" : "bottom center",
        }}
      />
    </div>
  );
};

// --- Main composition ---

/**
 * ContentVideo: 5-act structure for short-form content.
 *
 * Act 1 (0-3s):   Lifestyle B-roll, Daena enters from right, hook text
 * Act 2 (3-15s):  Daena in corner, B-roll illustrates topic
 * Act 3 (15-45s): Daena exits, full B-roll focus, captions only
 * Act 4 (45-55s): Daena re-enters large, emotional peak
 * Act 5 (55-60s): CTA text, Daena centered, brand colors
 *
 * Progress bar (teal #2DD4BF) at bottom.
 * Subtitles: 2-word chunks in white on dark box.
 */
export const ContentVideo: React.FC<ContentVideoProps> = ({
  scriptData,
  audioSrc,
  avatarSrc,
  lifestyleImages,
  platform,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();

  // --- Act boundaries (in frames) ---
  const act1End = fps * 3; //   0 -  3s
  const act2End = fps * 15; //  3 - 15s
  const act3End = fps * 45; // 15 - 45s
  const act4End = fps * 55; // 45 - 55s
  // act5 = 55s - end

  // --- Current B-roll image (cycle through) ---
  const brollCycleDuration = fps * 5;
  const brollIndex =
    Math.floor(frame / brollCycleDuration) % lifestyleImages.length;
  const brollLocalFrame = frame % brollCycleDuration;

  const progress = frame / durationInFrames;

  // --- Hook text (Act 1) ---
  const hookOpacity = interpolate(
    frame,
    [fps * 0.3, fps * 1, act1End - fps * 0.3, act1End],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // --- CTA text (Act 5) ---
  const ctaOpacity = interpolate(
    frame,
    [act4End, act4End + fps * 0.5],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const ctaScale = spring({
    frame: Math.max(0, frame - act4End),
    fps,
    config: { damping: 12, stiffness: 100, mass: 0.6 },
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0F1419" }}>
      {/* Optional audio */}
      {audioSrc && <Audio src={staticFile(audioSrc)} />}

      {/* B-roll background with Ken Burns */}
      <KenBurnsImage
        src={lifestyleImages[brollIndex]}
        frame={brollLocalFrame}
        totalFrames={brollCycleDuration}
        direction={brollIndex % 2 === 0 ? "left" : "right"}
      />

      {/* Cinematic overlays */}
      <Vignette />
      <BottomGradient />

      {/* Act 1: Daena enters, hook text */}
      <AvatarOverlay
        avatarSrc={avatarSrc}
        mode="large"
        enterFrame={fps * 0.5}
        exitFrame={act2End - fps * 0.5}
        frame={frame}
        fps={fps}
        width={width}
      />

      {/* Act 2: Daena in corner (overlap with act 1 exit) */}
      {frame >= act1End && frame < act2End && (
        <AvatarOverlay
          avatarSrc={avatarSrc}
          mode="corner"
          enterFrame={act1End}
          exitFrame={act2End}
          frame={frame}
          fps={fps}
          width={width}
        />
      )}

      {/* Act 4: Daena re-enters large */}
      <AvatarOverlay
        avatarSrc={avatarSrc}
        mode="large"
        enterFrame={act3End}
        exitFrame={act4End}
        frame={frame}
        fps={fps}
        width={width}
      />

      {/* Act 5: Daena centered */}
      {frame >= act4End && (
        <AvatarOverlay
          avatarSrc={avatarSrc}
          mode="center"
          enterFrame={act4End}
          exitFrame={durationInFrames}
          frame={frame}
          fps={fps}
          width={width}
        />
      )}

      {/* Hook text (Act 1) */}
      {frame < act1End + fps * 0.5 && (
        <div
          style={{
            position: "absolute",
            top: "8%",
            left: 40,
            right: 40,
            opacity: hookOpacity,
          }}
        >
          <h1
            style={{
              fontFamily: "Inter, Arial, sans-serif",
              fontSize: 48,
              fontWeight: 800,
              color: "#FFFFFF",
              textShadow: "0 4px 20px rgba(0,0,0,0.9)",
              lineHeight: 1.2,
              margin: 0,
              textAlign: "center",
            }}
          >
            {scriptData.hook}
          </h1>
        </div>
      )}

      {/* CTA text (Act 5) */}
      {frame >= act4End && (
        <div
          style={{
            position: "absolute",
            top: "10%",
            left: 40,
            right: 40,
            opacity: ctaOpacity,
            transform: `scale(${0.8 + ctaScale * 0.2})`,
          }}
        >
          <div
            style={{
              backgroundColor: "rgba(15, 20, 25, 0.9)",
              border: "2px solid #D4A843",
              borderRadius: 24,
              padding: "28px 36px",
              textAlign: "center",
            }}
          >
            <h2
              style={{
                fontFamily: "Inter, Arial, sans-serif",
                fontSize: 44,
                fontWeight: 700,
                color: "#D4A843",
                margin: 0,
                lineHeight: 1.3,
              }}
            >
              {scriptData.cta}
            </h2>
          </div>
        </div>
      )}

      {/* Subtitles (all acts) */}
      <SubtitleDisplay subtitles={scriptData.subtitles} frame={frame} />

      {/* Progress bar */}
      <ProgressBar progress={progress} />

      {/* Platform-specific safe-zone indicators (dev only) */}
    </AbsoluteFill>
  );
};
