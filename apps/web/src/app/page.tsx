'use client';

import Link from 'next/link';
import { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { useRouter } from 'next/navigation';

const STEPS = [
  { icon: '🔗', title: 'Paste a URL', desc: 'YouTube, Google Drive, or any video link' },
  { icon: '🧠', title: 'AI Analysis', desc: 'Transcript, events, actions, and insights extracted' },
  { icon: '⚡', title: 'Get Results', desc: 'Structured data you can search, export, and act on' },
];

const EXAMPLES = [
  'https://www.youtube.com/watch?v=aircAruvnKk',
  'https://www.youtube.com/watch?v=zjkBMFhNj_g',
];

export default function Home() {
  const [videoUrl, setVideoUrl] = useState('');
  const router = useRouter();

  const handleProcess = useCallback(() => {
    if (!videoUrl.trim()) return;
    router.push(`/dashboard?video=${encodeURIComponent(videoUrl)}`);
  }, [videoUrl, router]);

  return (
    <div className="min-h-screen text-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 lg:px-12 py-4 border-b border-white/[0.05]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-lg shadow-lg shadow-primary-500/25">
            E
          </div>
          <span className="font-bold text-xl tracking-tight">EventRelay</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="btn btn-secondary py-2 text-sm">
            Dashboard
          </Link>
          <Link href="/playground" className="btn btn-ghost py-2 text-sm text-white/50">
            API Docs
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-3xl mx-auto px-6 pt-20 pb-12 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/60 mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Gemini + OpenAI • Real-time Processing
        </div>

        <h1 className="text-4xl md:text-5xl font-black leading-tight mb-4">
          Video → <span className="gradient-text">Intelligence</span>
        </h1>
        <p className="text-white/40 text-lg max-w-xl mx-auto mb-10 leading-relaxed">
          Paste a video URL and get transcripts, events, actions, and AI-powered insights in seconds.
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
              placeholder="Paste a YouTube URL..."
              className="flex-1 px-4 py-3 bg-transparent text-white placeholder:text-white/30 focus:outline-none text-sm"
            />
            <button
              type="submit"
              disabled={!videoUrl.trim()}
              className="btn btn-primary py-3 px-8 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Analyze
            </button>
          </div>
        </form>

        {/* Example URLs */}
        <div className="flex flex-wrap items-center justify-center gap-2 mt-4">
          <span className="text-xs text-white/30">Try:</span>
          {EXAMPLES.map((url) => (
            <button
              key={url}
              onClick={() => { setVideoUrl(url); }}
              className="text-xs text-primary-400/70 hover:text-primary-400 transition truncate max-w-[200px]"
            >
              {url.replace('https://www.youtube.com/watch?v=', 'youtu.be/')}
            </button>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div className="max-w-3xl mx-auto px-6 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {STEPS.map((step, i) => (
            <div
              key={step.title}
              className={clsx(
                'relative p-6 rounded-2xl bg-white/[0.03] border border-white/[0.06]',
                'animate-fade-in-up opacity-0'
              )}
              style={{ animationDelay: `${i * 150}ms`, animationFillMode: 'forwards' }}
            >
              <div className="text-3xl mb-3">{step.icon}</div>
              <div className="text-xs text-white/30 font-semibold uppercase tracking-wider mb-1">
                Step {i + 1}
              </div>
              <h3 className="font-bold text-white mb-1">{step.title}</h3>
              <p className="text-sm text-white/40 leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-white/[0.06] py-6">
        <div className="max-w-3xl mx-auto px-6 flex items-center justify-between text-xs text-white/25">
          <span>EventRelay • AI Video Intelligence</span>
          <div className="flex items-center gap-4">
            <Link href="/playground" className="hover:text-white/50 transition">API</Link>
            <a href="https://github.com/groupthinking/EventRelay" target="_blank" rel="noopener noreferrer" className="hover:text-white/50 transition">GitHub</a>
          </div>
        </div>
      </div>
    </div>
  );
}