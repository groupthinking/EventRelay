'use client';

import Link from 'next/link';
import { useState, useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  WORKFLOW_TEMPLATES,
  CATEGORIES,
  type WorkflowTemplate,
  type TemplateCategory,
} from '@/lib/workflow-templates';

/* ═══════════════════════════════════════════
   UVAI Landing — Template Gallery + URL Input
   Airtop-style workflow gallery with glassmorphic cards
   ═══════════════════════════════════════════ */

const STATS = [
  { value: '10K+', label: 'Videos Processed' },
  { value: '500ms', label: 'Avg Response' },
  { value: '98%', label: 'Accuracy' },
  { value: '9', label: 'Workflow Templates' },
];

/* ─── Template Card ─── */
function TemplateCard({
  template,
  index,
}: {
  template: WorkflowTemplate;
  index: number;
}) {
  const router = useRouter();

  return (
    <button
      onClick={() =>
        router.push(
          `/dashboard?workflow=${template.id}`
        )
      }
      className="group relative text-left rounded-2xl p-6 transition-all duration-500 hover:scale-[1.02] hover:-translate-y-1"
      style={{
        background: 'rgba(19, 19, 24, 0.6)',
        border: '1px solid rgba(106, 242, 222, 0.06)',
        backdropFilter: 'blur(20px)',
        animationDelay: `${index * 60}ms`,
      }}
    >
      {/* Hover glow */}
      <div
        className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
        style={{
          background:
            'radial-gradient(circle at 50% 50%, rgba(106, 242, 222, 0.06) 0%, transparent 70%)',
        }}
      />

      {/* Featured badge */}
      {template.featured && (
        <div
          className="absolute top-4 right-4 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-widest"
          style={{
            background: 'rgba(106, 242, 222, 0.12)',
            color: '#6af2de',
            border: '1px solid rgba(106, 242, 222, 0.2)',
          }}
        >
          Featured
        </div>
      )}

      {/* Icon */}
      <div className="text-3xl mb-4">{template.icon}</div>

      {/* Title */}
      <h3
        className="font-heading text-lg font-bold tracking-tight mb-2 group-hover:text-[#6af2de] transition-colors duration-300"
        style={{ color: '#f8f5fd' }}
      >
        {template.title}
      </h3>

      {/* Description */}
      <p
        className="text-sm leading-relaxed mb-5 line-clamp-2"
        style={{ color: 'rgba(248, 245, 253, 0.45)' }}
      >
        {template.description}
      </p>

      {/* Pipeline stages preview */}
      <div className="flex items-center gap-1.5 mb-5 flex-wrap">
        {template.stages.map((stage, i) => (
          <span key={stage} className="flex items-center gap-1.5">
            <span
              className="text-[10px] px-2 py-0.5 rounded-md font-medium"
              style={{
                background: 'rgba(25, 25, 31, 0.8)',
                color: 'rgba(248, 245, 253, 0.5)',
                border: '1px solid rgba(72, 71, 77, 0.15)',
              }}
            >
              {stage}
            </span>
            {i < template.stages.length - 1 && (
              <span style={{ color: 'rgba(106, 242, 222, 0.3)' }}>→</span>
            )}
          </span>
        ))}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <span
          className="text-[10px] uppercase tracking-widest font-bold"
          style={{ color: 'rgba(248, 245, 253, 0.25)' }}
        >
          {template.estimatedTime}
        </span>
        <span
          className="text-xs font-bold uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0"
          style={{ color: '#6af2de' }}
        >
          Run →
        </span>
      </div>
    </button>
  );
}

