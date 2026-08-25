'use client';

import { useState } from 'react';
import { LoaderCircle, Play } from 'lucide-react';

/**
 * Where a run starts: a video to build from, or a written idea.
 *
 * Both inputs feed the same pipeline. The video path carries a verified
 * transcript as its evidence; the idea path is honest that its evidence is the
 * text the operator typed.
 */

export interface SourceStepProps {
  onStart: (input: { sourceUrl?: string; idea?: string }) => Promise<void>;
  starting: boolean;
  error?: string | null;
}

export default function SourceStep({ onStart, starting, error }: SourceStepProps) {
  const [mode, setMode] = useState<'video' | 'idea'>('video');
  const [sourceUrl, setSourceUrl] = useState('');
  const [idea, setIdea] = useState('');

  const ready = mode === 'video' ? sourceUrl.trim().length > 0 : idea.trim().length >= 20;

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!ready || starting) return;
        void onStart(
          mode === 'video' ? { sourceUrl: sourceUrl.trim() } : { idea: idea.trim() },
        );
      }}
    >
      <div className="flex gap-2" role="tablist" aria-label="Source type">
        {(['video', 'idea'] as const).map((option) => (
          <button
            key={option}
            type="button"
            role="tab"
            aria-selected={mode === option}
            onClick={() => setMode(option)}
            className="rounded-full border px-4 py-1.5 text-xs font-medium capitalize transition-colors"
            style={{
              borderColor:
                mode === option ? 'var(--evidence-accent-strong)' : 'var(--evidence-border)',
              background: mode === option ? 'rgba(54,189,161,0.12)' : 'transparent',
              color: mode === option ? 'var(--evidence-text)' : 'var(--evidence-muted)',
            }}
          >
            {option === 'video' ? 'From video' : 'From idea'}
          </button>
        ))}
      </div>

      {mode === 'video' ? (
        <div className="flex flex-col gap-2">
          <label
            htmlFor="run-source-url"
            className="text-xs font-medium"
            style={{ color: 'var(--evidence-muted)' }}
          >
            YouTube URL
          </label>
          <input
            id="run-source-url"
            aria-describedby="run-source-url-hint"
            type="url"
            value={sourceUrl}
            onChange={(event) => setSourceUrl(event.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            className="input font-mono text-sm"
            required
          />
          <p
            id="run-source-url-hint"
            className="text-xs"
            style={{ color: 'var(--evidence-muted)' }}
          >
            The run is blocked at the first gate unless a verified transcript can be
            retrieved — no captions, no build.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <label
            htmlFor="run-idea"
            className="text-xs font-medium"
            style={{ color: 'var(--evidence-muted)' }}
          >
            What should exist when this is done?
          </label>
          <textarea
            id="run-idea"
            aria-describedby="run-idea-hint"
            value={idea}
            onChange={(event) => setIdea(event.target.value)}
            rows={5}
            placeholder="An internal tool that ingests support tickets and drafts replies for review..."
            className="input text-sm leading-relaxed"
            required
            minLength={20}
          />
          <p
            id="run-idea-hint"
            className="text-xs"
            style={{ color: 'var(--evidence-muted)' }}
          >
            {idea.trim().length} characters — 20 minimum.
          </p>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-400" role="alert">
          {error}
        </p>
      )}

      <div>
        <button
          type="submit"
          disabled={!ready || starting}
          className="evidence-primary-button inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50"
        >
          {starting ? (
            <LoaderCircle size={16} className="animate-spin" aria-hidden="true" />
          ) : (
            <Play size={16} aria-hidden="true" />
          )}
          {starting ? 'Starting run' : 'Start delivery run'}
        </button>
      </div>
    </form>
  );
}
