'use client';

import { useState } from 'react';

type GenerationState = 'idle' | 'generating' | 'complete' | 'error';

export default function VideoGenerator() {
  const [prompt, setPrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [duration, setDuration] = useState(5);
  const [state, setState] = useState<GenerationState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);

  async function handleGenerate() {
    if (!prompt.trim() || state === 'generating') return;

    setState('generating');
    setError(null);
    setVideoSrc(null);

    try {
      const response = await fetch('/api/video/generate', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          aspectRatio,
          duration,
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}`);
      }

      const nextVideoSrc = data.videoUrl
        || (data.videoBase64 ? `data:video/mp4;base64,${data.videoBase64}` : null);

      if (!nextVideoSrc) {
        throw new Error('No video output returned.');
      }

      setVideoSrc(nextVideoSrc);
      setState('complete');
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Video generation failed.');
      setState('error');
    }
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">AI Video Generator</h3>
        <p className="mt-1 text-sm text-white/60">
          Generate short experimental clips through the Vercel AI Gateway.
        </p>
      </div>

      <div className="space-y-4">
        <textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Describe the video you want to generate..."
          className="min-h-32 w-full rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-primary-500/50"
        />

        <div className="grid gap-4 md:grid-cols-3">
          <label className="space-y-2 text-sm text-white/70">
            <span>Aspect ratio</span>
            <select
              value={aspectRatio}
              onChange={(event) => setAspectRatio(event.target.value)}
              className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-white"
            >
              <option value="16:9">16:9</option>
              <option value="9:16">9:16</option>
              <option value="1:1">1:1</option>
            </select>
          </label>

          <label className="space-y-2 text-sm text-white/70">
            <span>Duration (seconds)</span>
            <input
              type="number"
              min={1}
              max={10}
              value={duration}
              onChange={(event) => setDuration(Number(event.target.value) || 5)}
              className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-white"
            />
          </label>

          <div className="space-y-2 text-sm text-white/70">
            <span>Status</span>
            <div className="rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-white">
              {state}
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={handleGenerate}
          disabled={!prompt.trim() || state === 'generating'}
          className="rounded-xl bg-primary-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-primary-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {state === 'generating' ? 'Generating…' : 'Generate video'}
        </button>

        {error ? (
          <p className="text-sm text-red-300">{error}</p>
        ) : null}

        {videoSrc ? (
          <video
            controls
            className="w-full rounded-xl border border-white/10 bg-black"
            src={videoSrc}
          >
            Your browser does not support the video tag.
          </video>
        ) : null}
      </div>
    </section>
  );
}
