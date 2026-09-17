'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { submitHomePaste } from '@/lib/studio-handoff';

/**
 * Sell-page paste field. Does not load the workbench bundle.
 * Validates a YouTube URL, kicks pack emit, then router.push('/studio?video=').
 */
export default function HomePasteForm() {
  const router = useRouter();
  const [value, setValue] = useState('');
  const [error, setError] = useState('');
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
    <form onSubmit={onSubmit} className="mx-auto w-full max-w-2xl">
      <label htmlFor="home-youtube-url" className="mb-2 block text-left text-sm font-semibold text-white/80">
        YouTube URL
      </label>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
        <input
          id="home-youtube-url"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="https://www.youtube.com/watch?v=auJzb1D-fag"
          autoComplete="off"
          inputMode="url"
          aria-invalid={Boolean(error)}
          aria-describedby={helpId}
          className="min-w-0 flex-1 rounded-xl border border-white/15 bg-black/40 px-4 py-3.5 font-mono text-sm text-white outline-none placeholder:text-white/30 focus:border-teal-400/70 focus-visible:ring-2 focus-visible:ring-teal-300/80 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-950"
        />
        <button
          type="submit"
          className="btn btn-primary justify-center px-6 py-3.5 text-sm focus-visible:ring-2 focus-visible:ring-teal-200 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-950 sm:min-w-[9rem]"
        >
          Run in Studio
        </button>
      </div>
      {error ? (
        <p id="home-youtube-url-error" className="mt-2 text-left text-sm text-amber-300/90" role="alert">
          {error}
        </p>
      ) : (
        <p id="home-youtube-url-help" className="mt-2 text-left text-xs text-white/55">
          Opens Studio and starts the Video Pack handoff. Transcript quality varies by source.
        </p>
      )}
    </form>
  );
}
