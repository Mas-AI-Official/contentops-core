import { Composition } from 'remotion';
import { DaenaPromo } from './Composition';

export const RemotionRoot: React.FC = () => {
    return (
        <>
            <Composition
                id="DaenaPromo"
                component={DaenaPromo}
                durationInFrames={1950} // 65 seconds @ 30fps
                fps={30}
                width={1080}
                height={1920}
                defaultProps={{
                    assets: [],
                    audioPath: ""
                }}
            />
        </>
    );
};
