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
} from "remotion";

interface DaenaLifestyleProps {
  images: string[];
  avatarSrc: string;
  hookText: string;
}

/**
 * Ken Burns cinematic lifestyle composition.
 * - Zooms + pans across penthouse images
 * - 3D parallax: foreground shifts faster than background
 * - Daena avatar slides in from right, holds, then fades out
 * - Dark vignette overlay
 * - Hook text overlay
 */
export const DaenaLifestyle: React.FC<DaenaLifestyleProps> = ({
  images,
  avatarSrc,
  hookText,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();

  // --- Ken Burns on background image ---
  const imageIndex = Math.floor(
    (frame / durationInFrames) * images.length
  ) % images.length;

  const kenBurnsScale = interpolate(
    frame,
    [0, durationInFrames],
    [1.0, 1.15],
    { extrapolateRight: "clamp" }
  );

  const kenBurnsPanX = interpolate(
    frame,
    [0, durationInFrames],
    [0, -30],
    { extrapolateRight: "clamp" }
  );

  const kenBurnsPanY = interpolate(
    frame,
    [0, durationInFrames],
    [0, -15],
    { extrapolateRight: "clamp" }
  );

  // --- 3D Parallax layers ---
  const bgParallaxX = interpolate(frame, [0, durationInFrames], [0, -10], {
    extrapolateRight: "clamp",
  });
  const fgParallaxX = interpolate(frame, [0, durationInFrames], [0, -25], {
    extrapolateRight: "clamp",
  });

  // --- Avatar entrance/exit ---
  const avatarEnterStart = Math.floor(durationInFrames * 0.2);
  const avatarEnterEnd = Math.floor(durationInFrames * 0.3);
  const avatarExitStart = Math.floor(durationInFrames * 0.7);
  const avatarExitEnd = Math.floor(durationInFrames * 0.85);

  const avatarSlideX = interpolate(
    frame,
    [avatarEnterStart, avatarEnterEnd, avatarExitStart, avatarExitEnd],
    [width, width * 0.55, width * 0.55, width * 0.55],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const avatarSpringScale = spring({
    frame: frame - avatarEnterStart,
    fps,
    config: { damping: 12, stiffness: 80, mass: 0.8 },
  });

  const avatarScale = interpolate(
    frame,
    [avatarEnterStart, avatarEnterEnd],
    [0.85, 1.0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const avatarOpacity = interpolate(
    frame,
    [avatarExitStart, avatarExitEnd],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const avatarSlideDown = interpolate(
    frame,
    [avatarExitStart, avatarExitEnd],
    [0, 80],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // --- Hook text fade in ---
  const textOpacity = interpolate(
    frame,
    [fps * 0.5, fps * 1.5],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#0F1419" }}>
      {/* Background layer with Ken Burns */}
      <AbsoluteFill
        style={{
          transform: `scale(${kenBurnsScale}) translate(${kenBurnsPanX + bgParallaxX}px, ${kenBurnsPanY}px)`,
        }}
      >
        <Img
          src={staticFile(images[imageIndex])}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </AbsoluteFill>

      {/* Foreground parallax layer (duplicated image, shifted) */}
      <AbsoluteFill
        style={{
          transform: `translateX(${fgParallaxX}px)`,
          opacity: 0.15,
          mixBlendMode: "screen",
        }}
      >
        <Img
          src={staticFile(images[(imageIndex + 1) % images.length])}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </AbsoluteFill>

      {/* Dark vignette overlay */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.7) 100%)",
        }}
      />

      {/* Bottom gradient for text readability */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 40%)",
        }}
      />

      {/* Daena avatar */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: "100%",
          height: "80%",
          transform: `translateX(${avatarSlideX - width * 0.55}px) translateY(${avatarSlideDown}px) scale(${avatarScale * (0.85 + avatarSpringScale * 0.15)})`,
          opacity: avatarOpacity,
          transformOrigin: "bottom center",
        }}
      >
        <Img
          src={staticFile(avatarSrc)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            objectPosition: "bottom right",
          }}
        />
      </div>

      {/* Hook text */}
      <div
        style={{
          position: "absolute",
          bottom: 180,
          left: 40,
          right: 40,
          opacity: textOpacity,
        }}
      >
        <h1
          style={{
            fontFamily: "Inter, Arial, sans-serif",
            fontSize: 52,
            fontWeight: 700,
            color: "#FFFFFF",
            textShadow: "0 4px 20px rgba(0,0,0,0.8)",
            lineHeight: 1.2,
            margin: 0,
          }}
        >
          {hookText}
        </h1>
        <div
          style={{
            width: 60,
            height: 4,
            backgroundColor: "#D4A843",
            marginTop: 16,
            borderRadius: 2,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
