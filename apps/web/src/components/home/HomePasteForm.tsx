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
      <label htmlFor="home-youtube-url" className="mb-2 block text-left text-sm font-semibold text-slate-700">
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
          className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3.5 font-mono text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-amber-500 focus-visible:ring-2 focus-visible:ring-amber-500/40 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
        />
        <button
          type="submit"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-amber-600 px-6 py-3.5 text-sm font-semibold text-white shadow-sm transition hover:bg-amber-700 focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white sm:min-w-[9rem]"
        >
          Run in Studio
        </button>
      </div>
      {error ? (
        <p id="home-youtube-url-error" className="mt-2 text-left text-sm font-medium text-red-700" role="alert">
          {error}
        </p>
      ) : (
        <p id="home-youtube-url-help" className="mt-2 text-left text-xs text-slate-500">
          Opens Studio and starts the Video Pack handoff. Transcript quality varies by source.
        </p>
      )}
    </form>
  );
}
