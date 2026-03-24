'use client';

import Link from 'next/link';
import { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { useRouter } from 'next/navigation';
import { ArrowRight } from 'lucide-react';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';

const STEPS = [
  { num: '01', title: 'Paste a Video URL', desc: 'Drop any YouTube link — tutorials, talks, walkthroughs' },
  { num: '02', title: 'AI Watches & Understands', desc: 'Gemini analyzes the video content, extracts technologies, concepts, and structure' },
  { num: '03', title: 'Get Insights & Code', desc: 'Receive a full breakdown — summary, actions, topics, and generated project scaffold' },
];

const EXAMPLES = [
  { url: 'https://www.youtube.com/watch?v=aircAruvnKk', label: '3Blue1Brown — Neural Networks' },
  { url: 'https://www.youtube.com/watch?v=zjkBMFhNj_g', label: 'Tech Tutorial' },
];

export default function Home() {
  const [videoUrl, setVideoUrl] = useState('');
  const router = useRouter();

  const handleProcess = useCallback(() => {
    if (!videoUrl.trim()) return;
    router.push(`/dashboard?video=${encodeURIComponent(videoUrl)}`);
  }, [videoUrl, router]);

  return (
    <div className="min-h-screen text-white flex flex-col">
      <Nav />

      {/* Hero */}
      <div className="max-w-3xl mx-auto px-6 pt-20 pb-12">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/60 mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Open source &bull; Self-hostable
        </div>

        <h1 className="text-4xl md:text-5xl font-black leading-tight mb-4 font-heading">
          Video → <span className="gradient-text">Software</span>
        </h1>
        <p className="text-white/40 text-lg max-w-xl mb-10 leading-relaxed">
          Paste a YouTube URL. AI analyzes the content, extracts every technology, concept, and action item — then generates a project scaffold you can deploy.
        </p>

        {/* Input */}
        <form
          onSubmit={(e) => { e.preventDefault(); handleProcess(); }}
          className="max-w-2xl mx-auto"
        >
          <div className="flex gap-3 p-2 rounded-2xl bg-white/[0.04] border border-white/[0.08] focus-within:border-primary-500/40 focus-within:shadow-lg focus-within:shadow-primary-500/5 transition-all">
            <input
              type="text"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              placeholder="https://youtube.com/watch?v=..."
              className="flex-1 px-4 py-3 bg-transparent text-white placeholder:text-white/30 focus:outline-none text-sm"
            />
            <button
              type="submit"
              disabled={!videoUrl.trim()}
              className="btn btn-primary py-3 px-8 disabled:opacity-30 disabled:cursor-not-allowed group relative"
              title={!videoUrl.trim() ? 'Paste a YouTube URL first' : undefined}
            >
              Process Video
            </button>
          </div>
          {/* F-009: Hint text when button is disabled */}
          {!videoUrl.trim() && (
            <p className="text-xs text-white/20 mt-2 ml-2">Paste a YouTube URL above to get started</p>
          )}
        </form>

        {/* Example URLs */}
        <div className="flex flex-wrap items-center gap-3 mt-5">
          <span className="text-xs text-white/30">Try:</span>
          {EXAMPLES.map(({ url, label }) => (
            <button
              key={url}
              onClick={() => { setVideoUrl(url); }}
              className="text-xs px-4 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-primary-400/80 hover:text-primary-400 hover:border-primary-500/30 transition"
            >
              {label}
            </button>
          ))}
        </div>

        <div className="mt-6 flex">
          <Link
            href="/prototype"
            className="inline-flex items-center gap-2 rounded-full border border-primary-500/25 bg-primary-500/10 px-4 py-2 text-sm font-medium text-primary-200 transition hover:border-primary-500/40 hover:bg-primary-500/15"
          >
            Open the clickable product prototype
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {/* How it works */}
      <div className="max-w-2xl mx-auto px-6 pb-20 flex-1">
        <div className="space-y-0">
          {STEPS.map((step, i) => (
            <div
              key={step.title}
              className={clsx(
                'flex items-start gap-5 py-5',
                i < STEPS.length - 1 && 'border-b border-white/[0.06]',
                'animate-fade-in-up opacity-0'
              )}
              style={{ animationDelay: `${i * 150}ms`, animationFillMode: 'forwards' }}
            >
              <span className="text-sm font-mono text-primary-400 pt-0.5 shrink-0">{step.num}</span>
              <div>
                <h2 className="font-semibold text-white mb-1 text-left text-base font-heading">{step.title}</h2>
                <p className="text-sm text-white/40 leading-relaxed text-left">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <Footer variant="compact" />
    </div>
  );
}

