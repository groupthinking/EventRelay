'use client';

import Link from 'next/link';
import { useState, useEffect, useRef } from 'react';
import { clsx } from 'clsx';
import { SuggestedPrompts } from '@/components/ui';

// ============================================
// Animated Counter Component
// ============================================
function AnimatedCounter({
  value,
  label,
  suffix = ''
}: {
  value: string;
  label: string;
  suffix?: string;
}) {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { threshold: 0.1 }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={clsx(
        'text-center transition-all duration-700',
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      )}
    >
      <div className="text-4xl md:text-5xl font-black bg-gradient-to-r from-primary-400 via-accent-400 to-primary-400 bg-clip-text text-transparent bg-[length:200%_auto] animate-gradient">
        {value}{suffix}
      </div>
      <div className="text-sm text-white/50 mt-2 font-medium">{label}</div>
    </div>
  );
}

// ============================================
// Pipeline Visualization
// ============================================
function PipelineVisualization() {
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStage((prev) => (prev + 1) % 4);
    }, 2500);
    return () => clearInterval(timer);
  }, []);

  const stages = [
    {
      name: 'Ingest',
      icon: '📥',
      gradient: 'from-violet-500 to-purple-600',
      desc: 'Upload or paste any video URL',
      glow: 'shadow-violet-500/30'
    },
    {
      name: 'Process',
      icon: '⚡',
      gradient: 'from-purple-500 to-indigo-600',
      desc: 'AI analyzes in 2.3s avg',
      glow: 'shadow-purple-500/30'
    },
    {
      name: 'Transform',
      icon: '🧠',
      gradient: 'from-indigo-500 to-blue-600',
      desc: 'Extract insights & actions',
      glow: 'shadow-indigo-500/30'
    },
    {
      name: 'Deploy',
      icon: '🚀',
      gradient: 'from-blue-500 to-cyan-600',
      desc: 'Generate live applications',
      glow: 'shadow-cyan-500/30'
    },
  ];

  return (
    <div className="relative w-full max-w-5xl mx-auto py-16 px-4">
      {/* Connection line background */}
      <div className="absolute top-1/2 left-[10%] right-[10%] h-1 bg-gradient-to-r from-violet-500/20 via-purple-500/20 via-indigo-500/20 to-cyan-500/20 transform -translate-y-1/2 rounded-full" />

      {/* Active progress line */}
      <div
        className="absolute top-1/2 left-[10%] h-1 bg-gradient-to-r from-violet-500 via-purple-500 via-indigo-500 to-cyan-500 transform -translate-y-1/2 rounded-full transition-all duration-1000 ease-out"
        style={{ width: `${((activeStage + 1) / 4) * 80}%` }}
      />

      <div className="relative flex justify-between">
        {stages.map((stage, index) => (
          <div
            key={stage.name}
            className={clsx(
              'flex flex-col items-center transition-all duration-500',
              index <= activeStage ? 'opacity-100' : 'opacity-40'
            )}
          >
            {/* Icon container */}
            <div
              className={clsx(
                'relative w-20 h-20 md:w-24 md:h-24 rounded-2xl bg-gradient-to-br flex items-center justify-center text-3xl md:text-4xl transition-all duration-500',
                stage.gradient,
                index === activeStage && 'scale-110 shadow-2xl ring-4 ring-white/20',
                index === activeStage && stage.glow
              )}
            >
              {stage.icon}
              {/* Pulse ring for active */}
              {index === activeStage && (
                <div className="absolute inset-0 rounded-2xl animate-ping opacity-20 bg-white" />
              )}
            </div>

            {/* Label */}
            <span className="mt-4 font-bold text-lg text-white">{stage.name}</span>
            <span className="mt-1 text-sm text-white/50 text-center max-w-[120px] hidden md:block">
              {stage.desc}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================
// Feature Card
// ============================================
function FeatureCard({
  icon,
  title,
  desc,
  gradient,
  delay = 0
}: {
  icon: string;
  title: string;
  desc: string;
  gradient: string;
  delay?: number;
}) {
  return (
    <div
      className={clsx(
        'group relative overflow-hidden rounded-2xl p-[1px]',
        'bg-gradient-to-br',
        gradient,
        'animate-fade-in-up opacity-0'
      )}
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'forwards' }}
    >
      <div className="relative rounded-2xl bg-surface-900/95 backdrop-blur-xl p-6 h-full transition-all duration-300 group-hover:bg-surface-900/80">
        {/* Icon */}
        <div className="text-4xl mb-4 transform transition-transform duration-300 group-hover:scale-110">
          {icon}
        </div>

        {/* Content */}
        <h3 className="text-xl font-bold text-white mb-2 group-hover:text-primary-400 transition-colors">
          {title}
        </h3>
        <p className="text-white/60 leading-relaxed">{desc}</p>

        {/* Hover glow effect */}
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />

        {/* Bottom accent line */}
        <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-primary-500 to-accent-500 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left" />
      </div>
    </div>
  );
}

// ============================================
// Persona Card
// ============================================
function PersonaCard({
  emoji,
  role,
  benefit,
  delay = 0
}: {
  emoji: string;
  role: string;
  benefit: string;
  delay?: number;
}) {
  return (
    <div
      className={clsx(
        'bg-white/[0.03] backdrop-blur-xl rounded-2xl p-6',
        'border border-white/[0.08] hover:border-primary-500/30',
        'transition-all duration-300 hover:-translate-y-2 hover:shadow-xl hover:shadow-primary-500/10',
        'animate-fade-in-up opacity-0'
      )}
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'forwards' }}
    >
      <div className="text-4xl mb-4">{emoji}</div>
      <div className="font-bold text-white mb-2">{role}</div>
      <div className="text-sm text-white/50 leading-relaxed">{benefit}</div>
    </div>
  );
}

