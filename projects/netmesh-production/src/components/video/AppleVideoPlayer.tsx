import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize, Minimize, Settings, SkipForward, SkipBack, Layers } from 'lucide-react';
import { Slider } from '@/components/ui/slider';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

interface Chapter {
    time: number;
    label: string;
    description?: string;
}

interface AppleVideoPlayerProps {
    src: string;
    poster?: string;
    chapters?: Chapter[];
    onOverlayTrigger?: () => void;
}

// Mock Chapters if none provided
const MOCK_CHAPTERS = [
    { time: 0, label: "Intro", description: "Welcome to the tutorial" },
    { time: 120, label: "Installation", description: "Setting up the environment" },
    { time: 340, label: "Configuration", description: "API Keys and Secrets" },
    { time: 600, label: "Deployment", description: "Going live on Vercel" },
];

export function AppleVideoPlayer({ src, poster, chapters = MOCK_CHAPTERS, onOverlayTrigger }: AppleVideoPlayerProps) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [progress, setProgress] = useState(0);
    const [duration, setDuration] = useState(0);
    const [volume, setVolume] = useState(1);
    const [isMuted, setIsMuted] = useState(false);
    const [showControls, setShowControls] = useState(true);
    const [showChapters, setShowChapters] = useState(false);
    const controlsTimeoutRef = useRef<NodeJS.Timeout>();

    const formatTime = (time: number) => {
        const minutes = Math.floor(time / 60);
        const seconds = Math.floor(time % 60);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    };

    const togglePlay = () => {
        if (videoRef.current) {
            if (isPlaying) {
                videoRef.current.pause();
            } else {
                videoRef.current.play();
            }
            setIsPlaying(!isPlaying);
        }
    };

    const handleTimeUpdate = () => {
        if (videoRef.current) {
            setProgress(videoRef.current.currentTime);
        }
    };

    const handleLoadedMetadata = () => {
        if (videoRef.current) {
            setDuration(videoRef.current.duration);
        }
    };

    const handleSeek = (value: number[]) => {
        if (videoRef.current) {
            videoRef.current.currentTime = value[0];
            setProgress(value[0]);
        }
    };

    const handleVolumeChange = (value: number[]) => {
        if (videoRef.current) {
            videoRef.current.volume = value[0];
            setVolume(value[0]);
            setIsMuted(value[0] === 0);
        }
    };

    const handleMouseMove = () => {
        setShowControls(true);
        if (controlsTimeoutRef.current) {
            clearTimeout(controlsTimeoutRef.current);
        }
        controlsTimeoutRef.current = setTimeout(() => {
            if (isPlaying) setShowControls(false);
        }, 2500);
    };

    return (
        <div
            className="relative group rounded-xl overflow-hidden shadow-2xl bg-black aspect-video w-full max-w-5xl mx-auto border border-white/10"
            onMouseMove={handleMouseMove}
            onMouseLeave={() => isPlaying && setShowControls(false)}
        >
            <video
                ref={videoRef}
                src={src || "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"} // Fallback mock video
                poster={poster}
                className="w-full h-full object-cover"
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onClick={togglePlay}
            />

            {/* Chapters Overlay (Apple/X-Ray Style) */}
            <div className={cn(
                "absolute right-0 top-0 bottom-0 w-80 bg-black/80 backdrop-blur-xl border-l border-white/10 p-6 transition-transform duration-300 ease-out z-20",
                showChapters ? "translate-x-0" : "translate-x-full"
            )}>
                <h3 className="text-lg font-semibold mb-4 text-white">Chapters</h3>
                <ScrollArea className="h-[calc(100%-3rem)] pr-4">
                    <div className="space-y-4">
                        {chapters.map((chapter, i) => (
                            <div
                                key={i}
                                className={cn(
                                    "p-3 rounded-lg cursor-pointer transition-colors hover:bg-white/10",
                                    progress >= chapter.time && progress < (chapters[i + 1]?.time || duration) ? "bg-white/20 border-l-2 border-[#0092b8]" : ""
                                )}
                                onClick={() => {
                                    if (videoRef.current) videoRef.current.currentTime = chapter.time;
                                    setProgress(chapter.time);
                                }}
                            >
                                <div className="flex justify-between text-sm text-gray-300 mb-1">
                                    <span className="font-medium text-white">{chapter.label}</span>
                                    <span className="font-mono text-xs">{formatTime(chapter.time)}</span>
                                </div>
                                <p className="text-xs text-gray-400 line-clamp-2">{chapter.description}</p>
                            </div>
                        ))}
                    </div>
                </ScrollArea>
            </div>

            {/* Main Controls Overlay */}
            <div className={cn(
                "absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent transition-opacity duration-300 flex flex-col justify-end p-6 z-10",
                showControls ? "opacity-100" : "opacity-0 pointer-events-none"
            )}>

                {/* Progress Bar (Apple Style - Hover to expand) */}
                <div className="mb-4 group/slider relative">
                    {/* Visual Chapters markers on timeline */}
                    <div className="absolute top-1/2 left-0 w-full h-1 -translate-y-1/2 pointer-events-none px-1">
                        {chapters.slice(1).map((c, i) => (
                            <div
                                key={i}
                                className="absolute w-0.5 h-2 bg-white/50 z-10"
                                style={{ left: `${(c.time / duration) * 100}%` }}
                            />
                        ))}
                    </div>

                    <Slider
                        value={[progress]}
                        max={duration}
                        step={1}
                        onValueChange={handleSeek}
                        className="cursor-pointer"
                    />
                </div>

                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button size="icon" variant="ghost" className="text-white hover:bg-white/20 rounded-full h-10 w-10" onClick={togglePlay}>
                            {isPlaying ? <Pause className="h-6 w-6 fill-current" /> : <Play className="h-6 w-6 fill-current" />}
                        </Button>

                        <div className="flex items-center gap-2 group/vol">
                            <Button size="icon" variant="ghost" className="text-white hover:bg-white/20 rounded-full h-8 w-8" onClick={() => setIsMuted(!isMuted)}>
                                {isMuted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
                            </Button>
                            <div className="w-0 overflow-hidden group-hover/vol:w-24 transition-all duration-300">
                                <Slider value={[isMuted ? 0 : volume]} max={1} step={0.1} onValueChange={handleVolumeChange} className="w-20" />
                            </div>
                        </div>

                        <span className="text-sm font-medium text-white/90 tabular-nums">
                            {formatTime(progress)} / {formatTime(duration)}
                        </span>
                    </div>

                    <div className="flex items-center gap-2">
                        <Button
                            size="sm"
                            variant="ghost"
                            className={cn("text-white hover:bg-white/20 gap-2 rounded-full", showChapters && "bg-white/20 text-[#0092b8]")}
                            onClick={() => setShowChapters(!showChapters)}
                        >
                            <Layers className="h-4 w-4" />
                            <span className="hidden sm:inline">Context</span>
                        </Button>

                        <Button size="icon" variant="ghost" className="text-white hover:bg-white/20 rounded-full h-8 w-8">
                            <Settings className="h-5 w-5" />
                        </Button>

                        <Button size="icon" variant="ghost" className="text-white hover:bg-white/20 rounded-full h-8 w-8" onClick={() =>
                            document.fullscreenElement ? document.exitFullscreen() : videoRef.current?.parentElement?.requestFullscreen()
                        }>
                            <Maximize className="h-5 w-5" />
                        </Button>
                    </div>
                </div>
            </div>

            {/* Center Play Button (Youtube/Apple style when paused) */}
            {!isPlaying && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="bg-black/40 backdrop-blur-sm p-6 rounded-full border border-white/20 shadow-2xl scale-100 hover:scale-110 transition-transform duration-200">
                        <Play className="h-12 w-12 text-white fill-white ml-1" />
                    </div>
                </div>
            )}

        </div>
    );
}
