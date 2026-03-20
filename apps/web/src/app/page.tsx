'use client';

import Link from 'next/link';
import { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { useRouter } from 'next/navigation';
import { useToast } from '@/components/ui/Toast';

// ─── URL Validation ────────────────────────────────────────────────────────────
function validateVideoUrl(url: string): string | null {
  if (!url.trim()) {
    return 'Please enter a video URL';
  }

  try {
    // Try to parse as URL
    new URL(url);
  } catch {
    return 'Please enter a valid URL';
  }

  // Check if it's a recognized video platform
  const videoPatterns = [
    /youtube\.com/i,
    /youtu\.be/i,
    /drive\.google\.com/i,
    /vimeo\.com/i,
    /loom\.com/i,
    /\.mp4$/i,
    /\.webm$/i,
  ];

  if (!videoPatterns.some(pattern => pattern.test(url))) {
    return 'URL must be from a supported platform (YouTube, Google Drive, Vimeo, etc.) or a direct video link';
  }

  return null;
}

const STEPS = [
  { icon: '🔗', title: 'Paste a Video URL', desc: 'Drop any YouTube link — tutorials, talks, walkthroughs' },
  { icon: '🧠', title: 'AI Watches & Understands', desc: 'Gemini analyzes the video content, extracts technologies, concepts, and structure' },
  { icon: '🚀', title: 'Get Insights & Code', desc: 'Receive a full breakdown — summary, actions, topics, and generated project scaffold' },
];

const EXAMPLES = [
  { url: 'https://www.youtube.com/watch?v=aircAruvnKk', label: '3Blue1Brown — Neural Networks' },
  { url: 'https://www.youtube.com/watch?v=zjkBMFhNj_g', label: 'Tech Tutorial' },
];

export default function Home() {
  const [videoUrl, setVideoUrl] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [pasting, setPasting] = useState(false);
  const router = useRouter();
  const typedWord = useTypewriter(USE_CASES);
  const { addToast } = useToast();

  const handleProcess = useCallback(() => {
    const error = validateVideoUrl(videoUrl);
    if (error) {
      setUrlError(error);
      return;
    }
    setUrlError(null);
    router.push(`/dashboard?video=${encodeURIComponent(videoUrl)}`);
  }, [videoUrl, router]);

  const handleUrlChange = useCallback((value: string) => {
    setVideoUrl(value);
    if (urlError) setUrlError(null); // clear error on change
  }, []);

  const handlePasteFromClipboard = useCallback(async () => {
    try {
      setPasting(true);
      const text = await navigator.clipboard.readText();
      if (text.trim()) {
        setVideoUrl(text.trim());
        setUrlError(null);
        addToast('Pasted from clipboard', 'success');
      } else {
        addToast('Clipboard is empty', 'warning');
      }
    } catch {
      addToast('Could not access clipboard — paste manually', 'error');
    } finally {
      setPasting(false);
    }
  }, [addToast]);

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
            API
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-3xl mx-auto px-6 pt-20 pb-12 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/60 mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Powered by Gemini &amp; Vertex AI
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
              type="url"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              placeholder="https://youtube.com/watch?v=..."
              className="flex-1 px-4 py-3 bg-transparent text-white placeholder:text-white/30 focus:outline-none text-sm"
            />
            {/* Paste from clipboard */}
            <button
              type="button"
              onClick={handlePasteFromClipboard}
              disabled={pasting}
              title="Paste from clipboard"
              className="btn btn-ghost py-3 px-3 text-white/40 hover:text-white/70 disabled:opacity-40"
            >
              {pasting ? (
                <span className="inline-block animate-spin text-xs">⏳</span>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              )}
            </button>
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
              className="text-xs px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-primary-400/80 hover:text-primary-400 hover:border-primary-500/30 transition"
            >
              {label}
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
          <span>EventRelay • Agentic Video Execution Platform</span>
          <div className="flex items-center gap-4">
            <Link href="/playground" className="hover:text-white/50 transition">API</Link>
            <a href="https://github.com/groupthinking/EventRelay" target="_blank" rel="noopener noreferrer" className="hover:text-white/50 transition">GitHub</a>
          </div>
        </div>
      </div>
    </div>
  );
}