// ============================================
// Testimonial Card
// ============================================
function TestimonialCard({
  initials,
  name,
  role,
  quote,
  gradient,
  delay = 0
}: {
  initials: string;
  name: string;
  role: string;
  quote: string;
  gradient: string;
  delay?: number;
}) {
  return (
    <div
      className={clsx(
        'bg-gradient-to-br backdrop-blur-xl rounded-2xl border border-white/[0.08] p-6',
        gradient,
        'animate-fade-in-up opacity-0'
      )}
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'forwards' }}
    >
      <div className="flex items-center gap-4 mb-4">
        <div className={clsx(
          'w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold',
          'bg-gradient-to-br from-primary-400 to-accent-500'
        )}>
          {initials}
        </div>
        <div>
          <div className="font-semibold text-white">{name}</div>
          <div className="text-sm text-white/50">{role}</div>
        </div>
      </div>
      <p className="text-white/80 italic leading-relaxed">&ldquo;{quote}&rdquo;</p>
      <div className="flex gap-1 mt-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <span key={i} className="text-yellow-400">★</span>
        ))}
      </div>
    </div>
  );
}

// ============================================
// Loading Spinner Component
// ============================================
function LoadingSpinner({ size = 20 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="animate-spin"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        strokeOpacity="0.25"
      />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

// ============================================
// Mobile Menu Component
// ============================================
function MobileMenu({
  isOpen,
  onClose
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={clsx(
          'fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] transition-opacity duration-300 md:hidden',
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
      />

      {/* Menu Panel */}
      <div
        className={clsx(
          'fixed top-0 right-0 h-full w-72 bg-surface-900/95 backdrop-blur-xl border-l border-white/[0.08] z-[101] transition-transform duration-300 ease-out md:hidden',
          isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-10 h-10 flex items-center justify-center rounded-lg bg-white/[0.05] hover:bg-white/[0.1] transition-colors"
          aria-label="Close menu"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        {/* Menu Links */}
        <nav className="flex flex-col pt-20 px-6">
          <Link
            href="/dashboard"
            className="py-4 text-lg font-medium text-white/70 hover:text-white border-b border-white/[0.05] transition-colors"
            onClick={onClose}
          >
            Dashboard
          </Link>
          <Link
            href="/playground"
            className="py-4 text-lg font-medium text-white/70 hover:text-white border-b border-white/[0.05] transition-colors"
            onClick={onClose}
          >
            API
          </Link>
          <Link
            href="/docs"
            className="py-4 text-lg font-medium text-white/70 hover:text-white border-b border-white/[0.05] transition-colors"
            onClick={onClose}
          >
            Docs
          </Link>

          {/* CTA Button */}
          <Link
            href="/dashboard"
            className="mt-8 btn btn-primary text-center"
            onClick={onClose}
          >
            Get Started
            <span className="ml-1">→</span>
          </Link>
        </nav>
      </div>
    </>
  );
}

// ============================================
// Scroll to Top Button
// ============================================
function ScrollToTopButton() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const toggleVisibility = () => {
      setIsVisible(window.scrollY > 500);
    };

    window.addEventListener('scroll', toggleVisibility);
    return () => window.removeEventListener('scroll', toggleVisibility);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <button
      onClick={scrollToTop}
      className={clsx(
        'fixed bottom-8 right-8 z-50 w-12 h-12 rounded-full',
        'bg-gradient-to-br from-primary-500 to-primary-600',
        'shadow-lg shadow-primary-500/30',
        'flex items-center justify-center',
        'transition-all duration-300',
        'hover:shadow-xl hover:shadow-primary-500/40 hover:-translate-y-1',
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
      )}
      aria-label="Scroll to top"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M18 15l-6-6-6 6" />
      </svg>
    </button>
  );
}

// ============================================
// Floating Orbs Background
// ============================================
function FloatingOrbs() {
  return (
    <>
      <div className="fixed top-20 left-[10%] w-72 h-72 bg-primary-500/20 rounded-full blur-[100px] animate-float" />
      <div className="fixed top-40 right-[15%] w-96 h-96 bg-accent-500/15 rounded-full blur-[120px] animate-float" style={{ animationDelay: '1s' }} />
      <div className="fixed bottom-20 left-[20%] w-80 h-80 bg-primary-600/15 rounded-full blur-[100px] animate-float" style={{ animationDelay: '2s' }} />
      <div className="fixed bottom-40 right-[10%] w-64 h-64 bg-accent-400/10 rounded-full blur-[80px] animate-float" style={{ animationDelay: '0.5s' }} />
    </>
  );
}

// ============================================
// Main Homepage
// ============================================
export default function HomePage() {
  const [videoUrl, setVideoUrl] = useState('');
  const [isLoaded, setIsLoaded] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    setIsLoaded(true);
  }, []);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (videoUrl.trim() && !isAnalyzing) {
      setIsAnalyzing(true);
      // Small delay to show loading state before navigation
      await new Promise(resolve => setTimeout(resolve, 300));
      window.location.href = `/dashboard?video=${encodeURIComponent(videoUrl)}`;
    }
  };

  return (
    <main className="min-h-screen text-white overflow-hidden">
      {/* Animated background */}
      <FloatingOrbs />

      {/* Mobile Menu */}
      <MobileMenu isOpen={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)} />

      {/* Scroll to Top Button */}
      <ScrollToTopButton />

      {/* Navigation */}
      <nav className="relative z-50 flex items-center justify-between px-6 lg:px-12 py-5 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-lg shadow-lg shadow-primary-500/30 transition-transform hover:scale-105">
            U
          </div>
          <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent">UVAI.io</span>
        </div>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-8">
          <Link href="/dashboard" className="text-white/50 hover:text-white transition-all duration-200 font-medium hover:-translate-y-0.5">
            Dashboard
          </Link>
          <Link href="/playground" className="text-white/50 hover:text-white transition-all duration-200 font-medium hover:-translate-y-0.5">
            API
          </Link>
          <Link href="/docs" className="text-white/50 hover:text-white transition-all duration-200 font-medium hover:-translate-y-0.5">
            Docs
          </Link>
          <Link
            href="/dashboard"
            className="btn btn-primary px-5 py-2.5 group inline-flex items-center gap-2"
          >
            Get Started
            <span className="transition-transform group-hover:translate-x-1">→</span>
          </Link>
        </div>

        {/* Mobile Hamburger Button */}
        <button
          onClick={() => setIsMobileMenuOpen(true)}
          className="md:hidden w-10 h-10 flex items-center justify-center rounded-lg bg-white/[0.05] hover:bg-white/[0.1] transition-colors"
          aria-label="Open menu"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </nav>

      {/* Hero Section */}
      <section className={clsx(
        'relative z-10 max-w-6xl mx-auto px-6 pt-20 lg:pt-32 pb-20',
        'transition-all duration-1000',
        isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      )}>
        <div className="text-center">
          {/* Status Badge */}
          <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-white/[0.03] border border-white/[0.08] mb-8 backdrop-blur-xl">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-400" />
            </span>
            <span className="text-sm text-white/70 font-medium">
              Powered by Gemini 2.5 Flash + Multi-Agent AI
            </span>
          </div>

          {/* Main Headline */}
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-black leading-[0.9] mb-6 tracking-tighter">
            <span className="block text-white drop-shadow-lg">
              VIDEO TO
            </span>
            <span className="block text-white drop-shadow-lg">
              LEARNING
            </span>
            <span className="block bg-gradient-to-r from-primary-400 via-accent-400 to-primary-400 bg-clip-text text-transparent bg-[length:200%_auto] animate-gradient drop-shadow-lg">
              APP
            </span>
          </h1>

          {/* Subheadline */}
          <p className="text-lg md:text-xl text-white/60 max-w-xl mx-auto mb-10 leading-relaxed">
            Generate interactive learning apps from
            <br />
            <span className="text-white/80">YouTube content</span>
          </p>

          {/* Attribution */}
          <p className="text-sm text-white/40 mb-10">
            An experiment by <span className="text-primary-400 hover:text-primary-300 transition-colors cursor-pointer">Aaron Wade</span>
          </p>

          {/* Main CTA Input */}
          <form onSubmit={handleAnalyze} className="max-w-2xl mx-auto mb-8">
            <div className="relative group">
              {/* Glow effect */}
              <div className="absolute -inset-1 bg-gradient-to-r from-primary-500/20 via-accent-500/20 to-primary-500/20 rounded-3xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

              <div className="relative flex gap-3 p-2.5 rounded-2xl bg-surface-900/80 border border-white/[0.1] backdrop-blur-xl shadow-2xl shadow-primary-500/10 transition-all duration-300 group-hover:border-primary-500/30">
                <input
                  type="text"
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  placeholder="Paste a URL from YouTube..."
                  className="flex-1 px-6 py-4 bg-transparent text-white text-lg placeholder:text-white/40 focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={isAnalyzing}
                  className={clsx(
                    'px-8 py-4 rounded-xl font-bold text-lg',
                    'bg-gradient-to-r from-primary-500 via-primary-600 to-primary-500 bg-[length:200%_100%]',
                    'shadow-lg shadow-primary-500/30',
                    'hover:shadow-xl hover:shadow-primary-500/40',
                    'hover:-translate-y-0.5 active:translate-y-0',
                    'transition-all duration-300',
                    'flex items-center gap-2',
                    'animate-gradient',
                    'disabled:opacity-80 disabled:cursor-not-allowed disabled:hover:translate-y-0'
                  )}
                >
                  {isAnalyzing ? (
                    <>
                      <LoadingSpinner size={20} />
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      Generate app
                      <span className="text-xl transition-transform group-hover:translate-x-1">→</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>

          {/* Suggested Topics */}
          <div className="mb-16">
            <SuggestedPrompts
              onSelectTopic={(query) => {
                const searchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
                if (typeof window !== 'undefined') {
                  window.open(searchUrl, '_blank', 'noopener,noreferrer');
                }
              }}
            />
          </div>

          {/* Video Preview Card - Example */}
          <div className="max-w-lg mx-auto mb-16">
            <div className="relative">
              {/* "Example" Badge */}
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 text-xs font-medium text-white/80">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse"></span>
                  Example Preview
                </span>
              </div>

              <div className="relative group">
                {/* Glow effect */}
                <div className="absolute -inset-4 bg-gradient-to-r from-primary-500/10 via-accent-500/10 to-primary-500/10 rounded-3xl blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700" />

                <div className="relative overflow-hidden rounded-2xl border border-white/[0.1] bg-surface-900/80 backdrop-blur-xl shadow-2xl transition-all duration-500 group-hover:border-white/[0.15]">
                  {/* Video thumbnail placeholder */}
                  <div className="relative aspect-video bg-gradient-to-br from-surface-800 to-surface-900 flex items-center justify-center">
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                    <div className="text-6xl opacity-50 group-hover:opacity-70 transition-opacity">🎬</div>

                    {/* Play button overlay */}
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300">
                      <div className="w-16 h-16 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 flex items-center justify-center transition-transform">
                        <span className="text-2xl ml-1">▶</span>
                      </div>
                    </div>

                    {/* Video info overlay */}
                    <div className="absolute bottom-4 left-4 right-4">
                      <p className="text-sm text-white/70 font-medium">Sample: How to build a startup</p>
                      <p className="text-xs text-white/40 mt-1">12:34 • Ready to transform</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="flex justify-center gap-12 md:gap-20">
            <AnimatedCounter value="50K" suffix="+" label="Videos Processed" />
            <AnimatedCounter value="2.3" suffix="s" label="Avg Processing" />
            <AnimatedCounter value="7" label="AI Models" />
          </div>
        </div>
      </section>

      {/* Pipeline Section */}
      <section className="relative z-10 py-20 border-t border-b border-white/[0.05]">
        <div className="text-center mb-8">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
            Video as Data Pipeline
          </h2>
          <p className="text-white/40 text-lg">
            From raw footage to deployed software in seconds
          </p>
        </div>
        <PipelineVisualization />
      </section>

      {/* Features Section */}
      <section className="relative z-10 max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            The Bloomberg Terminal for Video
          </h2>
          <p className="text-white/50 max-w-2xl mx-auto text-lg">
            Enterprise-grade video intelligence that turns hours of content into actionable insights
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          <FeatureCard
            icon="🎬"
            title="Video-to-Software"
            desc="Generate working prototypes and deployable code directly from tutorial videos"
            gradient="from-violet-500/20 to-purple-500/20"
            delay={100}
          />
          <FeatureCard
            icon="📊"
            title="Meeting Intelligence"
            desc="Extract action items, decisions, and follow-ups from any meeting recording"
            gradient="from-purple-500/20 to-indigo-500/20"
            delay={200}
          />
          <FeatureCard
            icon="🔍"
            title="Content Search"
            desc="Vector-powered semantic search across your entire video library"
            gradient="from-indigo-500/20 to-blue-500/20"
            delay={300}
          />
          <FeatureCard
            icon="⚡"
            title="Real-time Processing"
            desc="Stream processing with 2.3s average latency using Gemini 2.5 Flash"
            gradient="from-blue-500/20 to-cyan-500/20"
            delay={400}
          />
          <FeatureCard
            icon="🔗"
            title="API-First Design"
            desc="RESTful APIs with WebSocket support for seamless integration"
            gradient="from-cyan-500/20 to-teal-500/20"
            delay={500}
          />
          <FeatureCard
            icon="🤖"
            title="Multi-Agent AI"
            desc="7 specialized AI brains working in parallel for comprehensive analysis"
            gradient="from-teal-500/20 to-green-500/20"
            delay={600}
          />
        </div>
      </section>

      {/* Personas Section */}
      <section className="relative z-10 max-w-6xl mx-auto px-6 py-24 border-t border-white/[0.05]">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Built for Every Role</h2>
          <p className="text-white/50 text-lg">From executives to developers, UVAI adapts to your workflow</p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
          <PersonaCard
            emoji="📈"
            role="Account Manager"
            benefit="Get meeting summaries and action items without watching hours of recordings"
            delay={100}
          />
          <PersonaCard
            emoji="🔬"
            role="R&D Lead"
            benefit="Deep-dive analysis with frame-by-frame visual intelligence"
            delay={200}
          />
          <PersonaCard
            emoji="💻"
            role="Developer"
            benefit="Generate working code and prototypes from video tutorials"
            delay={300}
          />
          <PersonaCard
            emoji="📱"
            role="Content Creator"
            benefit="Repurpose long-form video into blogs, clips, and social posts"
            delay={400}
          />
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="relative z-10 max-w-6xl mx-auto px-6 py-24 border-t border-white/[0.05]">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Trusted by Forward-Thinking Teams
          </h2>
          <p className="text-white/50 text-lg">
            See how teams are transforming their video workflows
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <TestimonialCard
            initials="SK"
            name="Sarah Kim"
            role="VP of Product, TechFlow"
            quote="We process 50+ hours of customer calls weekly. UVAI cut our analysis time from days to minutes. The action item extraction is incredibly accurate."
            gradient="from-violet-500/10 to-purple-500/10"
            delay={100}
          />
          <TestimonialCard
            initials="JM"
            name="James Mitchell"
            role="Engineering Lead, DevScale"
            quote="The video-to-code feature is mind-blowing. I paste a tutorial URL and get working prototypes in seconds. It&apos;s changed how we onboard new team members."
            gradient="from-indigo-500/10 to-blue-500/10"
            delay={200}
          />
          <TestimonialCard
            initials="AR"
            name="Alex Rodriguez"
            role="Content Director, MediaPro"
            quote="We repurpose webinar recordings into blog posts, social clips, and newsletters. What took a week now takes an hour. ROI was immediate."
            gradient="from-cyan-500/10 to-teal-500/10"
            delay={300}
          />
        </div>

        {/* Company logos */}
        <div className="mt-16 pt-12 border-t border-white/[0.05]">
          <p className="text-center text-white/30 text-sm mb-8">Powering video intelligence at</p>
          <div className="flex justify-center items-center gap-12 flex-wrap">
            {['TechFlow', 'DevScale', 'MediaPro', 'StartupAI', 'CloudNine'].map((company) => (
              <span key={company} className="text-2xl font-bold text-white/20 hover:text-white/40 transition-colors">
                {company}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* API Preview Section */}
      <section className="relative z-10 max-w-6xl mx-auto px-6 py-24">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-3xl md:text-4xl font-bold mb-6">Developer-First API</h2>
            <p className="text-white/50 mb-8 text-lg leading-relaxed">
              Simple, powerful APIs that integrate with your existing workflows.
              Process videos, extract insights, and deploy applications programmatically.
            </p>
            <div className="flex gap-4">
              <Link href="/playground" className="btn btn-primary">
                View API Docs
              </Link>
              <Link href="/playground" className="btn btn-secondary">
                Try Playground
              </Link>
            </div>
          </div>

          {/* Code preview */}
          <div className="bg-surface-900/80 backdrop-blur-xl rounded-2xl border border-white/[0.08] p-6 font-mono text-sm overflow-hidden shadow-2xl shadow-primary-500/5">
            <div className="flex gap-2 mb-6">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <div className="w-3 h-3 rounded-full bg-green-500/80" />
            </div>
            <pre className="text-white/70 overflow-x-auto leading-relaxed">
{`// Analyze a video with one API call
const result = await uvai.video.analyze({
  url: "https://youtube.com/watch?v=...",
  options: {
    extract: ["summary", "actions", "code"],
    deploy: true
  }
});

// Get results in 2.3 seconds
console.log(result.summary);
// => "This tutorial covers React hooks..."

console.log(result.actions);
// => ["Implement useState", "Add useEffect..."]

console.log(result.deployedUrl);
// => "https://app-xyz.uvai.io"`}
            </pre>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 max-w-4xl mx-auto px-6 py-24 text-center">
        <div className="bg-gradient-to-br from-primary-500/10 to-accent-500/10 backdrop-blur-xl rounded-3xl border border-white/[0.08] p-12 md:p-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Ready to Transform Your Video Workflow?
          </h2>
          <p className="text-white/50 mb-10 max-w-xl mx-auto text-lg">
            Join thousands of teams using UVAI to extract intelligence from video content
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link href="/dashboard" className="btn btn-primary text-lg px-10 py-4">
              Start Free Trial
            </Link>
            <a href="mailto:enterprise@uvai.io" className="btn btn-secondary text-lg px-10 py-4">
              Contact Sales
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/[0.05] px-6 py-16">
        <div className="max-w-6xl mx-auto">
          {/* Footer Top */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
            {/* Brand Column */}
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-bold shadow-lg shadow-primary-500/25">
                  U
                </div>
                <span className="font-bold text-lg">UVAI.io</span>
              </div>
              <p className="text-white/40 text-sm leading-relaxed mb-4">
                Transform any video into interactive learning experiences with AI.
              </p>
              {/* Social Icons */}
              <div className="flex gap-3">
                <a
                  href="https://github.com/groupthinking/EventRelay"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] flex items-center justify-center transition-colors"
                  aria-label="GitHub"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" className="text-white/60 hover:text-white">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                </a>
                <a
                  href="https://twitter.com/uvai_io"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] flex items-center justify-center transition-colors"
                  aria-label="Twitter"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" className="text-white/60 hover:text-white">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                  </svg>
                </a>
                <a
                  href="https://discord.gg/uvai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] flex items-center justify-center transition-colors"
                  aria-label="Discord"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" className="text-white/60 hover:text-white">
                    <path d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 00-.041-.106 13.107 13.107 0 01-1.872-.892.077.077 0 01-.008-.128 10.2 10.2 0 00.372-.292.074.074 0 01.077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 01.078.01c.12.098.246.198.373.292a.077.077 0 01-.006.127 12.299 12.299 0 01-1.873.892.077.077 0 00-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
                  </svg>
                </a>
              </div>
            </div>

            {/* Product Column */}
            <div>
              <h4 className="font-semibold text-white mb-4">Product</h4>
              <ul className="space-y-3 text-sm">
                <li><Link href="/dashboard" className="text-white/40 hover:text-white transition-colors">Dashboard</Link></li>
                <li><Link href="/playground" className="text-white/40 hover:text-white transition-colors">API Playground</Link></li>
                <li><Link href="/docs" className="text-white/40 hover:text-white transition-colors">Documentation</Link></li>
                <li><Link href="/pricing" className="text-white/40 hover:text-white transition-colors">Pricing</Link></li>
              </ul>
            </div>

            {/* Resources Column */}
            <div>
              <h4 className="font-semibold text-white mb-4">Resources</h4>
              <ul className="space-y-3 text-sm">
                <li><Link href="/blog" className="text-white/40 hover:text-white transition-colors">Blog</Link></li>
                <li><Link href="/changelog" className="text-white/40 hover:text-white transition-colors">Changelog</Link></li>
                <li><Link href="/support" className="text-white/40 hover:text-white transition-colors">Support</Link></li>
                <li><Link href="/status" className="text-white/40 hover:text-white transition-colors">Status</Link></li>
              </ul>
            </div>

            {/* Company Column */}
            <div>
              <h4 className="font-semibold text-white mb-4">Company</h4>
              <ul className="space-y-3 text-sm">
                <li><Link href="/about" className="text-white/40 hover:text-white transition-colors">About</Link></li>
                <li><Link href="/privacy" className="text-white/40 hover:text-white transition-colors">Privacy</Link></li>
                <li><Link href="/terms" className="text-white/40 hover:text-white transition-colors">Terms</Link></li>
                <li><a href="mailto:hello@uvai.io" className="text-white/40 hover:text-white transition-colors">Contact</a></li>
              </ul>
            </div>
          </div>

          {/* Footer Bottom */}
          <div className="pt-8 border-t border-white/[0.05] flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-white/30 text-sm">
              © 2026 UVAI.io. Built with AI by <span className="text-primary-400">Aaron Wade</span>
            </p>
            <div className="flex items-center gap-2 text-white/30 text-sm">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400" />
              </span>
              All systems operational
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}