import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ProgressSpinner } from '../ui/progress-spinner';

interface VideoPreviewProps {
  file: File;
  className?: string;
  showMetadata?: boolean;
  showControls?: boolean;
  autoPlay?: boolean;
  muted?: boolean;
  loop?: boolean;
  onVideoLoad?: (duration: number, dimensions: { width: number; height: number }) => void;
  onError?: (error: string) => void;
}

interface VideoMetadata {
  duration: number;
  width: number;
  height: number;
  bitrate?: number;
  codec?: string;
  frameRate?: number;
}

const VideoPreview: React.FC<VideoPreviewProps> = ({
  file,
  className = '',
  showMetadata = true,
  showControls = true,
  autoPlay = false,
  muted = true,
  loop = false,
  onVideoLoad,
  onError
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null);
  const [thumbnail, setThumbnail] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(muted);

  // Generate video URL
  const videoUrl = URL.createObjectURL(file);

  // Generate thumbnail
  const generateThumbnail = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    if (!ctx) return;

    // Set canvas dimensions to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Seek to 25% of video for thumbnail
    const seekTime = video.duration * 0.25;
    video.currentTime = seekTime;

    // Wait for seek to complete
    const handleSeeked = () => {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const thumbnailDataUrl = canvas.toDataURL('image/jpeg', 0.8);
      setThumbnail(thumbnailDataUrl);
      video.removeEventListener('seeked', handleSeeked);
    };

    video.addEventListener('seeked', handleSeeked);
  }, []);

  // Handle video load
  const handleVideoLoad = useCallback(() => {
    if (!videoRef.current) return;

    const video = videoRef.current;
    const videoMetadata: VideoMetadata = {
      duration: video.duration,
      width: video.videoWidth,
      height: video.videoHeight
    };

    setMetadata(videoMetadata);
    setDuration(video.duration);
    setIsLoading(false);
    onVideoLoad?.(video.duration, { width: video.videoWidth, height: video.videoHeight });

    // Generate thumbnail after a short delay
    setTimeout(generateThumbnail, 100);
  }, [onVideoLoad, generateThumbnail]);

  // Handle video error
  const handleVideoError = useCallback((e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    const errorMessage = 'Failed to load video';
    setError(errorMessage);
    setIsLoading(false);
    onError?.(errorMessage);
  }, [onError]);

  // Handle time update
  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  }, []);

  // Handle play/pause
  const handlePlayPause = useCallback(() => {
    if (!videoRef.current) return;

    if (isPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play();
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying]);

  // Handle seek
  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (!videoRef.current) return;

    const seekTime = parseFloat(e.target.value);
    videoRef.current.currentTime = seekTime;
    setCurrentTime(seekTime);
  }, []);

  // Handle volume change
  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (!videoRef.current) return;

    const newVolume = parseFloat(e.target.value);
    videoRef.current.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  }, []);

  // Handle mute toggle
  const handleMuteToggle = useCallback(() => {
    if (!videoRef.current) return;

    if (isMuted) {
      videoRef.current.volume = volume;
      setIsMuted(false);
    } else {
      videoRef.current.volume = 0;
      setIsMuted(true);
    }
  }, [isMuted, volume]);

  // Format time
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      URL.revokeObjectURL(videoUrl);
    };
  }, [videoUrl]);

  if (error) {
    return (
      <div className={`p-6 bg-red-50 border border-red-200 rounded-lg text-center ${className}`}>
        <div className="text-red-500 text-4xl mb-2">❌</div>
        <h3 className="text-lg font-semibold text-red-700 mb-2">Video Load Error</h3>
        <p className="text-red-600">{error}</p>
        <p className="text-sm text-red-500 mt-2">File: {file.name}</p>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-lg overflow-hidden ${className}`}>
      {/* Video Container */}
      <div className="relative bg-black">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-center">
              <ProgressSpinner size="lg" />
              <p className="mt-2 text-white">Loading video...</p>
            </div>
          </div>
        )}

        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-auto max-h-96"
          onLoadedMetadata={handleVideoLoad}
          onError={handleVideoError}
          onTimeUpdate={handleTimeUpdate}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          autoPlay={autoPlay}
          muted={muted}
          loop={loop}
          controls={false}
        />

        {/* Custom Controls Overlay */}
        {showControls && !isLoading && (
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
            {/* Play/Pause Button */}
            <button
              onClick={handlePlayPause}
              className="bg-white/20 hover:bg-white/30 text-white rounded-full p-2 transition-colors"
            >
              {isPlaying ? '⏸️' : '▶️'}
            </button>

            {/* Progress Bar */}
            <div className="mt-2 flex items-center space-x-2">
              <span className="text-white text-xs">{formatTime(currentTime)}</span>
              <input
                type="range"
                min="0"
                max={duration || 0}
                value={currentTime}
                onChange={handleSeek}
                className="flex-1 h-1 bg-white/30 rounded-full appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, white ${(currentTime / (duration || 1)) * 100}%, transparent 0%)`
                }}
              />
              <span className="text-white text-xs">{formatTime(duration)}</span>
            </div>

            {/* Volume Controls */}
            <div className="mt-2 flex items-center space-x-2">
              <button
                onClick={handleMuteToggle}
                className="text-white text-sm hover:text-gray-300 transition-colors"
              >
                {isMuted ? '🔇' : '🔊'}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="w-20 h-1 bg-white/30 rounded-full appearance-none cursor-pointer"
              />
            </div>
          </div>
        )}
      </div>

      {/* Metadata Section */}
      {showMetadata && metadata && (
        <div className="p-4 border-t border-gray-200">
          <h3 className="font-semibold text-gray-800 mb-3">Video Information</h3>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-600">File Name:</p>
              <p className="font-medium text-gray-800 truncate">{file.name}</p>
            </div>
            
            <div>
              <p className="text-gray-600">File Size:</p>
              <p className="font-medium text-gray-800">{formatFileSize(file.size)}</p>
            </div>
            
            <div>
              <p className="text-gray-600">Duration:</p>
              <p className="font-medium text-gray-800">{formatTime(metadata.duration)}</p>
            </div>
            
            <div>
              <p className="text-gray-600">Resolution:</p>
              <p className="font-medium text-gray-800">{metadata.width} × {metadata.height}</p>
            </div>
            
            <div>
              <p className="text-gray-600">Format:</p>
              <p className="font-medium text-gray-800">{file.type || 'Unknown'}</p>
            </div>
            
            <div>
              <p className="text-gray-600">Last Modified:</p>
              <p className="font-medium text-gray-800">
                {new Date(file.lastModified).toLocaleDateString()}
              </p>
            </div>
          </div>

          {/* Thumbnail */}
          {thumbnail && (
            <div className="mt-4">
              <p className="text-gray-600 mb-2">Thumbnail:</p>
              <img
                src={thumbnail}
                alt="Video thumbnail"
                className="w-32 h-20 object-cover rounded border border-gray-200"
              />
            </div>
          )}
        </div>
      )}

      {/* Hidden canvas for thumbnail generation */}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
};

export default VideoPreview;
