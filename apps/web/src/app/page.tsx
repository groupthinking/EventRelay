'use client';

import Link from 'next/link';
import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';

/* ═══════════════════════════════════════════
   UVAI Landing — Video-Media-First Design
   Generated via Google Stitch MCP (PRO_AGENT)
   Adapted to Next.js / CSS Variables
   ═══════════════════════════════════════════ */

const INSIGHTS = [
  { icon: '⏱', text: 'Action identified: API setup tutorial at 02:14', tag: 'ACTION', color: 'teal' },
  { icon: '🎯', text: 'Key concept: Neural network backpropagation', tag: 'TOPIC', color: 'teal' },
  { icon: '⚡', text: 'Code snippet detected: Python TensorFlow model', tag: 'CODE', color: 'cyan' },
  { icon: '⚠️', text: 'Complexity spike at segment 3 — advanced content', tag: 'ALERT', color: 'amber' },
];

const STATS = [
  { value: '10K+', label: 'Videos Processed' },
  { value: '500ms', label: 'Response Time' },
  { value: '98%', label: 'Accuracy Rate' },
  { value: '50+', label: 'AI Agents Active' },
];

const FEATURES = [
  {
    title: 'Transcript Extraction',
    description: 'Sub-second precision timestamps with speaker diarization and language detection.',
    icon: '📝',
  },
  {
    title: 'Action Item Mining',
    description: 'AI identifies every task, recommendation, and next step mentioned in the video.',
    icon: '✅',
  },
  {
    title: 'Scene Intelligence',
    description: 'Visual timeline segmentation with topic clustering and emotional arc mapping.',
    icon: '🎬',
  },
];

