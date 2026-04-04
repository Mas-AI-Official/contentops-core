import { Composition } from "remotion";
import { DaenaLifestyle } from "./compositions/DaenaLifestyle";
import { DaenaPresenter } from "./compositions/DaenaPresenter";
import { ContentVideo } from "./compositions/ContentVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="DaenaLifestyle"
        component={DaenaLifestyle}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          images: [
            "data/assets/daena/casual/penthouse_back_full_room.png",
            "data/assets/daena/casual/penthouse_back_livingroom.png",
            "data/assets/daena/casual/penthouse_sitting_window.png",
          ],
          avatarSrc: "data/assets/daena/casual/penthouse_standing_confident.png",
          hookText: "What if your AI actually understood you?",
        }}
      />

      <Composition
        id="DaenaPresenter"
        component={DaenaPresenter}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          avatarSrc: "data/assets/daena/casual/penthouse_standing_confident.png",
          line: "Meet Daena. Your governed AI partner.",
          showBubble: true,
        }}
      />

      <Composition
        id="ContentVideo"
        component={ContentVideo}
        durationInFrames={1800}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          scriptData: {
            hook: "What if your AI actually understood you?",
            body: "Daena governs every action. Every decision is auditable.",
            cta: "Try Daena free today.",
            subtitles: [
              { text: "What if", startFrame: 0, endFrame: 30 },
              { text: "your AI", startFrame: 30, endFrame: 60 },
              { text: "actually understood", startFrame: 60, endFrame: 90 },
              { text: "you?", startFrame: 90, endFrame: 120 },
            ],
          },
          audioSrc: "",
          avatarSrc:
            "data/assets/daena/casual/penthouse_standing_confident.png",
          lifestyleImages: [
            "data/assets/daena/casual/penthouse_back_full_room.png",
            "data/assets/daena/casual/penthouse_back_livingroom.png",
            "data/assets/daena/casual/penthouse_sitting_window.png",
            "data/assets/daena/casual/penthouse_standing_front_smile.png",
          ],
          platform: "reels" as const,
        }}
      />
    </>
  );
};
