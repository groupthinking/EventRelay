'use client';

import { useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowRight, Link2, Sparkles } from 'lucide-react';
import AppShell from '@/components/AppShell';
import Footer from '@/components/Footer';
import { submitHomePaste } from '@/lib/studio-handoff';
import {
  INTENTS,
  SHOWCASE_CARDS,
  SHOWCASE_CATEGORIES,
  SHOWCASE_SAMPLE_URL,
  type IntentId,
} from './showcase-data';
import '@/styles/project-workspace-home.css';

/**
 * Plan 005 P1 Home. One source video per run: the dock accepts a YouTube URL
 * plus an intent chip and hands off to Studio. It never opens a general chat.
 */
export default function ProjectWorkspaceHome() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [url, setUrl] = useState('');
  const [intent, setIntent] = useState<IntentId>('tasks');
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [category, setCategory] = useState<(typeof SHOWCASE_CATEGORIES)[number]>('All');

  const helpId = error ? 'home-dock-error' : 'home-dock-help';
  const cards =
    category === 'All' ? SHOWCASE_CARDS : SHOWCASE_CARDS.filter((card) => card.category === category);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const href = submitHomePaste(url);
    if (!href) {
      setError('Paste a valid YouTube URL to start a Video Pack run, or try the sample below.');
      return;
    }
    setError('');
    router.push(`${href}&intent=${intent}`);
  };

  const pickCard = (cardId: string) => {
    const card = SHOWCASE_CARDS.find((item) => item.id === cardId);
    if (!card) return;
    setIntent(card.intent);
    if (!url.trim()) setUrl(SHOWCASE_SAMPLE_URL);
    setError('');
    const label = INTENTS.find((item) => item.id === card.intent)?.label ?? card.intent;
    setStatus(`Selected ${card.title} (${label}). Paste your YouTube URL or start with the sample.`);
    inputRef.current?.focus();
  };

  return (
    <AppShell>
      <main className="pwh" data-testid="project-workspace-home">
        <section className="pwh-hero" aria-labelledby="home-heading">
          <p className="pwh-kicker">
            <span className="pwh-dot" aria-hidden="true" />
            Universal Video Action Intelligence
          </p>
          <h1 id="home-heading" className="pwh-title">
            What are we building from video today?
          </h1>
          <p className="pwh-lede">
            Paste a YouTube URL and pick an intent to open a hashed Video Pack run in Studio.
            Transcript quality varies by source.
          </p>

          <form className="pwh-dock" onSubmit={onSubmit} noValidate>
            <label htmlFor="home-dock-input" className="sr-only">
              YouTube URL
            </label>
            <div className="pwh-dock-field">
              <Link2 size={18} aria-hidden="true" />
              <input
                ref={inputRef}
                id="home-dock-input"
                name="youtubeUrl"
                type="url"
                inputMode="url"
                autoComplete="off"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="Paste a YouTube URL"
                aria-invalid={Boolean(error)}
                aria-describedby={helpId}
              />
            </div>

            <div className="pwh-intents" role="group" aria-label="Workflow intent">
              {INTENTS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="pwh-chip"
                  aria-pressed={intent === item.id}
                  onClick={() => setIntent(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="pwh-dock-footer">
              <span className="pwh-pill">Auto · Video Pack</span>
              <Link href="/studio?sample=1" className="pwh-sample">
                <Sparkles size={14} aria-hidden="true" />
                Try a sample
              </Link>
              <button type="submit" className="uvai-btn uvai-btn-primary pwh-submit">
                <span>Start in Studio</span>
                <ArrowRight size={16} aria-hidden="true" />
              </button>
            </div>

            {error ? (
              <p id="home-dock-error" className="pwh-error" role="alert">
                {error}
              </p>
            ) : (
              <p id="home-dock-help" className="pwh-help">
                One source video per project. Checks stay proposed until they run.
              </p>
            )}
            <p className="pwh-status" aria-live="polite">
              {status}
            </p>
          </form>

          <ul className="pwh-links" aria-label="More ways in">
            <li>
              <Link href="/#showcase">Skills</Link>
            </li>
            <li>
              <Link href="/docs/api#endpoints">Connectors (MCP)</Link>
            </li>
            <li>
              <Link href="/pricing">Pricing</Link>
            </li>
          </ul>
        </section>

        <section id="showcase" className="pwh-showcase" aria-labelledby="showcase-heading">
          <h2 id="showcase-heading" className="pwh-section-title">
            What you can build from one video
          </h2>
          <div className="pwh-tabs" role="tablist" aria-label="Showcase categories">
            {SHOWCASE_CATEGORIES.map((item) => (
              <button
                key={item}
                type="button"
                role="tab"
                id={`showcase-tab-${item}`}
                aria-selected={category === item}
                aria-controls="showcase-panel"
                className="pwh-tab"
                onClick={() => setCategory(item)}
              >
                {item}
              </button>
            ))}
          </div>
          <div
            id="showcase-panel"
            role="tabpanel"
            aria-labelledby={`showcase-tab-${category}`}
            className="pwh-grid"
          >
            {cards.map((card) => (
              <button
                key={card.id}
                type="button"
                className="pwh-card"
                data-testid="showcase-card"
                data-category={card.category}
                data-tone={card.tone}
                onClick={() => pickCard(card.id)}
              >
                <span className="pwh-card-head">
                  <span className="pwh-card-category">{card.category}</span>
                  <span className="pwh-card-kind" data-kind={card.kind}>
                    {card.kind}
                  </span>
                </span>
                <span className="pwh-card-title">{card.title}</span>
                <span className="pwh-card-desc">{card.description}</span>
              </button>
            ))}
          </div>
        </section>

        <Footer variant="compact" />
      </main>
    </AppShell>
  );
}
