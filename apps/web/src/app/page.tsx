'use client';

import Link from 'next/link';
import { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { useRouter } from 'next/navigation';

// ============================================
// Sidebar Component
// ============================================
function Sidebar() {
  const [activeTab, setActiveTab] = useState<'history' | 'projects' | 'timeline'>('history');

  return (
    <aside className="hidden lg:flex flex-col w-[260px] min-h-screen bg-[#0d0e14] border-r border-white/[0.06] fixed left-0 top-0 z-40">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-white/[0.06]">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center">
          <span className="text-sm font-black">U</span>
        </div>
        <div>
          <div className="font-bold text-sm text-white">UVAI</div>
          <div className="text-[11px] text-white/40">Video Intelligence</div>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="px-4 py-4">
        <Link
          href="/dashboard"
          className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-600 text-white text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          <span className="text-lg">+</span> New Chat
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex mx-4 bg-white/[0.04] rounded-lg p-0.5">
        {(['history', 'projects', 'timeline'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              'flex-1 py-1.5 text-xs font-medium rounded-md capitalize transition-all',
              activeTab === tab
                ? 'bg-white/[0.08] text-white shadow-sm'
                : 'text-white/40 hover:text-white/60'
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {activeTab === 'history' && (
          <div className="space-y-3">
            <div className="text-[11px] text-white/30 font-medium uppercase tracking-wider">Today</div>
            <div className="text-sm text-white/50 italic py-8 text-center">
              No history yet. Process a video to get started.
            </div>
          </div>
        )}
        {activeTab === 'projects' && (
          <div className="text-sm text-white/50 italic py-8 text-center">
            No projects yet.
          </div>
        )}
        {activeTab === 'timeline' && (
          <div className="text-sm text-white/50 italic py-8 text-center">
            No events yet.
          </div>
        )}
      </div>

      {/* Bottom */}
      <div className="border-t border-white/[0.06] px-4 py-3 space-y-1">
        <Link href="/playground" className="flex items-center gap-2 text-xs text-white/40 hover:text-white/60 transition py-1">
          <span>📡</span> API Playground
        </Link>
        <div className="flex items-center gap-2 text-xs text-white/30 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Connected v2.0.0
        </div>
      </div>
    </aside>
  );
}

// ============================================
// MCP Tool Card
// ============================================
function MCPToolCard({
  icon,
  color,
  title,
  description,
  delay = 0,
}: {
  icon: string;
  color: string;
  title: string;
  description: string;
  delay?: number;
}) {
  return (
    <div
      className="group relative rounded-xl bg-white/[0.03] border border-white/[0.06] p-5 hover:bg-white/[0.06] hover:border-white/[0.12] transition-all duration-300 cursor-pointer animate-fade-in-up opacity-0"
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'forwards' }}
    >
      <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center text-lg mb-3', color)}>
        {icon}
      </div>
      <h3 className="font-semibold text-white text-sm mb-1">{title}</h3>
      <p className="text-white/40 text-xs leading-relaxed">{description}</p>
    </div>
  );
}

// ============================================
// Use Case Card
// ============================================
function UseCaseCard({
  title,
  description,
  features,
  accentColor,
  delay = 0,
}: {
  title: string;
  description: string;
  features: string[];
  accentColor: string;
  delay?: number;
}) {
  return (
    <div
      className={clsx(
        'rounded-xl bg-white/[0.03] border border-white/[0.06] p-6',
        'hover:border-transparent transition-all duration-300 cursor-pointer',
        'animate-fade-in-up opacity-0',
        accentColor
      )}
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'forwards' }}
    >
      <h3 className="font-bold text-white mb-2">{title}</h3>
      <p className="text-white/50 text-sm mb-4 leading-relaxed">{description}</p>
      <ul className="space-y-1.5">
        {features.map((feature) => (
          <li key={feature} className="flex items-center gap-2 text-xs text-white/40">
            <span className="w-1 h-1 rounded-full bg-white/30" />
            {feature}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ============================================
// Workflow Card
// ============================================
function WorkflowCard({
  title,
  description,
  icon,
  delay = 0,
}: {
  title: string;
  description: string;
  icon: string;
  delay?: number;
}) {
  return (
    <div
      className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-5 hover:bg-white/[0.06] transition-all duration-300 animate-fade-in-up opacity-0"
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'forwards' }}
    >
      <div className="text-2xl mb-3">{icon}</div>
      <h3 className="font-semibold text-white text-sm mb-1">{title}</h3>
      <p className="text-white/40 text-xs leading-relaxed">{description}</p>
    </div>
  );
}

// ============================================
// Main Page
// ============================================
export default function Home() {
  const [videoUrl, setVideoUrl] = useState('');
  const [activeSection, setActiveSection] = useState<'tools' | 'stories' | 'usecases' | 'workflows'>('tools');
  const router = useRouter();

  const handleProcess = useCallback(() => {
    if (!videoUrl.trim()) return;
    router.push(`/dashboard?video=${encodeURIComponent(videoUrl)}`);
  }, [videoUrl, router]);

  return (
    <div className="min-h-screen text-white bg-[#0a0b10]">
      <Sidebar />

      {/* Main Content */}
      <div className="lg:ml-[260px] min-h-screen">
        {/* Top Header */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            {/* Mobile logo */}
            <div className="lg:hidden flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center font-black text-sm">
                U
              </div>
              <span className="font-bold">UVAI.io</span>
            </div>
            <span className="hidden lg:block text-white/50 text-sm">New Chat</span>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/dashboard"
              className="px-3 py-1.5 rounded-lg text-xs text-white/50 hover:text-white/80 hover:bg-white/[0.05] transition"
            >
              Dashboard
            </Link>
            <Link
              href="/playground"
              className="px-3 py-1.5 rounded-lg text-xs text-white/50 hover:text-white/80 hover:bg-white/[0.05] transition"
            >
              API Playground
            </Link>
          </div>
        </header>

        {/* Hero */}
        <div className="max-w-4xl mx-auto px-6 pt-16 pb-8">
          {/* Badge */}
          <div className="flex justify-center mb-8">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/60">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              Powered by Gemini 2.0 • MCP Agents
            </div>
          </div>

          {/* Headline */}
          <h1 className="text-4xl md:text-6xl font-black text-center leading-tight mb-5">
            Video → <span className="bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">Intelligence</span> → Action
          </h1>
          <p className="text-center text-white/40 text-lg max-w-2xl mx-auto mb-12 leading-relaxed">
            Transform any video into actionable intelligence and deployed software.
            Extract transcripts, identify events, generate code — all in seconds.
          </p>

          {/* Central Input */}
          <div className="relative mx-auto max-w-2xl">
            <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-2 hover:border-white/[0.15] transition-colors focus-within:border-cyan-500/30 focus-within:shadow-lg focus-within:shadow-cyan-500/5">
              <div className="flex items-center gap-3">
                <span className="pl-3 text-white/30">🔗</span>
                <input
                  type="text"
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleProcess()}
                  placeholder="Paste YouTube URL or describe what you want to do..."
                  className="flex-1 bg-transparent text-white placeholder:text-white/30 outline-none text-sm py-2"
                />
                <button
                  onClick={handleProcess}
                  disabled={!videoUrl.trim()}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-600 text-white text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <span>▶</span> Process
                </button>
              </div>
            </div>

            {/* Context chips */}
            <div className="flex items-center gap-3 mt-3 justify-center">
              {[
                { icon: '💬', label: 'Context' },
                { icon: '📎', label: 'Files' },
                { icon: '🔗', label: 'URLs' },
                { icon: '⚡', label: 'Workflow' },
              ].map((chip) => (
                <button
                  key={chip.label}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-xs text-white/40 hover:text-white/60 hover:bg-white/[0.06] transition"
                >
                  <span>{chip.icon}</span> {chip.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Section Toggle Pills */}
        <div className="max-w-4xl mx-auto px-6 pb-6">
          <div className="flex justify-center gap-2">
            {([
              { key: 'tools', label: 'MCP Tools' },
              { key: 'stories', label: 'Success Stories' },
              { key: 'usecases', label: 'Use Cases' },
              { key: 'workflows', label: 'Workflows' },
            ] as const).map((section) => (
              <button
                key={section.key}
                onClick={() => setActiveSection(section.key)}
                className={clsx(
                  'px-4 py-2 rounded-full text-xs font-medium transition-all',
                  activeSection === section.key
                    ? 'bg-white/[0.1] text-white border border-white/[0.15]'
                    : 'text-white/40 hover:text-white/60 border border-transparent'
                )}
              >
                {section.label}
              </button>
            ))}
          </div>
        </div>

        {/* Section Content */}
        <div className="max-w-5xl mx-auto px-6 pb-20">

          {/* MCP Tools */}
          {activeSection === 'tools' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold">MCP Agent Tools</h2>
                <Link href="/playground" className="text-xs text-cyan-400 hover:text-cyan-300 transition">
                  View API →
                </Link>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
                <MCPToolCard
                  icon="CC"
                  color="bg-cyan-500/15 text-cyan-400"
                  title="Extract Transcript"
                  description="Word-perfect transcripts with speaker diarization, timestamps, and 50+ language support."
                  delay={100}
                />
                <MCPToolCard
                  icon="⚡"
                  color="bg-orange-500/15 text-orange-400"
                  title="Extract Events"
                  description="Automatically identify action items, key moments, decisions, and structured events."
                  delay={200}
                />
                <MCPToolCard
                  icon="🧠"
                  color="bg-purple-500/15 text-purple-400"
                  title="Full Analysis"
                  description="Comprehensive AI analysis with sentiment, topics, summaries, and action plans."
                  delay={300}
                />
                <MCPToolCard
                  icon="<>"
                  color="bg-green-500/15 text-green-400"
                  title="Video to Software"
                  description="Transform tutorial videos into working, deployable applications automatically."
                  delay={400}
                />
              </div>

              {/* Example prompts */}
              <h3 className="text-sm font-semibold text-white/60 mb-4">Try These Examples</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {[
                  { text: 'Extract transcript from conference talk', accent: 'hover:border-cyan-500/30' },
                  { text: 'Find key decisions from board meeting', accent: 'hover:border-orange-500/30' },
                  { text: 'Analyze sentiment of product review', accent: 'hover:border-purple-500/30' },
                  { text: 'Generate app from tutorial video', accent: 'hover:border-green-500/30' },
                ].map((ex) => (
                  <button
                    key={ex.text}
                    onClick={() => setVideoUrl(ex.text)}
                    className={clsx(
                      'text-left px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.06] text-sm text-white/50 hover:text-white/70 transition-all',
                      ex.accent
                    )}
                  >
                    {ex.text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Success Stories */}
          {activeSection === 'stories' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {[
                {
                  quote: 'UVAI transformed our content workflow. We process 50+ videos weekly and extract actionable insights in minutes instead of hours.',
                  gradient: 'from-cyan-500/10 to-purple-500/10',
                },
                {
                  quote: 'The Video-to-Software feature is game-changing. We turned a 2-hour tutorial into a working prototype in under 10 minutes.',
                  gradient: 'from-purple-500/10 to-pink-500/10',
                },
                {
                  quote: 'MCP integration lets our AI assistant process videos directly. It\'s like having a research team available 24/7.',
                  gradient: 'from-orange-500/10 to-yellow-500/10',
                },
              ].map((story, i) => (
                <div
                  key={i}
                  className={clsx(
                    'rounded-xl bg-gradient-to-br p-[1px] animate-fade-in-up opacity-0',
                    story.gradient
                  )}
                  style={{ animationDelay: `${i * 150}ms`, animationFillMode: 'forwards' }}
                >
                  <div className="rounded-xl bg-surface-900/95 p-6 h-full">
                    <div className="text-3xl mb-3">"</div>
                    <p className="text-white/60 text-sm leading-relaxed italic">{story.quote}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Use Cases */}
          {activeSection === 'usecases' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <UseCaseCard
                title="Education & Training"
                description="Convert lecture videos into searchable transcripts, study guides, and interactive quizzes automatically."
                features={['Auto-generate study notes', 'Create chapter markers', 'Extract key concepts']}
                accentColor="hover:border-cyan-500/30"
                delay={100}
              />
              <UseCaseCard
                title="Meeting Intelligence"
                description="Transform recorded meetings into actionable insights with automatic action item extraction."
                features={['Extract action items', 'Identify decisions', 'Generate summaries']}
                accentColor="hover:border-orange-500/30"
                delay={200}
              />
              <UseCaseCard
                title="Content Repurposing"
                description="Turn long-form videos into blog posts, social media content, and marketing materials."
                features={['Create blog posts', 'Extract quotes', 'Generate social clips']}
                accentColor="hover:border-purple-500/30"
                delay={300}
              />
              <UseCaseCard
                title="AI Agent Integration"
                description="Connect UVAI to your AI assistants via MCP for automated video processing workflows."
                features={['MCP-compatible', 'Works with Claude & GPT', 'Webhook support']}
                accentColor="hover:border-green-500/30"
                delay={400}
              />
            </div>
          )}

          {/* Workflows */}
          {activeSection === 'workflows' && (
            <div>
              <h2 className="text-lg font-bold mb-6">Automated Workflows</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <WorkflowCard
                  icon="📦"
                  title="Batch Processing"
                  description="Upload a list of YouTube URLs and process them all simultaneously."
                  delay={100}
                />
                <WorkflowCard
                  icon="⏰"
                  title="Scheduled Analysis"
                  description="Schedule automatic processing of videos at specific times or intervals."
                  delay={200}
                />
                <WorkflowCard
                  icon="📺"
                  title="Channel Monitor"
                  description="Automatically process new uploads from specified YouTube channels."
                  delay={300}
                />
                <WorkflowCard
                  icon="🔧"
                  title="Custom Pipeline"
                  description="Chain multiple tools together with custom logic for your video processing."
                  delay={400}
                />
              </div>
            </div>
          )}
        </div>

        {/* Bottom Stats */}
        <div className="border-t border-white/[0.06] py-8">
          <div className="max-w-4xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            <div>
              <div className="text-2xl font-black text-white">2.3s</div>
              <div className="text-xs text-white/30 mt-1">Avg Processing</div>
            </div>
            <div>
              <div className="text-2xl font-black text-white">50+</div>
              <div className="text-xs text-white/30 mt-1">Languages</div>
            </div>
            <div>
              <div className="text-2xl font-black text-white">300+</div>
              <div className="text-xs text-white/30 mt-1">Edge Locations</div>
            </div>
            <div>
              <div className="text-2xl font-black text-white">99.9%</div>
              <div className="text-xs text-white/30 mt-1">Uptime</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}