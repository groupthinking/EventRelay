'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';

// Pipeline stage visualization
function PipelineVisualization() {
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStage((prev) => (prev + 1) % 4);
    }, 2000);
    return () => clearInterval(timer);
  }, []);

  const stages = [
    { name: 'Ingest', icon: '📥', color: 'from-violet-500 to-purple-600', desc: 'Upload or paste any video URL' },
    { name: 'Process', icon: '⚡', color: 'from-purple-500 to-indigo-600', desc: 'AI analyzes in 2.3s avg' },
    { name: 'Transform', icon: '🧠', color: 'from-indigo-500 to-blue-600', desc: 'Extract insights & actions' },
    { name: 'Deploy', icon: '🚀', color: 'from-blue-500 to-cyan-600', desc: 'Generate live applications' },
  ];

  return (
    <div className="relative w-full max-w-4xl mx-auto py-12">
      {/* Connection line */}
      <div className="absolute top-1/2 left-0 right-0 h-1 bg-gradient-to-r from-violet-500 via-purple-500 via-indigo-500 to-blue-500 transform -translate-y-1/2 opacity-20 rounded-full" />
      <div
        className="absolute top-1/2 left-0 h-1 bg-gradient-to-r from-violet-500 via-purple-500 via-indigo-500 to-blue-500 transform -translate-y-1/2 rounded-full transition-all duration-1000"
        style={{ width: `${((activeStage + 1) / 4) * 100}%` }}
      />

      <div className="relative flex justify-between">
        {stages.map((stage, index) => (
          <div
            key={stage.name}
            className={`flex flex-col items-center transition-all duration-500 ${
              index <= activeStage ? 'opacity-100 scale-100' : 'opacity-40 scale-95'
            }`}
          >
            <div
              className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${stage.color} flex items-center justify-center text-3xl shadow-lg transform transition-all duration-300 ${
                index === activeStage ? 'scale-110 shadow-2xl ring-4 ring-white/30' : ''
              }`}
            >
              {stage.icon}
            </div>
            <span className="mt-3 font-bold text-lg text-white">{stage.name}</span>
            <span className="mt-1 text-sm text-white/60 text-center max-w-24">{stage.desc}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Stats counter with animation
function AnimatedCounter({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <div className="text-4xl md:text-5xl font-black bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
        {value}
      </div>
      <div className="text-sm text-white/60 mt-1">{label}</div>
    </div>
  );
}

// Feature card
function FeatureCard({ icon, title, desc, gradient }: { icon: string; title: string; desc: string; gradient: string }) {
  return (
    <div className={`group relative overflow-hidden rounded-2xl bg-gradient-to-br ${gradient} p-[1px]`}>
      <div className="relative rounded-2xl bg-slate-900/90 backdrop-blur-xl p-6 h-full transition-transform group-hover:transform group-hover:scale-[1.02]">
        <div className="text-4xl mb-4">{icon}</div>
        <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
        <p className="text-white/60">{desc}</p>
        {/* Glow effect */}
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </div>
  );
}

// Use case personas
function PersonaCard({ emoji, role, benefit }: { emoji: string; role: string; benefit: string }) {
  return (
    <div className="bg-white/5 backdrop-blur-xl rounded-xl p-6 border border-white/10 hover:border-white/20 transition-all hover:transform hover:scale-105">
      <div className="text-3xl mb-3">{emoji}</div>
      <div className="font-bold text-white mb-2">{role}</div>
      <div className="text-sm text-white/60">{benefit}</div>
    </div>
  );
}

export default function HomePage() {
  const [videoUrl, setVideoUrl] = useState('');

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (videoUrl.trim()) {
      window.location.href = `/dashboard?video=${encodeURIComponent(videoUrl)}`;
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-white overflow-hidden">
      {/* Gradient background effects */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-violet-900/20 via-slate-950 to-slate-950" />
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl" />
      <div className="fixed bottom-0 right-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl" />

      {/* Navigation */}
      <nav className="relative z-50 flex items-center justify-between px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center font-black text-lg">
            U
          </div>
          <span className="font-bold text-xl">UVAI.io</span>
        </div>
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="text-white/60 hover:text-white transition">Dashboard</Link>
          <Link href="/playground" className="text-white/60 hover:text-white transition">API</Link>
          <Link href="/docs" className="text-white/60 hover:text-white transition">Docs</Link>
          <Link
            href="https://api.uvai.io/docs"
            target="_blank"
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 font-medium hover:opacity-90 transition"
          >
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 max-w-6xl mx-auto px-6 pt-20 pb-16">
        <div className="text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="text-sm text-white/80">Powered by Gemini 2.5 Flash + Multi-Agent AI</span>
          </div>

          {/* Main headline - Business focused */}
          <h1 className="text-5xl md:text-7xl font-black leading-tight mb-6">
            <span className="bg-gradient-to-r from-white via-white to-white/80 bg-clip-text text-transparent">
              Transform Video into
            </span>
            <br />
            <span className="bg-gradient-to-r from-violet-400 via-purple-400 to-blue-400 bg-clip-text text-transparent">
              Actionable Intelligence
            </span>
          </h1>

          <p className="text-xl text-white/60 max-w-2xl mx-auto mb-10">
            Stop watching. Start acting. UVAI extracts insights, generates action items,
            and deploys live applications from any video in <strong className="text-cyan-400">2.3 seconds</strong>.
          </p>

          {/* Main CTA - Video URL input */}
          <form onSubmit={handleAnalyze} className="max-w-2xl mx-auto mb-10">
            <div className="flex gap-3 p-2 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl">
              <input
                type="text"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="Paste any YouTube URL or video link..."
                className="flex-1 px-4 py-3 bg-transparent text-white placeholder:text-white/40 focus:outline-none"
              />
              <button
                type="submit"
                className="px-8 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 font-bold hover:opacity-90 transition flex items-center gap-2"
              >
                Analyze Now
                <span className="text-lg">→</span>
              </button>
            </div>
          </form>

          {/* Trust indicators */}
          <div className="flex justify-center gap-12 text-white/40 text-sm">
            <AnimatedCounter value="50K+" label="Videos Processed" />
            <AnimatedCounter value="2.3s" label="Avg Processing Time" />
            <AnimatedCounter value="7" label="AI Brains Connected" />
            <AnimatedCounter value="99.9%" label="Uptime SLA" />
          </div>
        </div>
      </section>

      {/* Pipeline Visualization */}
      <section className="relative z-10 py-16 border-t border-b border-white/5">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-white/80">Video as Data Pipeline</h2>
          <p className="text-white/40">From raw footage to deployed software in seconds</p>
        </div>
        <PipelineVisualization />
      </section>

      {/* Features Section */}
      <section className="relative z-10 max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">The Bloomberg Terminal for Video</h2>
          <p className="text-white/60 max-w-2xl mx-auto">
            Enterprise-grade video intelligence that turns hours of content into actionable insights
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <FeatureCard
            icon="🎬"
            title="Video-to-Software"
            desc="Generate working prototypes and deployable code directly from tutorial videos"
            gradient="from-violet-500/20 to-purple-500/20"
          />
          <FeatureCard
            icon="📊"
            title="Meeting Intelligence"
            desc="Extract action items, decisions, and follow-ups from any meeting recording"
            gradient="from-purple-500/20 to-indigo-500/20"
          />
          <FeatureCard
            icon="🔍"
            title="Content Search"
            desc="Vector-powered semantic search across your entire video library"
            gradient="from-indigo-500/20 to-blue-500/20"
          />
          <FeatureCard
            icon="⚡"
            title="Real-time Processing"
            desc="Stream processing with 2.3s average latency using Gemini 2.5 Flash"
            gradient="from-blue-500/20 to-cyan-500/20"
          />
          <FeatureCard
            icon="🔗"
            title="API-First Design"
            desc="RESTful APIs with WebSocket support for seamless integration"
            gradient="from-cyan-500/20 to-teal-500/20"
          />
          <FeatureCard
            icon="🤖"
            title="Multi-Agent AI"
            desc="7 specialized AI brains working in parallel for comprehensive analysis"
            gradient="from-teal-500/20 to-green-500/20"
          />
        </div>
      </section>

      {/* Personas Section */}
      <section className="relative z-10 max-w-6xl mx-auto px-6 py-20 border-t border-white/5">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">Built for Every Role</h2>
          <p className="text-white/60">From executives to developers, UVAI adapts to your workflow</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <PersonaCard
            emoji="📈"
            role="Account Manager"
            benefit="Get meeting summaries and action items without watching hours of recordings"
          />
          <PersonaCard
            emoji="🔬"
            role="R&D Lead"
            benefit="Deep-dive analysis with frame-by-frame visual intelligence"
          />
          <PersonaCard
            emoji="💻"
            role="Developer"
            benefit="Generate working code and prototypes from video tutorials"
          />
          <PersonaCard
            emoji="📱"
            role="Content Creator"
            benefit="Repurpose long-form video into blogs, clips, and social posts"
          />
        </div>
      </section>

      {/* Testimonials Section - Social Proof */}
      <section className="relative z-10 max-w-6xl mx-auto px-6 py-20 border-t border-white/5">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">Trusted by Forward-Thinking Teams</h2>
          <p className="text-white/60">See how teams are transforming their video workflows</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Testimonial 1 */}
          <div className="bg-gradient-to-br from-violet-500/10 to-purple-500/10 backdrop-blur-xl rounded-2xl border border-white/10 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-violet-400 to-purple-500 flex items-center justify-center text-lg font-bold">
                SK
              </div>
              <div>
                <div className="font-medium text-white">Sarah Kim</div>
                <div className="text-sm text-white/60">VP of Product, TechFlow</div>
              </div>
            </div>
            <p className="text-white/80 italic">
              &ldquo;We process 50+ hours of customer calls weekly. UVAI cut our analysis time from
              days to minutes. The action item extraction is incredibly accurate.&rdquo;
            </p>
            <div className="flex gap-1 mt-4">
              {[1,2,3,4,5].map(i => <span key={i} className="text-yellow-400">★</span>)}
            </div>
          </div>

          {/* Testimonial 2 */}
          <div className="bg-gradient-to-br from-indigo-500/10 to-blue-500/10 backdrop-blur-xl rounded-2xl border border-white/10 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-400 to-blue-500 flex items-center justify-center text-lg font-bold">
                JM
              </div>
              <div>
                <div className="font-medium text-white">James Mitchell</div>
                <div className="text-sm text-white/60">Engineering Lead, DevScale</div>
              </div>
            </div>
            <p className="text-white/80 italic">
              &ldquo;The video-to-code feature is mind-blowing. I paste a tutorial URL and get
              working prototypes in seconds. It&apos;s changed how we onboard new team members.&rdquo;
            </p>
            <div className="flex gap-1 mt-4">
              {[1,2,3,4,5].map(i => <span key={i} className="text-yellow-400">★</span>)}
            </div>
          </div>

          {/* Testimonial 3 */}
          <div className="bg-gradient-to-br from-cyan-500/10 to-teal-500/10 backdrop-blur-xl rounded-2xl border border-white/10 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-400 to-teal-500 flex items-center justify-center text-lg font-bold">
                AR
              </div>
              <div>
                <div className="font-medium text-white">Alex Rodriguez</div>
                <div className="text-sm text-white/60">Content Director, MediaPro</div>
              </div>
            </div>
            <p className="text-white/80 italic">
              &ldquo;We repurpose webinar recordings into blog posts, social clips, and newsletters.
              What took a week now takes an hour. ROI was immediate.&rdquo;
            </p>
            <div className="flex gap-1 mt-4">
              {[1,2,3,4,5].map(i => <span key={i} className="text-yellow-400">★</span>)}
            </div>
          </div>
        </div>

        {/* Company Logos */}
        <div className="mt-12 pt-8 border-t border-white/5">
          <p className="text-center text-white/40 text-sm mb-6">Powering video intelligence at</p>
          <div className="flex justify-center items-center gap-12 flex-wrap opacity-60">
            <span className="text-2xl font-bold text-white/60">TechFlow</span>
            <span className="text-2xl font-bold text-white/60">DevScale</span>
            <span className="text-2xl font-bold text-white/60">MediaPro</span>
            <span className="text-2xl font-bold text-white/60">StartupAI</span>
            <span className="text-2xl font-bold text-white/60">CloudNine</span>
          </div>
        </div>
      </section>

      {/* API Preview Section */}
      <section className="relative z-10 max-w-6xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-3xl font-bold mb-6">Developer-First API</h2>
            <p className="text-white/60 mb-8">
              Simple, powerful APIs that integrate with your existing workflows.
              Process videos, extract insights, and deploy applications programmatically.
            </p>
            <div className="flex gap-4">
              <Link
                href="https://api.uvai.io/docs"
                target="_blank"
                className="px-6 py-3 rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 font-medium hover:opacity-90 transition"
              >
                View API Docs
              </Link>
              <Link
                href="/api"
                className="px-6 py-3 rounded-lg border border-white/20 font-medium hover:bg-white/5 transition"
              >
                Try Playground
              </Link>
            </div>
          </div>
          <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-white/10 p-6 font-mono text-sm overflow-hidden">
            <div className="flex gap-2 mb-4">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <div className="w-3 h-3 rounded-full bg-green-500" />
            </div>
            <pre className="text-white/80 overflow-x-auto">
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
      <section className="relative z-10 max-w-4xl mx-auto px-6 py-20 text-center">
        <div className="bg-gradient-to-br from-violet-500/10 to-purple-500/10 backdrop-blur-xl rounded-3xl border border-white/10 p-12">
          <h2 className="text-4xl font-bold mb-4">Ready to Transform Your Video Workflow?</h2>
          <p className="text-white/60 mb-8 max-w-xl mx-auto">
            Join thousands of teams using UVAI to extract intelligence from video content
          </p>
          <div className="flex justify-center gap-4">
            <Link
              href="/dashboard"
              className="px-8 py-4 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 font-bold text-lg hover:opacity-90 transition"
            >
              Start Free Trial
            </Link>
            <Link
              href="mailto:enterprise@uvai.io"
              className="px-8 py-4 rounded-xl border border-white/20 font-bold text-lg hover:bg-white/5 transition"
            >
              Contact Sales
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/5 px-6 py-12">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center font-bold">
              U
            </div>
            <span className="font-bold">UVAI.io</span>
            <span className="text-white/40 text-sm ml-2">© 2026</span>
          </div>
          <div className="flex gap-6 text-white/40 text-sm">
            <Link href="/privacy" className="hover:text-white transition">Privacy</Link>
            <Link href="/terms" className="hover:text-white transition">Terms</Link>
            <Link href="https://github.com/groupthinking/EventRelay" className="hover:text-white transition">GitHub</Link>
            <Link href="https://twitter.com/uvai_io" className="hover:text-white transition">Twitter</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}