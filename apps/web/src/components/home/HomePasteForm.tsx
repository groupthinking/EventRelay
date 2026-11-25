'use client';

import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, Link2, Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { submitHomePaste } from '@/lib/studio-handoff';

const MODES = ['Video Pack', 'Templates & Tools', 'MCP & Prompts'] as const;

/**
 * Sell-page paste field. Does not load the workbench bundle.
 * Validates a YouTube URL, kicks pack emit, then router.push('/studio?video=').
 */
export default function HomePasteForm({ variant = 'classic' }: { variant?: 'classic' | 'onramp' }) {
  const onramp = variant === 'onramp';
  const router = useRouter();
  const [value, setValue] = useState('');
  const [error, setError] = useState('');
  const [mode, setMode] = useState<(typeof MODES)[number]>(MODES[0]);
  const helpId = error ? 'home-youtube-url-error' : 'home-youtube-url-help';

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const href = submitHomePaste(value);
    if (!href) {
      setError('Need a valid YouTube URL.');
      return;
    }
    setError('');
    router.push(href);
  };

  return (
    <form
      onSubmit={onSubmit}
      toolname="extract_youtube_video_pack"
      tooldescription="Open UVAI Studio and extract a structured Video Pack, transcript, chapters, and agent workflow from a YouTube URL"
      className={onramp ? 'live-onramp-form' : 'home-composer-surface mx-auto w-full max-w-2xl'}
      data-mode={onramp ? undefined : mode}
    >
      {onramp ? null : (
      <div className="home-composer-modes" role="group" aria-label="Focus">
        {MODES.map((item) => (
          <button
            key={item}
            type="button"
            className="home-composer-mode"
            aria-pressed={mode === item}
            onClick={() => setMode(item)}
          >
            {item}
          </button>
        ))}
      </div>
      )}
      <label htmlFor="home-youtube-url" className={onramp ? 'sr-only' : 'uvai-label mb-2 block text-left'}>
        YouTube URL
      </label>
      <div className={onramp ? 'live-onramp-input' : 'template-source-input'}>
        <Link2 size={18} aria-hidden="true" className="template-source-icon" />
        <input
          id="home-youtube-url"
          name="youtubeUrl"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="https://www.youtube.com/watch?v=auJzb1D-fag"
          autoComplete="off"
          inputMode="url"
          aria-invalid={Boolean(error)}
          aria-describedby={helpId}
          className={onramp ? 'live-onramp-field' : 'uvai-input min-w-0 flex-1 font-mono text-sm'}
        />
        <button
          type="submit"
          aria-label="Build from video in Studio"
          className={onramp ? 'uvai-btn uvai-btn-primary live-onramp-submit' : 'template-send home-build-button'}
        >
          <span>Build from video</span>
          <ArrowRight size={18} aria-hidden="true" />
        </button>
      </div>
      {error ? (
        <p id="home-youtube-url-error" className="mt-2 text-left text-sm font-medium" style={{ color: 'var(--uvai-danger)' }} role="alert">
          {error}
        </p>
      ) : (
        <p id="home-youtube-url-help" className="mt-2 text-left text-xs" style={{ color: 'var(--uvai-ink-faint)' }}>
          Opens Studio to extract a Video Pack and inspect source-linked tasks. Transcript quality varies by source.
        </p>
      )}
      {onramp ? (
        <Link href="/studio?sample=1" className="live-onramp-sample" data-testid="home-try-sample">
          <Sparkles size={16} aria-hidden="true" />
          Try a sample
          <span className="live-onramp-sample-note">cached real pack · no sign-in</span>
        </Link>
      ) : null}
    </form>
  );
}