export default function Home() {
  const [videoUrl, setVideoUrl] = useState('');
  const [activeInsight, setActiveInsight] = useState(0);
  const router = useRouter();

  const handleProcess = useCallback(() => {
    if (!videoUrl.trim()) return;
    router.push(`/dashboard?video=${encodeURIComponent(videoUrl)}`);
  }, [videoUrl, router]);

  // Cycle through insights for the demo animation
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveInsight((prev) => (prev + 1) % INSIGHTS.length);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen text-white" style={{ background: '#0e0e13' }}>
      {/* ─── NAV ─── */}
      <nav
        className="fixed top-0 w-full z-50"
        style={{
          background: 'rgba(14, 14, 19, 0.8)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
        }}
      >
        <div className="flex justify-between items-center px-6 py-4 max-w-[1440px] mx-auto">
          <Link href="/" className="text-2xl font-black tracking-tighter font-heading" style={{ color: '#6af2de' }}>
            UVAI
          </Link>
          <div className="hidden md:flex gap-8 items-center">
            {['Features', 'Pricing', 'Dashboard'].map((link) => (
              <Link
                key={link}
                href={`/${link.toLowerCase()}`}
                className="text-sm tracking-wide uppercase transition-colors duration-300 hover:opacity-100"
                style={{ color: 'rgba(248,245,253,0.5)', fontFamily: 'var(--font-body)' }}
              >
                {link}
              </Link>
            ))}
          </div>
          <Link
            href="/dashboard"
            className="px-6 py-2 rounded-md font-bold text-sm transition-all duration-300 active:scale-95"
            style={{
              background: 'linear-gradient(135deg, #6af2de, #10b7a5)',
              color: '#002b26',
            }}
          >
            Launch App
          </Link>
        </div>
      </nav>

      <main className="pt-24 overflow-x-hidden">
        {/* ─── HERO ─── */}
        <section
          className="relative min-h-[90vh] flex flex-col items-center justify-center px-6"
          style={{
            background: 'radial-gradient(circle at 50% 40%, rgba(106, 242, 222, 0.06) 0%, transparent 65%)',
          }}
        >
          {/* Badge */}
          <span
            className="text-xs tracking-[0.3em] uppercase mb-6 block"
            style={{ color: '#6af2de', fontFamily: 'var(--font-body)' }}
          >
            Video Intelligence Engine
          </span>

          {/* Headline */}
          <h1
            className="font-heading text-5xl md:text-7xl font-bold tracking-tighter mb-6 leading-[1.05] text-center"
            style={{ color: '#f8f5fd' }}
          >
            Video to{' '}
            <span
              className="bg-clip-text"
              style={{
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundImage: 'linear-gradient(135deg, #6af2de, #38fbf7)',
              }}
            >
              Intelligence
            </span>
            <br />
            in 60 seconds
          </h1>

          <p className="text-lg md:text-xl max-w-2xl mx-auto text-center leading-relaxed mb-10" style={{ color: 'rgba(248,245,253,0.5)' }}>
            Paste any YouTube URL. Our neural engine extracts every concept, action item, and insight — and generates deployable project scaffolds.
          </p>

          {/* URL Input */}
          <form
            onSubmit={(e) => { e.preventDefault(); handleProcess(); }}
            className="w-full max-w-2xl mb-12"
          >
            <div
              className="flex gap-2 p-2 rounded-xl transition-all duration-300"
              style={{
                background: 'rgba(25, 25, 31, 0.8)',
                border: '1px solid rgba(106, 242, 222, 0.15)',
                boxShadow: videoUrl ? '0 0 30px rgba(106, 242, 222, 0.1)' : 'none',
              }}
            >
              <input
                type="text"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="https://youtube.com/watch?v=..."
                className="flex-1 px-4 py-3 bg-transparent text-white placeholder:text-white/20 focus:outline-none text-sm"
              />
              <button
                type="submit"
                disabled={!videoUrl.trim()}
                className="px-8 py-3 rounded-lg font-bold text-sm transition-all duration-300 active:scale-95 disabled:opacity-30"
                style={{
                  background: 'linear-gradient(135deg, #6af2de, #10b7a5)',
                  color: '#002b26',
                }}
              >
                Analyze Footage
              </button>
            </div>
          </form>

          {/* ─── PRODUCT MOCKUP (THE STAR) ─── */}
          <div className="relative w-full max-w-5xl group">
            {/* Glow backdrop */}
            <div
              className="absolute -inset-2 rounded-2xl blur-3xl opacity-40 group-hover:opacity-70 transition-opacity duration-1000"
              style={{ background: 'linear-gradient(135deg, rgba(106,242,222,0.15), rgba(32,192,255,0.1))' }}
            />

            {/* Main card */}
            <div
              className="relative rounded-2xl overflow-hidden shadow-2xl"
              style={{
                background: 'rgba(19, 19, 24, 0.9)',
                border: '1px solid rgba(106, 242, 222, 0.08)',
                backdropFilter: 'blur(20px)',
              }}
            >
              {/* Header bar */}
              <div className="flex justify-between items-center px-6 py-3" style={{ background: 'rgba(25, 25, 31, 0.9)' }}>
                <div className="flex items-center gap-3">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full" style={{ background: '#ff5f57' }} />
                    <div className="w-3 h-3 rounded-full" style={{ background: '#febc2e' }} />
                    <div className="w-3 h-3 rounded-full" style={{ background: '#28c840' }} />
                  </div>
                  <span className="text-xs tracking-[0.2em] uppercase" style={{ color: 'rgba(248,245,253,0.4)' }}>
                    UVAI Intelligence Report
                  </span>
                </div>
                <span className="text-[10px] uppercase" style={{ color: 'rgba(248,245,253,0.25)' }}>
                  Live Processing
                </span>
              </div>

              {/* Split layout */}
              <div className="grid lg:grid-cols-12 min-h-[420px]">
                {/* LEFT: Video Player */}
                <div className="lg:col-span-5 relative" style={{ background: '#0a0a0f' }}>
                  {/* Fake video frame */}
                  <div className="aspect-video relative overflow-hidden">
                    <div
                      className="absolute inset-0"
                      style={{
                        background: 'linear-gradient(145deg, #131318 0%, #0a0a0f 50%, #0e1117 100%)',
                      }}
                    />
                    {/* Play button */}
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div
                        className="w-16 h-16 rounded-full flex items-center justify-center"
                        style={{
                          background: 'rgba(106, 242, 222, 0.15)',
                          border: '2px solid rgba(106, 242, 222, 0.4)',
                        }}
                      >
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="#6af2de">
                          <path d="M8 5v14l11-7z" />
                        </svg>
                      </div>
                    </div>
                    {/* HUD overlays */}
                    <div className="absolute top-3 left-3 flex items-center gap-2">
                      <div
                        className="px-2 py-0.5 rounded text-[10px] tracking-widest uppercase"
                        style={{
                          background: 'rgba(25,25,31,0.8)',
                          borderLeft: '2px solid #6af2de',
                          color: '#6af2de',
                        }}
                      >
                        Live_Feed
                      </div>
                      <div
                        className="px-2 py-0.5 rounded text-[10px] font-heading"
                        style={{ background: 'rgba(25,25,31,0.8)', color: '#f8f5fd' }}
                      >
                        00:42:15
                      </div>
                    </div>
                    <div className="absolute top-3 right-3">
                      <div
                        className="px-2 py-0.5 rounded text-[10px] uppercase"
                        style={{ background: 'rgba(25,25,31,0.8)', color: '#f8f5fd' }}
                      >
                        1080p
                      </div>
                    </div>
                    {/* Detection badges */}
                    <div className="absolute bottom-12 left-3 flex gap-1.5">
                      {['Speaker Detected', 'Code Block'].map((badge) => (
                        <span
                          key={badge}
                          className="text-[9px] px-2 py-0.5 rounded uppercase font-bold tracking-tight"
                          style={{
                            background: 'rgba(32, 192, 255, 0.15)',
                            color: '#69ccff',
                            border: '1px solid rgba(32, 192, 255, 0.25)',
                          }}
                        >
                          {badge}
                        </span>
                      ))}
                    </div>
                    {/* Scrub bar */}
                    <div className="absolute bottom-3 left-3 right-3">
                      <div className="w-full h-1 rounded-full" style={{ background: 'rgba(37,37,44,0.8)' }}>
                        <div className="h-full rounded-full" style={{ width: '42%', background: '#6af2de' }} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* RIGHT: Intelligence Panel */}
                <div className="lg:col-span-7 flex flex-col" style={{ borderLeft: '1px solid rgba(72,71,77,0.15)' }}>
                  {/* Tabs */}
                  <div className="flex gap-0" style={{ borderBottom: '1px solid rgba(72,71,77,0.15)' }}>
                    {['Summary', 'Transcript', 'Actions', 'Topics'].map((tab, i) => (
                      <button
                        key={tab}
                        className="px-5 py-3 text-xs tracking-widest uppercase transition-colors"
                        style={{
                          color: i === 0 ? '#6af2de' : 'rgba(248,245,253,0.35)',
                          borderBottom: i === 0 ? '2px solid #6af2de' : '2px solid transparent',
                          background: i === 0 ? 'rgba(106, 242, 222, 0.05)' : 'transparent',
                        }}
                      >
                        {tab}
                      </button>
                    ))}
                  </div>

                  {/* Scene Timeline */}
                  <div className="px-5 pt-5">
                    <div className="flex justify-between text-[10px] uppercase tracking-widest mb-3" style={{ color: 'rgba(248,245,253,0.35)' }}>
                      <span>Scene Timeline</span>
                      <span>04:20</span>
                    </div>
                    <div className="flex gap-1 h-8">
                      {[
                        { w: '25%', opacity: 0.5 },
                        { w: '15%', opacity: 0.25 },
                        { w: '40%', opacity: 0.65 },
                        { w: '20%', opacity: 0.3 },
                      ].map((seg, i) => (
                        <div
                          key={i}
                          className="rounded-sm cursor-pointer hover:opacity-100 transition-opacity"
                          style={{
                            width: seg.w,
                            background: i === 3 ? 'rgba(255,113,108,0.3)' : `rgba(106,242,222,${seg.opacity})`,
                          }}
                        />
                      ))}
                    </div>
                  </div>

                  {/* Insight feed */}
                  <div className="flex-1 px-5 py-4 space-y-0">
                    {INSIGHTS.map((insight, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-3 py-3 transition-all duration-500"
                        style={{
                          borderBottom: i < INSIGHTS.length - 1 ? '1px solid rgba(72,71,77,0.1)' : 'none',
                          opacity: activeInsight === i ? 1 : 0.5,
                          transform: activeInsight === i ? 'translateX(4px)' : 'translateX(0)',
                        }}
                      >
                        <span className="text-base">{insight.icon}</span>
                        <span className="text-sm flex-1" style={{ color: '#f8f5fd' }}>{insight.text}</span>
                        <span
                          className="text-[9px] px-2 py-0.5 rounded uppercase font-bold"
                          style={{
                            background: insight.color === 'amber'
                              ? 'rgba(255, 160, 0, 0.1)'
                              : insight.color === 'cyan'
                                ? 'rgba(32, 192, 255, 0.1)'
                                : 'rgba(106, 242, 222, 0.1)',
                            color: insight.color === 'amber'
                              ? '#ffc107'
                              : insight.color === 'cyan'
                                ? '#69ccff'
                                : '#6af2de',
                          }}
                        >
                          {insight.tag}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ─── METRICS BAR ─── */}
        <section className="py-20" style={{ background: '#131318' }}>
          <div className="max-w-[1440px] mx-auto px-8 grid grid-cols-2 md:grid-cols-4 gap-12">
            {STATS.map((stat) => (
              <div key={stat.label} className="text-center md:text-left">
                <div className="font-heading text-4xl font-bold tracking-tighter mb-1" style={{ color: '#f8f5fd' }}>
                  {stat.value}
                </div>
                <div className="text-xs uppercase tracking-[0.2em]" style={{ color: 'rgba(248,245,253,0.35)' }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ─── FEATURES / INSIGHTS PANEL ─── */}
        <section className="py-32 px-8 max-w-[1440px] mx-auto">
          <div className="grid lg:grid-cols-12 gap-16 items-start">
            {/* Left: Feature list */}
            <div className="lg:col-span-5 space-y-10">
              <div>
                <h2 className="font-heading text-4xl font-bold mb-6" style={{ color: '#f8f5fd' }}>
                  AI-Driven
                  <br />
                  <span style={{ color: '#6af2de' }}>Narrative Insights</span>
                </h2>
                <p className="leading-relaxed" style={{ color: 'rgba(248,245,253,0.5)' }}>
                  Our engine doesn&apos;t just see pixels — it understands context. Extract metadata, emotional arc, technical depth, and actionable steps automatically.
                </p>
              </div>

              <div className="space-y-4">
                {FEATURES.map((feat, i) => (
                  <div
                    key={feat.title}
                    className="p-6 rounded-lg transition-colors cursor-pointer"
                    style={{
                      background: i === 0 ? 'rgba(31, 31, 38, 0.8)' : 'rgba(25, 25, 31, 0.5)',
                      borderLeft: i === 0 ? '4px solid #6af2de' : '4px solid transparent',
                    }}
                  >
                    <h4 className="font-heading text-lg mb-2 flex items-center gap-3" style={{ color: '#f8f5fd' }}>
                      <span>{feat.icon}</span> {feat.title}
                    </h4>
                    <p className="text-sm" style={{ color: 'rgba(248,245,253,0.45)' }}>
                      {feat.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: Analysis dashboard mockup */}
            <div
              className="lg:col-span-7 rounded-xl overflow-hidden shadow-2xl"
              style={{
                background: 'rgba(19, 19, 24, 0.8)',
                border: '1px solid rgba(72, 71, 77, 0.1)',
              }}
            >
              {/* Mockup header */}
              <div className="flex justify-between items-center px-6 py-4" style={{ background: 'rgba(25, 25, 31, 0.9)' }}>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full" style={{ background: '#6af2de' }} />
                  <span className="font-heading text-sm tracking-widest uppercase" style={{ color: '#f8f5fd' }}>
                    Intelligence Report v2
                  </span>
                </div>
                <span className="text-[10px] uppercase" style={{ color: 'rgba(248,245,253,0.25)' }}>Updated 2s ago</span>
              </div>

              <div className="p-6 space-y-6">
                {/* Mini data cards */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg" style={{ background: 'rgba(25, 25, 31, 0.8)' }}>
                    <div className="text-[10px] uppercase tracking-widest mb-2" style={{ color: 'rgba(248,245,253,0.3)' }}>
                      Topics Extracted
                    </div>
                    <div className="font-heading text-2xl" style={{ color: '#6af2de' }}>24</div>
                  </div>
                  <div className="p-4 rounded-lg" style={{ background: 'rgba(25, 25, 31, 0.8)' }}>
                    <div className="text-[10px] uppercase tracking-widest mb-2" style={{ color: 'rgba(248,245,253,0.3)' }}>
                      Confidence
                    </div>
                    <div className="font-heading text-2xl" style={{ color: '#6af2de' }}>99.4%</div>
                  </div>
                </div>

                {/* Simulated log entries */}
                <div className="space-y-0">
                  {[
                    { text: 'Technical tutorial structure identified', tag: 'AUTO_LOG' },
                    { text: 'Speaker diarization: 2 voices detected', tag: 'AUTO_LOG' },
                    { text: 'High complexity spike at segment 3', tag: 'REVIEW', alert: true },
                  ].map((log, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-4 py-3"
                      style={{ borderBottom: i < 2 ? '1px solid rgba(72,71,77,0.1)' : 'none' }}
                    >
                      <span className="text-sm flex-1" style={{ color: '#f8f5fd' }}>{log.text}</span>
                      <span
                        className="text-[9px] px-2 py-0.5 rounded uppercase font-bold"
                        style={{
                          background: log.alert ? 'rgba(255,113,108,0.1)' : 'rgba(32, 192, 255, 0.1)',
                          color: log.alert ? '#ff716c' : '#69ccff',
                        }}
                      >
                        {log.tag}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ─── CTA ─── */}
        <section className="py-32 px-6">
          <div
            className="max-w-4xl mx-auto rounded-2xl p-12 text-center relative overflow-hidden"
            style={{ background: 'rgba(31, 31, 38, 0.8)' }}
          >
            {/* Glow orb */}
            <div
              className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2 w-64 h-64 rounded-full blur-3xl"
              style={{ background: 'rgba(106, 242, 222, 0.08)' }}
            />
            <h2 className="font-heading text-4xl md:text-5xl font-bold mb-8 relative" style={{ color: '#f8f5fd' }}>
              Ready to see through the
              <br />
              <span style={{ color: '#6af2de' }}>intelligence lens?</span>
            </h2>
            <div className="flex flex-col sm:flex-row gap-4 justify-center relative">
              <Link
                href="/dashboard"
                className="px-10 py-4 rounded-lg font-bold hover:scale-105 transition-transform"
                style={{ background: 'linear-gradient(135deg, #6af2de, #10b7a5)', color: '#002b26' }}
              >
                Get Started Free
              </Link>
              <Link
                href="/pricing"
                className="px-10 py-4 rounded-lg font-bold transition-colors"
                style={{ border: '1px solid rgba(72,71,77,0.3)', color: '#f8f5fd' }}
              >
                View Pricing
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* ─── FOOTER ─── */}
      <footer className="py-12 px-8" style={{ borderTop: '1px solid rgba(72,71,77,0.1)' }}>
        <div className="flex flex-col md:flex-row justify-between items-center gap-8 max-w-[1440px] mx-auto">
          <div className="flex flex-col items-center md:items-start gap-2">
            <div className="text-lg font-bold font-heading tracking-tighter" style={{ color: '#f8f5fd' }}>UVAI</div>
            <div className="text-sm" style={{ color: 'rgba(248,245,253,0.35)' }}>
              © 2026 UVAI. Video Intelligence Engine.
            </div>
          </div>
          <div className="flex gap-8">
            {['Features', 'Pricing', 'Dashboard', 'GitHub'].map((link) => (
              <Link
                key={link}
                href={link === 'GitHub' ? 'https://github.com/groupthinking/EventRelay' : `/${link.toLowerCase()}`}
                className="text-sm uppercase tracking-wide transition-all duration-300 hover:-translate-y-0.5"
                style={{ color: 'rgba(248,245,253,0.35)' }}
                target={link === 'GitHub' ? '_blank' : undefined}
              >
                {link}
              </Link>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
