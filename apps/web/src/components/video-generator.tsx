'use client';

import { useEffect, useRef, useState } from 'react';

type GenerationState = 'idle' | 'generating' | 'done' | 'error';

interface VideoGeneratorProps {
  className?: string;
}

// Client-side ceiling for the request. Kept above the server's maxDuration
// (300s) so the server-side timeout wins first and the user sees the server's
// more informative 504 rather than a generic client-side abort.
const CLIENT_TIMEOUT_MS = 310_000;

export default function VideoGenerator({ className = '' }: VideoGeneratorProps) {
  const [prompt, setPrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [duration, setDuration] = useState(5);
  const [state, setState] = useState<GenerationState>('idle');
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoBase64, setVideoBase64] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const clearTimer = () => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  // On unmount, tear down the elapsed-time interval and abort any in-flight
  // request so it doesn't keep running (up to 5 min) or set state on an
  // unmounted component.
  useEffect(() => {
    return () => {
      clearTimer();
      abortRef.current?.abort();
    };
  }, []);

  const handleGenerate = async () => {
    if (!prompt.trim() || state === 'generating') return;

    setState('generating');
    setError(null);
    setVideoUrl(null);
    setVideoBase64(null);
    setElapsed(0);
    const t0 = Date.now();

    // Tick elapsed timer
    clearTimer();
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - t0) / 1000));
    }, 1000);

    const controller = new AbortController();
    abortRef.current = controller;
    const timeoutId = setTimeout(() => controller.abort(), CLIENT_TIMEOUT_MS);

    try {
      const res = await fetch('/api/video/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim(), aspectRatio, duration }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      clearTimer();
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error ?? `HTTP ${res.status}`);
      }

      setVideoUrl(data.video ?? null);
      setVideoBase64(data.videoBase64 ?? null);
      setState('done');
    } catch (err) {
      clearTimeout(timeoutId);
      clearTimer();
      setError(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  };

  const videoSrc = videoUrl ?? (videoBase64 ? `data:video/mp4;base64,${videoBase64}` : null);

  return (
    <div className={`bg-white/5 rounded-2xl border border-white/10 p-6 ${className}`}>
      <div className="flex items-center gap-3 mb-6">
        <span className="px-2 py-1 rounded-md text-xs font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">
          EXPERIMENTAL
        </span>
        <h2 className="text-lg font-semibold text-white">AI Video Generator</h2>
        <span className="text-xs text-white/40">Powered by Google Veo 3.1 via Vercel AI Gateway</span>
      </div>

      <div className="space-y-4">
        {/* Prompt input */}
        <div>
          <label htmlFor="video-prompt" className="block text-sm text-white/60 mb-2">Prompt</label>
          <textarea
            id="video-prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="A cinematic shot of a futuristic city at golden hour, time-lapse clouds..."
            maxLength={1000}
            rows={3}
            className="w-full px-4 py-3 bg-slate-900 rounded-xl border border-white/10 text-sm text-white/80 placeholder-white/30 resize-none focus:outline-none focus:border-purple-500/50 transition-colors"
          />
          <p className="text-xs text-white/30 mt-1 text-right">{prompt.length}/1000</p>
        </div>

        {/* Controls */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="video-aspect-ratio" className="block text-sm text-white/60 mb-2">Aspect Ratio</label>
            <select
              id="video-aspect-ratio"
              value={aspectRatio}
              onChange={(e) => setAspectRatio(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 rounded-lg border border-white/10 text-sm text-white/80 focus:outline-none focus:border-purple-500/50"
            >
              <option value="16:9">16:9 (Landscape)</option>
              <option value="9:16">9:16 (Portrait)</option>
              <option value="1:1">1:1 (Square)</option>
              <option value="4:3">4:3 (Standard)</option>
            </select>
          </div>
          <div>
            <label htmlFor="video-duration" className="block text-sm text-white/60 mb-2">Duration (seconds)</label>
            <select
              id="video-duration"
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full px-3 py-2 bg-slate-900 rounded-lg border border-white/10 text-sm text-white/80 focus:outline-none focus:border-purple-500/50"
            >
              <option value={5}>5s</option>
              <option value={8}>8s</option>
              <option value={10}>10s</option>
            </select>
          </div>
        </div>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={state === 'generating' || !prompt.trim()}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-purple-600 to-purple-700 font-medium text-sm hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {state === 'generating' ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
              Generating… {elapsed > 0 && `(${elapsed}s)`}
            </span>
          ) : (
            'Generate Video'
          )}
        </button>

        {/* Warning */}
        <p className="text-xs text-yellow-500/70 text-center">
          ⚠️ Video generation can take 1–3 minutes and requires AI_GATEWAY_API_KEY to be configured.
        </p>

        {/* Error */}
        {state === 'error' && error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Video result */}
        {state === 'done' && videoSrc && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-green-400">✅ Generation complete ({elapsed}s)</span>
              <a
                href={videoSrc}
                download="generated-video.mp4"
                aria-label="Download the generated video as an MP4 file"
                className="text-xs text-white/50 hover:text-white transition"
              >
                Download ↓
              </a>
            </div>
            <video
              src={videoSrc}
              controls
              autoPlay
              loop
              playsInline
              aria-label={`Generated video for prompt: ${prompt.trim()}`}
              className="w-full rounded-xl border border-white/10 bg-black"
            >
              <track kind="captions" label="No captions available" />
            </video>
          </div>
        )}

        {/* Idle placeholder */}
        {state === 'idle' && (
          <div className="flex items-center justify-center h-32 rounded-xl border border-white/5 bg-slate-900/50">
            <p className="text-white/20 text-sm">Generated video will appear here</p>
          </div>
        )}
      </div>
    </div>
  );
}
