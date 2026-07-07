'use client';

import { useState } from 'react';

type GenerationState = 'idle' | 'generating' | 'complete' | 'error';

interface VideoResult {
  base64?: string;
  mediaType?: string;
  error?: string;
}

export function VideoGenerator() {
  const [prompt, setPrompt] = useState('');
  const [state, setState] = useState<GenerationState>('idle');
  const [result, setResult] = useState<VideoResult | null>(null);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setState('generating');
    setResult(null);

    try {
      const response = await fetch('/api/video/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim() }),
      });

      const data = await response.json();
      if (!response.ok) {
        setState('error');
        setResult({ error: data.error || 'Generation failed' });
        return;
      }

      setState('complete');
      setResult(data);
    } catch (err) {
      setState('error');
      setResult({ error: err instanceof Error ? err.message : 'Network error' });
    }
  };

  const videoSrc = result?.base64 ? `data:${result.mediaType || 'video/mp4'};base64,${result.base64}` : null;

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the video you want to generate..."
          aria-label="Video generation prompt"
          className="flex-1 px-4 py-3 bg-surface-900 rounded-xl border border-white/10 text-white/80 placeholder:text-white/30 focus:outline-none focus:border-primary-500/50"
          maxLength={1000}
          disabled={state === 'generating'}
        />
        <button
          onClick={handleGenerate}
          disabled={state === 'generating' || !prompt.trim()}
          className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 font-medium text-white disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition"
        >
          {state === 'generating' ? 'Generating...' : 'Generate'}
        </button>
      </div>

      {state === 'generating' && (
        <div className="flex items-center justify-center h-48 bg-surface-900 rounded-xl border border-white/10">
          <div className="text-center">
            <div className="w-10 h-10 rounded-full border-4 border-purple-500 border-t-transparent animate-spin mx-auto mb-3" />
            <p className="text-white/60 text-sm">Generating video (this may take a few minutes)...</p>
          </div>
        </div>
      )}

      {state === 'error' && result?.error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
          <p className="text-red-400 text-sm">{result.error}</p>
        </div>
      )}

      {state === 'complete' && videoSrc && (
        <div className="rounded-xl overflow-hidden border border-white/10">
          <video
            src={videoSrc}
            controls
            className="w-full max-h-96"
            autoPlay
            muted
          />
        </div>
      )}
    </div>
  );
}
