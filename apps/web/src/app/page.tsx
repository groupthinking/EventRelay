'use client';

import Link from 'next/link';
import { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { useRouter } from 'next/navigation';
import { ArrowRight } from 'lucide-react';

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
    <div className="min-h-screen text-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 lg:px-12 py-4 border-b border-white/[0.05]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-lg shadow-lg shadow-primary-500/25">
            U
          </div>
          <span className="font-bold text-xl tracking-tight">UVAI</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="btn btn-secondary py-2 text-sm">
            Dashboard
          </Link>
          <Link href="/prototype" className="btn btn-secondary py-2 text-sm">
            Prototype
          </Link>
          <Link href="/playground" className="btn btn-ghost py-2 text-sm text-white/50">
            API
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-3xl mx-auto px-6 pt-20 pb-12 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/60 mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Open source &bull; Self-hostable
        </div>

        <h1 className="text-4xl md:text-5xl font-black leading-tight mb-4">
          Video → <span className="gradient-text">Software</span>
        </h1>
        <p className="text-white/40 text-lg max-w-xl mx-auto mb-10 leading-relaxed">
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
              className="btn btn-primary py-3 px-8 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Process Video
            </button>
          </div>
        </form>

        {/* Example URLs */}
        <div className="flex flex-wrap items-center justify-center gap-3 mt-5">
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

        <div className="mt-6 flex justify-center">
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
      <div className="max-w-2xl mx-auto px-6 pb-20">
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
                <h2 className="font-semibold text-white mb-1 text-left text-base">{step.title}</h2>
                <p className="text-sm text-white/40 leading-relaxed text-left">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-white/[0.06] py-6">
        <div className="max-w-3xl mx-auto px-6 flex items-center justify-between text-xs text-white/25">
          <span>UVAI • Video to Software</span>
          <div className="flex items-center gap-4">
            <Link href="/playground" className="hover:text-white/50 transition py-2 px-1">API</Link>
            <a href="https://github.com/groupthinking/EventRelay" target="_blank" rel="noopener noreferrer" className="hover:text-white/50 transition py-2 px-1">GitHub</a>
          </div>
        </div>
      </div>
    </div>
  );
}
