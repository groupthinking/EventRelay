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
      <label htmlFor="home-youtube-url" className="sr-only">
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
          className="min-w-0 flex-1 rounded-xl border border-white/15 bg-black/40 px-4 py-3.5 font-mono text-sm text-white outline-none placeholder:text-white/30 focus:border-teal-400/70"
        />
        <button
          type="submit"
          className="btn btn-primary justify-center px-6 py-3.5 text-sm sm:min-w-[9rem]"
        >
          Run in Studio
        </button>
      </div>
      {error ? (
        <p className="mt-2 text-sm text-amber-300/90" role="alert">
          {error}
        </p>
      ) : (
        <p className="mt-2 text-xs text-white/40">
          Lands in Studio and starts the live video pack / analysis path.
        </p>
      )}
    </form>
  );
}
