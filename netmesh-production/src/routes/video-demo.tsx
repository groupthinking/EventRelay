import { AppleVideoPlayer } from '@/components/video/AppleVideoPlayer';

export default function VideoPlayerPage() {
    return (
        <div className="container mx-auto py-10 px-4">
            <div className="mb-6">
                <h1 className="text-2xl font-bold tracking-tight mb-2">Video Analysis Output</h1>
                <p className="text-muted-foreground">Apple-style playback with 'Context' overlay for chapters/insights.</p>
            </div>
            <AppleVideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            />
        </div>
    );
}
