import { AbsoluteFill, Sequence, Video, Audio, useVideoConfig, useCurrentFrame, interpolate, Img } from 'remotion';

export const DaenaPromo: React.FC<{
    assets: string[];
    audioPath: string;
    logoPath?: string;
}> = ({ assets, audioPath, logoPath }) => {
    const { fps, durationInFrames, width, height } = useVideoConfig();
    const frame = useCurrentFrame();

    const clipDuration = assets.length > 0 ? durationInFrames / assets.length : durationInFrames;

    // Animation for the overlay
    const opacity = interpolate(frame, [0, 30], [0, 1], {
        extrapolateRight: 'clamp',
    });

    return (
        <AbsoluteFill style={{ backgroundColor: '#0A1128' }}>
            {/* Dynamic Background with Neon Green Accent */}
            <div style={{
                position: 'absolute',
                width: '100%',
                height: '100%',
                background: 'radial-gradient(circle at 50% 50%, #1a1c2c 0%, #000 100%)',
            }} />

            {/* Video Sequences */}
            {assets.map((src, i) => (
                <Sequence key={i} from={Math.round(i * clipDuration)} durationInFrames={Math.round(clipDuration)}>
                    <Video
                        src={src}
                        muted
                        style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover',
                            filter: 'brightness(0.8)',
                            transform: `scale(${interpolate(frame % clipDuration, [0, clipDuration], [1, 1.05])})`
                        }}
                    />
                </Sequence>
            ))}

            {/* Logo Watermark (Top Right) */}
            {logoPath && (
                <div style={{
                    position: 'absolute',
                    top: '60px',
                    right: '60px',
                    width: '320px',
                    opacity: 0.9,
                    filter: 'drop-shadow(0 0 10px rgba(0,0,0,0.5))'
                }}>
                    <Img src={logoPath} style={{ width: '100%' }} />
                </div>
            )}

            {/* Glassmorphism Title Card at bottom */}
            <AbsoluteFill style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'flex-end',
                alignItems: 'center',
                paddingBottom: '200px',
                opacity: opacity
            }}>
                <div style={{
                    width: '90%',
                    padding: '40px',
                    background: 'rgba(0, 0, 0, 0.4)',
                    backdropFilter: 'blur(20px) saturate(180%)',
                    WebkitBackdropFilter: 'blur(20px) saturate(180%)',
                    borderRadius: '32px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    boxShadow: '0 20px 50px rgba(0, 0, 0, 0.5)',
                    textAlign: 'center'
                }}>
                    <h1 style={{
                        color: '#FFD700', // Gold color to match logo
                        fontSize: '90px',
                        margin: '0 0 10px 0',
                        fontFamily: 'system-ui, -apple-system, sans-serif',
                        textShadow: '0 0 30px rgba(255, 215, 0, 0.3)',
                        letterSpacing: '-2px',
                        fontWeight: 900
                    }}>
                        DAENA GAO
                    </h1>
                    <p style={{
                        color: '#FFF',
                        fontSize: '36px',
                        margin: 0,
                        textTransform: 'uppercase',
                        letterSpacing: '8px',
                        opacity: 0.9,
                        fontWeight: 400
                    }}>
                        GOVERNED AGENT OPERATIONS
                    </p>
                </div>
            </AbsoluteFill>

            {/* Main Audio */}
            {audioPath && <Audio src={audioPath} />}
        </AbsoluteFill>
    );
};
