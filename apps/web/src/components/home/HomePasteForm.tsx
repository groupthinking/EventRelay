'use client';

import { FormEvent, useState } from 'react';
import { ArrowUp, Link2 } from 'lucide-react';
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
      <label htmlFor="home-youtube-url" className="uvai-label mb-2 block text-left">
        YouTube URL
      </label>
      <div className="template-source-input">
        <Link2 size={18} aria-hidden="true" className="template-source-icon" />
        <input
          id="home-youtube-url"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="https://www.youtube.com/watch?v=auJzb1D-fag"
          autoComplete="off"
          inputMode="url"
          aria-invalid={Boolean(error)}
          aria-describedby={helpId}
          className="uvai-input min-w-0 flex-1 font-mono text-sm"
        />
        <button
          type="submit"
          aria-label="Run in Studio"
          className="template-send"
        >
          <ArrowUp size={20} aria-hidden="true" />
        </button>
      </div>
      {error ? (
        <p id="home-youtube-url-error" className="mt-2 text-left text-sm font-medium" style={{ color: 'var(--uvai-danger)' }} role="alert">
          {error}
        </p>
      ) : (
        <p id="home-youtube-url-help" className="mt-2 text-left text-xs" style={{ color: 'var(--uvai-ink-faint)' }}>
          Opens Studio and starts the Video Pack handoff. Transcript quality varies by source.
        </p>
      )}
    </form>
  );
}
