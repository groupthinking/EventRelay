'use client';

import Link from 'next/link';
import { useState, useEffect, useRef } from 'react';
import { clsx } from 'clsx';

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

  useEffect(() => {
    setIsLoaded(true);
  }, []);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (videoUrl.trim()) {
      window.location.href = `/dashboard?video=${encodeURIComponent(videoUrl)}`;
    }
  };

  return (
    <main className="min-h-screen text-white overflow-hidden">
      {/* Animated background */}
      <FloatingOrbs />

      {/* Navigation */}
      <nav className="relative z-50 flex items-center justify-between px-6 lg:px-12 py-4 border-b border-white/[0.05]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-lg shadow-lg shadow-primary-500/25">
            U
          </div>
          <span className="font-bold text-xl tracking-tight">UVAI.io</span>
        </div>
        <div className="hidden md:flex items-center gap-8">
          <Link href="/dashboard" className="text-white/60 hover:text-white transition-colors font-medium">
            Dashboard
          </Link>
          <Link href="/playground" className="text-white/60 hover:text-white transition-colors font-medium">
            API
          </Link>
          <Link href="/docs" className="text-white/60 hover:text-white transition-colors font-medium">
            Docs
          </Link>
          <Link
            href="/dashboard"
            className="btn btn-primary"
          >
            Get Started
            <span className="ml-1">→</span>
          </Link>
        </div>
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
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-black leading-[0.95] mb-8 tracking-tight">
            <span className="block text-white">
              Transform Video into
            </span>
            <span className="block bg-gradient-to-r from-primary-400 via-accent-400 to-primary-400 bg-clip-text text-transparent bg-[length:200%_auto] animate-gradient">
              Actionable Intelligence
            </span>
          </h1>

          {/* Subheadline */}
          <p className="text-xl md:text-2xl text-white/50 max-w-2xl mx-auto mb-12 leading-relaxed font-light">
            Stop watching. Start acting. UVAI extracts insights, generates action items,
            and deploys live applications from any video in{' '}
            <strong className="text-accent-400 font-semibold">2.3 seconds</strong>.
          </p>

          {/* Main CTA Input */}
          <form onSubmit={handleAnalyze} className="max-w-2xl mx-auto mb-16">
            <div className="flex gap-3 p-2 rounded-2xl bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl shadow-2xl shadow-primary-500/5">
              <input
                type="text"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="Paste any YouTube URL or video link..."
                className="flex-1 px-5 py-4 bg-transparent text-white placeholder:text-white/30 focus:outline-none text-lg"
              />
              <button
                type="submit"
                className="px-8 py-4 rounded-xl bg-gradient-to-r from-primary-500 to-primary-600 font-bold text-lg hover:shadow-xl hover:shadow-primary-500/25 transition-all hover:-translate-y-0.5 flex items-center gap-2"
              >
                Analyze Now
                <span className="text-xl">→</span>
              </button>
            </div>
          </form>

          {/* Stats */}
          <div className="flex justify-center gap-16 md:gap-24">
            <AnimatedCounter value="50K" suffix="+" label="Videos Processed" />
            <AnimatedCounter value="2.3" suffix="s" label="Avg Processing Time" />
            <AnimatedCounter value="7" label="AI Brains Connected" />
            <AnimatedCounter value="99.9" suffix="%" label="Uptime SLA" />
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
      <footer className="relative z-10 border-t border-white/[0.05] px-6 py-12">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-bold shadow-lg shadow-primary-500/25">
              U
            </div>
            <span className="font-bold">UVAI.io</span>
            <span className="text-white/30 text-sm ml-2">© 2026</span>
          </div>
          <div className="flex gap-8 text-white/40 text-sm">
            <Link href="/privacy" className="hover:text-white transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-white transition-colors">Terms</Link>
            <Link href="https://github.com/groupthinking/EventRelay" className="hover:text-white transition-colors">GitHub</Link>
            <Link href="https://twitter.com/uvai_io" className="hover:text-white transition-colors">Twitter</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}