/* ─── Main Page ─── */
export default function Home() {
  const [videoUrl, setVideoUrl] = useState('');
  const [activeCategory, setActiveCategory] = useState<TemplateCategory>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const router = useRouter();
  const galleryRef = useRef<HTMLDivElement>(null);

  const handleProcess = useCallback(() => {
    if (!videoUrl.trim()) return;
    router.push(`/dashboard?video=${encodeURIComponent(videoUrl)}`);
  }, [videoUrl, router]);

  const filteredTemplates = WORKFLOW_TEMPLATES.filter((t) => {
    const matchesCategory =
      activeCategory === 'all' || t.category === activeCategory;
    const matchesSearch =
      !searchQuery ||
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.tags.some((tag) =>
        tag.toLowerCase().includes(searchQuery.toLowerCase())
      );
    return matchesCategory && matchesSearch;
  });

  const scrollToGallery = () => {
    galleryRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

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
          <Link
            href="/"
            className="text-2xl font-black tracking-tighter font-heading"
            style={{ color: '#6af2de' }}
          >
            UVAI
          </Link>
          <div className="hidden md:flex gap-8 items-center">
            {['Workflows', 'Features', 'Pricing', 'Dashboard'].map((link) => (
              <Link
                key={link}
                href={
                  link === 'Workflows'
                    ? '#gallery'
                    : `/${link.toLowerCase()}`
                }
                onClick={
                  link === 'Workflows'
                    ? (e) => {
                        e.preventDefault();
                        scrollToGallery();
                      }
                    : undefined
                }
                className="text-sm tracking-wide uppercase transition-colors duration-300 hover:opacity-100"
                style={{
                  color: 'rgba(248,245,253,0.5)',
                  fontFamily: 'var(--font-body)',
                }}
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
          className="relative min-h-[70vh] flex flex-col items-center justify-center px-6"
          style={{
            background:
              'radial-gradient(circle at 50% 40%, rgba(106, 242, 222, 0.06) 0%, transparent 65%)',
          }}
        >
          <span
            className="text-xs tracking-[0.3em] uppercase mb-6 block"
            style={{ color: '#6af2de' }}
          >
            Agentic Video Execution Platform
          </span>

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
              Anything
            </span>
            <br />
            in one click
          </h1>

          <p
            className="text-lg md:text-xl max-w-2xl mx-auto text-center leading-relaxed mb-10"
            style={{ color: 'rgba(248,245,253,0.5)' }}
          >
            Choose a workflow template or paste any YouTube URL. Our AI agents
            extract intelligence, generate code, and deploy — end to end.
          </p>

          {/* URL Input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleProcess();
            }}
            className="w-full max-w-2xl mb-8"
          >
            <div
              className="flex gap-2 p-2 rounded-xl transition-all duration-300"
              style={{
                background: 'rgba(25, 25, 31, 0.8)',
                border: '1px solid rgba(106, 242, 222, 0.15)',
                boxShadow: videoUrl
                  ? '0 0 30px rgba(106, 242, 222, 0.1)'
                  : 'none',
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
                Analyze
              </button>
            </div>
          </form>

          {/* Or divider */}
          <div className="flex items-center gap-4 mb-6 w-full max-w-md">
            <div
              className="flex-1 h-px"
              style={{ background: 'rgba(72, 71, 77, 0.3)' }}
            />
            <span
              className="text-xs uppercase tracking-widest"
              style={{ color: 'rgba(248,245,253,0.25)' }}
            >
              or choose a workflow
            </span>
            <div
              className="flex-1 h-px"
              style={{ background: 'rgba(72, 71, 77, 0.3)' }}
            />
          </div>

          <button
            onClick={scrollToGallery}
            className="flex items-center gap-2 text-sm font-medium transition-all duration-300 hover:-translate-y-0.5"
            style={{ color: '#6af2de' }}
          >
            <span>Browse Templates</span>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M12 5v14M5 12l7 7 7-7" />
            </svg>
          </button>
        </section>

        {/* ─── STATS BAR ─── */}
        <section className="py-12" style={{ background: '#131318' }}>
          <div className="max-w-[1440px] mx-auto px-8 grid grid-cols-2 md:grid-cols-4 gap-8">
            {STATS.map((stat) => (
              <div key={stat.label} className="text-center">
                <div
                  className="font-heading text-3xl font-bold tracking-tighter mb-1"
                  style={{ color: '#f8f5fd' }}
                >
                  {stat.value}
                </div>
                <div
                  className="text-xs uppercase tracking-[0.2em]"
                  style={{ color: 'rgba(248,245,253,0.35)' }}
                >
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ─── TEMPLATE GALLERY ─── */}
        <section
          ref={galleryRef}
          id="gallery"
          className="py-20 px-6 md:px-8"
          style={{
            background:
              'radial-gradient(ellipse at 50% 0%, rgba(106, 242, 222, 0.03) 0%, transparent 50%)',
          }}
        >
          <div className="max-w-[1440px] mx-auto">
            {/* Gallery Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
              <div>
                <span
                  className="text-[10px] tracking-[0.3em] uppercase mb-3 block"
                  style={{ color: '#6af2de' }}
                >
                  Workflow Templates
                </span>
                <h2
                  className="font-heading text-3xl md:text-4xl font-bold tracking-tighter"
                  style={{ color: '#f8f5fd' }}
                >
                  Deploy end-to-end in one click
                </h2>
              </div>

              {/* Search */}
              <div className="w-full md:w-72">
                <div
                  className="flex items-center gap-2 px-4 py-2.5 rounded-lg"
                  style={{
                    background: 'rgba(25, 25, 31, 0.8)',
                    border: '1px solid rgba(72, 71, 77, 0.2)',
                  }}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="rgba(248,245,253,0.3)"
                    strokeWidth="2"
                  >
                    <circle cx="11" cy="11" r="8" />
                    <path d="m21 21-4.35-4.35" />
                  </svg>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search workflows..."
                    className="flex-1 bg-transparent text-sm text-white placeholder:text-white/25 focus:outline-none"
                  />
                </div>
              </div>
            </div>

            {/* Category Filters */}
            <div className="flex gap-2 mb-10 overflow-x-auto pb-2 scrollbar-hide">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id)}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-widest whitespace-nowrap transition-all duration-300"
                  style={{
                    background:
                      activeCategory === cat.id
                        ? 'rgba(106, 242, 222, 0.1)'
                        : 'rgba(25, 25, 31, 0.6)',
                    color:
                      activeCategory === cat.id
                        ? '#6af2de'
                        : 'rgba(248,245,253,0.4)',
                    border:
                      activeCategory === cat.id
                        ? '1px solid rgba(106, 242, 222, 0.2)'
                        : '1px solid rgba(72, 71, 77, 0.15)',
                  }}
                >
                  <span>{cat.icon}</span>
                  <span>{cat.label}</span>
                  {cat.id === 'all' && (
                    <span
                      className="ml-1 px-1.5 py-0.5 rounded text-[9px]"
                      style={{
                        background: 'rgba(106, 242, 222, 0.15)',
                        color: '#6af2de',
                      }}
                    >
                      {WORKFLOW_TEMPLATES.length}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Template Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {filteredTemplates.map((template, i) => (
                <TemplateCard key={template.id} template={template} index={i} />
              ))}
            </div>

            {filteredTemplates.length === 0 && (
              <div className="py-20 text-center">
                <p style={{ color: 'rgba(248,245,253,0.4)' }}>
                  No workflows match your search. Try a different term.
                </p>
              </div>
            )}
          </div>
        </section>

        {/* ─── HOW IT WORKS ─── */}
        <section className="py-24 px-6 md:px-8" style={{ background: '#131318' }}>
          <div className="max-w-[1440px] mx-auto">
            <div className="text-center mb-16">
              <span
                className="text-[10px] tracking-[0.3em] uppercase mb-3 block"
                style={{ color: '#6af2de' }}
              >
                How It Works
              </span>
              <h2
                className="font-heading text-3xl md:text-4xl font-bold tracking-tighter"
                style={{ color: '#f8f5fd' }}
              >
                Three steps. Zero config.
              </h2>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  step: '01',
                  title: 'Choose or Paste',
                  desc: 'Pick a workflow template or paste any YouTube URL. Our engine handles the rest.',
                },
                {
                  step: '02',
                  title: 'Watch Agents Work',
                  desc: 'Real-time SSE streaming shows each agent processing your video — transcription, extraction, generation.',
                },
                {
                  step: '03',
                  title: 'Get Results',
                  desc: 'Deployable code, structured reports, action items, or whatever your workflow produces — delivered instantly.',
                },
              ].map((item) => (
                <div
                  key={item.step}
                  className="relative p-8 rounded-2xl"
                  style={{
                    background: 'rgba(19, 19, 24, 0.6)',
                    border: '1px solid rgba(72, 71, 77, 0.1)',
                  }}
                >
                  <div
                    className="font-heading text-5xl font-black mb-4"
                    style={{ color: 'rgba(106, 242, 222, 0.1)' }}
                  >
                    {item.step}
                  </div>
                  <h3
                    className="font-heading text-xl font-bold mb-3"
                    style={{ color: '#f8f5fd' }}
                  >
                    {item.title}
                  </h3>
                  <p
                    className="text-sm leading-relaxed"
                    style={{ color: 'rgba(248,245,253,0.45)' }}
                  >
                    {item.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── CTA ─── */}
        <section className="py-24 px-6">
          <div
            className="max-w-4xl mx-auto rounded-2xl p-12 text-center relative overflow-hidden"
            style={{ background: 'rgba(31, 31, 38, 0.8)' }}
          >
            <div
              className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2 w-64 h-64 rounded-full blur-3xl"
              style={{ background: 'rgba(106, 242, 222, 0.08)' }}
            />
            <h2
              className="font-heading text-4xl md:text-5xl font-bold mb-4 relative"
              style={{ color: '#f8f5fd' }}
            >
              Ready to automate your
              <br />
              <span style={{ color: '#6af2de' }}>video workflows?</span>
            </h2>
            <p
              className="mb-8 max-w-lg mx-auto"
              style={{ color: 'rgba(248,245,253,0.45)' }}
            >
              Start with a template or bring your own video. No setup required.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center relative">
              <Link
                href="/dashboard"
                className="px-10 py-4 rounded-lg font-bold hover:scale-105 transition-transform"
                style={{
                  background: 'linear-gradient(135deg, #6af2de, #10b7a5)',
                  color: '#002b26',
                }}
              >
                Get Started Free
              </Link>
              <button
                onClick={scrollToGallery}
                className="px-10 py-4 rounded-lg font-bold transition-colors"
                style={{
                  border: '1px solid rgba(72,71,77,0.3)',
                  color: '#f8f5fd',
                }}
              >
                Browse Templates
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* ─── FOOTER ─── */}
      <footer
        className="py-12 px-8"
        style={{ borderTop: '1px solid rgba(72,71,77,0.1)' }}
      >
        <div className="flex flex-col md:flex-row justify-between items-center gap-8 max-w-[1440px] mx-auto">
          <div className="flex flex-col items-center md:items-start gap-2">
            <div
              className="text-lg font-bold font-heading tracking-tighter"
              style={{ color: '#f8f5fd' }}
            >
              UVAI
            </div>
            <div
              className="text-sm"
              style={{ color: 'rgba(248,245,253,0.35)' }}
            >
              © 2026 UVAI. Agentic Video Execution Platform.
            </div>
          </div>
          <div className="flex gap-8">
            {['Features', 'Pricing', 'Dashboard', 'GitHub'].map((link) => (
              <Link
                key={link}
                href={
                  link === 'GitHub'
                    ? 'https://github.com/groupthinking/EventRelay'
                    : `/${link.toLowerCase()}`
                }
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
