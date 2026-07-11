'use client';

import Link from 'next/link';
import { useState } from 'react';
import { clsx } from 'clsx';
import LandingNav from '@/components/landing/LandingNav';
import TemplatesSection from '@/components/landing/TemplatesSection';
import Footer from '@/components/Footer';

// ─── Visual Mockup Components ──────────────────────────────────────────────────

function TranscriptMockup() {
  const lines = [
    { ts: '00:00', speaker: 'Host', text: 'Welcome back. Today we are covering—', conf: 98 },
    { ts: '00:04', speaker: 'Host', text: 'distributed consensus algorithms at scale.', conf: 99 },
    { ts: '00:09', speaker: 'Guest', text: 'Right. The key insight is that Raft separates', conf: 97 },
    { ts: '00:14', speaker: 'Guest', text: 'leader election from log replication entirely.', conf: 99 },
    { ts: '00:19', speaker: 'Host', text: 'And that is why it is easier to reason about—', conf: 96 },
  ];
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-surface-950/80 overflow-hidden font-mono text-xs">
      {/* header bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
        <span className="text-white/30 text-[11px] tracking-wide uppercase">transcript.json</span>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-[10px] text-teal-400/80">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
            Processing
          </span>
        </div>
      </div>
      <div className="divide-y divide-white/[0.04]">
        {lines.map((l, i) => (
          <div key={i} className="flex items-start gap-3 px-4 py-2.5 hover:bg-white/[0.02] transition-colors group">
            <span className="text-white/20 w-10 shrink-0 tabular-nums pt-0.5">{l.ts}</span>
            <span className={clsx(
              'shrink-0 w-12 text-[10px] font-semibold uppercase tracking-wider pt-0.5',
              l.speaker === 'Host' ? 'text-teal-400/70' : 'text-cyan-400/70'
            )}>{l.speaker}</span>
            <span className="text-white/60 leading-relaxed flex-1">{l.text}</span>
            <span className="text-white/20 text-[10px] tabular-nums pt-0.5 opacity-0 group-hover:opacity-100 transition-opacity">{l.conf}%</span>
          </div>
        ))}
      </div>
      <div className="px-4 py-3 border-t border-white/[0.06] flex items-center justify-between bg-white/[0.01]">
        <span className="text-white/20 text-[11px]">5 segments · 0.8s latency</span>
        <span className="text-teal-400/60 text-[11px]">Whisper v3 → YT captions</span>
      </div>
    </div>
  );
}

function EventStreamMockup() {
  const events = [
    { domain: 'video', entity: 'segment', action: 'created', ts: '14:23:01.021', color: 'text-teal-400' },
    { domain: 'ai', entity: 'insight', action: 'detected', ts: '14:23:01.104', color: 'text-cyan-400' },
    { domain: 'task', entity: 'action_item', action: 'extracted', ts: '14:23:01.198', color: 'text-blue-400' },
    { domain: 'sentiment', entity: 'segment', action: 'scored', ts: '14:23:01.241', color: 'text-indigo-400' },
    { domain: 'topic', entity: 'cluster', action: 'labeled', ts: '14:23:01.305', color: 'text-purple-400' },
  ];
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-surface-950/80 overflow-hidden font-mono text-xs">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
        <span className="text-white/30 text-[11px] tracking-wide uppercase">event-stream</span>
        <span className="text-white/20 text-[10px]">live</span>
      </div>
      <div className="divide-y divide-white/[0.03]">
        {events.map((e, i) => (
          <div key={i} className="flex items-center gap-3 px-4 py-2 hover:bg-white/[0.02] transition-colors">
            <span className="text-white/15 tabular-nums text-[10px] shrink-0 w-24">{e.ts}</span>
            <span className={clsx('font-semibold shrink-0', e.color)}>
              {e.domain}<span className="text-white/20">.</span>{e.entity}<span className="text-white/20">.</span>{e.action}
            </span>
          </div>
        ))}
      </div>
      <div className="px-4 py-2.5 border-t border-white/[0.06] bg-white/[0.01] flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
        <span className="text-white/20 text-[11px]">5 events dispatched · 0 dropped</span>
      </div>
    </div>
  );
}

function ChatMockup() {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-surface-950/80 overflow-hidden text-xs flex flex-col">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
        <span className="text-white/30 text-[11px] tracking-wide uppercase font-mono">video-chat</span>
        <span className="text-[10px] text-white/20 font-mono">GPT-4o · ctx: full</span>
      </div>
      <div className="flex flex-col gap-3 p-4">
        {/* user message */}
        <div className="flex justify-end">
          <div className="max-w-[80%] bg-teal-500/15 border border-teal-500/20 rounded-xl rounded-tr-sm px-3 py-2 text-white/80 leading-relaxed">
            What did they decide about the API rate limits?
          </div>
        </div>
        {/* ai response */}
        <div className="flex gap-2.5">
          <div className="w-5 h-5 rounded-md bg-teal-500/20 border border-teal-500/30 flex items-center justify-center shrink-0 mt-0.5">
            <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
              <circle cx="6" cy="6" r="4" stroke="rgb(45 212 191)" strokeWidth="1.5"/>
              <circle cx="6" cy="6" r="1.5" fill="rgb(45 212 191)"/>
            </svg>
          </div>
          <div className="flex-1 bg-white/[0.04] border border-white/[0.06] rounded-xl rounded-tl-sm px-3 py-2 text-white/60 leading-relaxed">
            At <span className="text-teal-400 font-mono">14:32</span>, the team agreed to cap public API calls at{' '}
            <span className="text-white/80 font-semibold">500 req/min</span> with a burst allowance of{' '}
            <span className="text-white/80 font-semibold">2×</span> for 10s windows.{' '}
            <span className="text-teal-400/60">Marcus</span> was assigned to update the docs.
          </div>
        </div>
      </div>
      <div className="px-4 pb-4">
        <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-white/20 text-[11px]">
          Ask anything about this video...
        </div>
      </div>
    </div>
  );
}

function ExportMockup() {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-surface-950/80 overflow-hidden font-mono text-xs">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
        <span className="text-white/30 text-[11px] tracking-wide uppercase">POST</span>
        <span className="text-white/50">/api/v1/export</span>
        <span className="ml-auto text-green-400/70 text-[10px]">200 OK · 42ms</span>
      </div>
      <div className="p-4 text-[11px] leading-relaxed">
        <div className="text-white/20">{'{'}</div>
        <div className="pl-4">
          <div><span className="text-cyan-400">&quot;id&quot;</span><span className="text-white/30">: </span><span className="text-green-300/70">&quot;evt_01HZQR5F...&quot;</span><span className="text-white/20">,</span></div>
          <div><span className="text-cyan-400">&quot;format&quot;</span><span className="text-white/30">: </span><span className="text-green-300/70">&quot;notion&quot;</span><span className="text-white/20">,</span></div>
          <div><span className="text-cyan-400">&quot;events&quot;</span><span className="text-white/30">: </span><span className="text-white/40">[ 14 action items ]</span><span className="text-white/20">,</span></div>
          <div><span className="text-cyan-400">&quot;destination&quot;</span><span className="text-white/30">: </span><span className="text-green-300/70">&quot;Engineering Notes&quot;</span><span className="text-white/20">,</span></div>
          <div><span className="text-cyan-400">&quot;status&quot;</span><span className="text-white/30">: </span><span className="text-teal-400">&quot;synced&quot;</span></div>
        </div>
        <div className="text-white/20">{'}'}</div>
      </div>
      <div className="px-4 pt-0 pb-4 flex flex-wrap gap-1.5">
        {['JSON', 'CSV', 'Notion', 'Slack', 'REST API'].map(t => (
          <span key={t} className="px-2 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.06] text-white/40 text-[10px]">{t}</span>
        ))}
      </div>
    </div>
  );
}

function DeployMockup() {
  const steps = [
    { label: 'Extract audio', status: 'done' },
    { label: 'Transcribe', status: 'done' },
    { label: 'Generate code', status: 'done' },
    { label: 'Push to GitHub', status: 'active' },
    { label: 'Deploy to Vercel', status: 'pending' },
  ];
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-surface-950/80 overflow-hidden font-mono text-xs">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
        <span className="text-white/30 text-[11px] tracking-wide uppercase">deploy-pipeline</span>
        <span className="text-pink-400/70 text-[10px]">experimental</span>
      </div>
      <div className="p-4 space-y-2">
        {steps.map((s, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className={clsx(
              'w-4 h-4 rounded-full flex items-center justify-center shrink-0',
              s.status === 'done' && 'bg-teal-500/20 border border-teal-500/30',
              s.status === 'active' && 'bg-yellow-500/20 border border-yellow-500/40',
              s.status === 'pending' && 'bg-white/[0.04] border border-white/[0.08]',
            )}>
              {s.status === 'done' && (
                <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                  <path d="M1.5 4L3 5.5L6.5 2" stroke="rgb(45 212 191)" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              )}
              {s.status === 'active' && <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />}
            </div>
            <span className={clsx(
              s.status === 'done' && 'text-white/40 line-through',
              s.status === 'active' && 'text-white/80',
              s.status === 'pending' && 'text-white/20',
            )}>{s.label}</span>
            {s.status === 'active' && <span className="text-yellow-400/60 text-[10px] ml-auto">running…</span>}
            {s.status === 'done' && <span className="text-white/15 text-[10px] ml-auto">done</span>}
          </div>
        ))}
      </div>
      <div className="px-4 pb-4">
        <div className="rounded-lg bg-white/[0.02] border border-white/[0.04] px-3 py-2 text-[10px] text-white/20 font-mono">
          <span className="text-white/30">$</span> uvai deploy --watch youtube.com/watch?v=...
        </div>
      </div>
    </div>
  );
}

function McpMockup() {
  const agents = [
    { name: 'task-extractor', status: 'subscribed', events: 3 },
    { name: 'notion-writer', status: 'subscribed', events: 1 },
    { name: 'slack-notifier', status: 'subscribed', events: 2 },
    { name: 'custom-agent', status: 'idle', events: 0 },
  ];
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-surface-950/80 overflow-hidden font-mono text-xs">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
        <span className="text-white/30 text-[11px] tracking-wide uppercase">mcp-bus</span>
        <span className="text-cyan-400/60 text-[10px]">4 agents connected</span>
      </div>
      <div className="divide-y divide-white/[0.03]">
        {agents.map((a, i) => (
          <div key={i} className="flex items-center gap-3 px-4 py-2.5 hover:bg-white/[0.02] transition-colors">
            <span className={clsx(
              'w-1.5 h-1.5 rounded-full shrink-0',
              a.status === 'subscribed' ? 'bg-teal-400 animate-pulse' : 'bg-white/20'
            )} />
            <span className="text-white/60 flex-1">{a.name}</span>
            <span className={clsx(
              'text-[10px] px-1.5 py-0.5 rounded border',
              a.status === 'subscribed'
                ? 'text-teal-400/70 bg-teal-500/10 border-teal-500/20'
                : 'text-white/20 bg-white/[0.03] border-white/[0.06]'
            )}>{a.status}</span>
            {a.events > 0 && (
              <span className="text-white/30 text-[10px] tabular-nums">{a.events} evt</span>
            )}
          </div>
        ))}
      </div>
      <div className="px-4 py-2.5 border-t border-white/[0.06] bg-white/[0.01]">
        <span className="text-white/15 text-[11px]">Shared state: 6 keys · Last write 0.3s ago</span>
      </div>
    </div>
  );
}

// ─── Data ──────────────────────────────────────────────────────────────────────

const SECTIONS = [
  {
    id: 'transcription',
    tag: 'Core Processing',
    tagColor: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400',
    title: 'Transcription that actually works',
    subtitle:
      'Full verbatim transcripts with speaker timestamps — in under 60 seconds. No manual editing. No post-processing.',
    mockup: <TranscriptMockup />,
    bullets: [
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="2" y="3" width="12" height="2" rx="1" fill="currentColor" opacity="0.8"/>
            <rect x="2" y="7" width="8" height="2" rx="1" fill="currentColor" opacity="0.5"/>
            <rect x="2" y="11" width="10" height="2" rx="1" fill="currentColor" opacity="0.3"/>
          </svg>
        ),
        title: 'YouTube captions first',
        desc: "We use YouTube's own accurate captions as the primary source — fastest path to a clean transcript.",
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="5" stroke="currentColor" strokeWidth="1.5" opacity="0.7"/>
            <path d="M6 8.5L7.5 10L10 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        ),
        title: 'Whisper STT fallback',
        desc: "When captions are unavailable, OpenAI's state-of-the-art speech-to-text runs on the extracted audio.",
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" opacity="0.6"/>
            <path d="M8 2C8 2 10.5 5 10.5 8C10.5 11 8 14 8 14" stroke="currentColor" strokeWidth="1" opacity="0.4"/>
            <path d="M2 8H14" stroke="currentColor" strokeWidth="1" opacity="0.4"/>
          </svg>
        ),
        title: '90+ languages',
        desc: 'Automatic language detection and transcription — works globally without configuration.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5" opacity="0.6"/>
            <path d="M8 4.5V8L10.5 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        ),
        title: 'Timestamped paragraphs',
        desc: 'Every paragraph is anchored to its video timestamp — jump to any moment in one click.',
      },
    ],
  },
  {
    id: 'ai',
    tag: 'AI Intelligence',
    tagColor: 'bg-violet-500/10 border-violet-500/20 text-violet-400',
    title: 'AI that extracts meaning, not just words',
    subtitle:
      'Gemini 2.0 and GPT-4o go beyond transcription to surface what actually matters in any video.',
    mockup: <EventStreamMockup />,
    bullets: [
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 12L7 6L10 9L13 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.7"/>
          </svg>
        ),
        title: 'Event & action item extraction',
        desc: 'Decisions made, tasks assigned, and next steps automatically identified and categorized.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 2L10 6L14 6.5L11 9.5L11.5 14L8 12L4.5 14L5 9.5L2 6.5L6 6L8 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" opacity="0.7"/>
          </svg>
        ),
        title: 'Key insight detection',
        desc: 'Notable quotes, important data points, and expert opinions surfaced and highlighted.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="2" y="9" width="3" height="5" rx="0.5" fill="currentColor" opacity="0.3"/>
            <rect x="6.5" y="6" width="3" height="8" rx="0.5" fill="currentColor" opacity="0.5"/>
            <rect x="11" y="3" width="3" height="11" rx="0.5" fill="currentColor" opacity="0.7"/>
          </svg>
        ),
        title: 'Sentiment & topic modeling',
        desc: 'Emotional tone and topic segmentation across the full timeline — understand the shape of any discussion.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="2" y="3" width="12" height="2" rx="0.5" fill="currentColor" opacity="0.7"/>
            <rect x="2" y="7" width="9" height="1.5" rx="0.5" fill="currentColor" opacity="0.4"/>
            <rect x="2" y="10.5" width="11" height="1.5" rx="0.5" fill="currentColor" opacity="0.3"/>
          </svg>
        ),
        title: 'Multi-level summaries',
        desc: 'TLDR to full executive brief — summaries at whatever detail level your team needs.',
      },
    ],
  },
  {
    id: 'chat',
    tag: 'Video Chat',
    tagColor: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
    title: 'Ask questions. Get answers instantly.',
    subtitle:
      'Every video becomes a knowledge base you can query in plain English. No more scrubbing through recordings.',
    mockup: <ChatMockup />,
    bullets: [
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.5" opacity="0.7"/>
            <path d="M10.5 10.5L13.5 13.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.7"/>
          </svg>
        ),
        title: 'Ask anything about the video',
        desc: '"What did they decide about the API architecture?" — get a precise, sourced answer in milliseconds.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 5H13M3 8H10M3 11H12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.7"/>
          </svg>
        ),
        title: 'Full-transcript context',
        desc: 'The model knows the complete transcript and event timeline — not just a retrieved snippet.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 13L5 10H13C13.6 10 14 9.6 14 9V3C14 2.4 13.6 2 13 2H3C2.4 2 2 2.4 2 3V13Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" opacity="0.7"/>
          </svg>
        ),
        title: 'Persistent chat history',
        desc: 'Your conversation is saved and searchable — build on previous questions across sessions.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5" opacity="0.6"/>
            <path d="M8 4.5V8L10.5 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        ),
        title: 'Timestamp-linked answers',
        desc: 'Every answer links back to the exact moment in the video for instant verification.',
      },
    ],
  },
  {
    id: 'export',
    tag: 'Export & Integrations',
    tagColor: 'bg-green-500/10 border-green-500/20 text-green-400',
    title: 'Your data, wherever you need it',
    subtitle:
      'Export structured intelligence to the tools your team already uses. One call, fully formatted.',
    mockup: <ExportMockup />,
    bullets: [
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 4H12V12H4V4Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" opacity="0.6"/>
            <path d="M6 7H10M6 9.5H8.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.5"/>
          </svg>
        ),
        title: 'JSON & CSV export',
        desc: 'Machine-readable structured event data for developers, spreadsheets, and automation pipelines.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="2.5" y="2.5" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="1.5" opacity="0.6"/>
            <path d="M5.5 8H10.5M8 5.5V10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.5"/>
          </svg>
        ),
        title: 'Notion integration',
        desc: 'Push a full meeting summary with checklists directly into a Notion page — one API call.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 6H12C12.6 6 13 6.4 13 7V12C13 12.6 12.6 13 12 13H4C3.4 13 3 12.6 3 12V7C3 6.4 3.4 6 4 6Z" stroke="currentColor" strokeWidth="1.5" opacity="0.6"/>
            <path d="M6 6V4.5C6 3.7 6.7 3 7.5 3H8.5C9.3 3 10 3.7 10 4.5V6" stroke="currentColor" strokeWidth="1.5" opacity="0.4"/>
          </svg>
        ),
        title: 'Slack integration',
        desc: 'Post a formatted summary and action item digest to any channel automatically.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 8H14M8 2L8 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.5"/>
            <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5" opacity="0.6"/>
          </svg>
        ),
        title: 'Full REST API',
        desc: 'All functionality available programmatically. OpenAPI spec included. Build anything on top.',
      },
    ],
  },
  {
    id: 'deploy',
    tag: 'Deploy Pipeline',
    tagColor: 'bg-pink-500/10 border-pink-500/20 text-pink-400',
    isExperimental: true,
    title: 'Watch a tutorial. Deploy a working app.',
    subtitle:
      'Our experimental deploy pipeline watches a coding tutorial and produces a running application — fully automated.',
    mockup: <DeployMockup />,
    bullets: [
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="2" y="3" width="12" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.5" opacity="0.6"/>
            <path d="M5 7L7 9L11 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.7"/>
          </svg>
        ),
        title: 'Automated code generation',
        desc: 'GPT-4o watches the tutorial and writes the corresponding implementation from scratch.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="5" r="2.5" stroke="currentColor" strokeWidth="1.5" opacity="0.7"/>
            <circle cx="3" cy="12" r="1.5" stroke="currentColor" strokeWidth="1.5" opacity="0.5"/>
            <circle cx="13" cy="12" r="1.5" stroke="currentColor" strokeWidth="1.5" opacity="0.5"/>
            <path d="M6 7L4 10.5M10 7L12 10.5" stroke="currentColor" strokeWidth="1.2" opacity="0.4"/>
          </svg>
        ),
        title: 'GitHub repo creation',
        desc: 'Code is committed to a new GitHub repository under your account automatically.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 2L14 5V11L8 14L2 11V5L8 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" opacity="0.6"/>
          </svg>
        ),
        title: 'Vercel one-click deploy',
        desc: 'The repo is deployed to Vercel and a live preview URL is returned in seconds.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 8H8M8 8V3M8 8L13 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.6"/>
            <path d="M3 13H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.3"/>
          </svg>
        ),
        title: 'Configurable pipeline',
        desc: 'Bring your own GITHUB_TOKEN and Vercel credentials for full control over the output.',
      },
    ],
  },
  {
    id: 'mcp',
    tag: 'MCP Agent System',
    tagColor: 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400',
    title: 'Dispatch AI agents on extracted events',
    subtitle:
      'UVAI is built around the Model Context Protocol. Extracted events become triggers for intelligent, composable agents.',
    mockup: <McpMockup />,
    bullets: [
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="2" fill="currentColor" opacity="0.7"/>
            <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5" opacity="0.3"/>
            <path d="M8 2.5V5M8 11V13.5M2.5 8H5M11 8H13.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4"/>
          </svg>
        ),
        title: 'Structured event routing',
        desc: 'Events follow domain.entity.action naming and are dispatched to the correct agent automatically.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="5" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.5" opacity="0.7"/>
            <circle cx="11" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" opacity="0.5"/>
            <circle cx="11" cy="11" r="2" stroke="currentColor" strokeWidth="1.5" opacity="0.5"/>
            <path d="M7.5 8H9M7.5 7L9 6M7.5 9L9 10" stroke="currentColor" strokeWidth="1" opacity="0.4"/>
          </svg>
        ),
        title: 'Multi-agent dispatch',
        desc: 'Multiple specialized agents can act on the same event stream in parallel — no coordination overhead.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="2.5" y="2.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" opacity="0.6"/>
            <rect x="8.5" y="8.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" opacity="0.4"/>
            <path d="M8 5.5H10C11.1 5.5 12 6.4 12 7.5V8" stroke="currentColor" strokeWidth="1.2" opacity="0.4"/>
          </svg>
        ),
        title: 'Custom agent support',
        desc: 'Any MCP-compatible agent can subscribe to UVAI\'s event bus — no vendor lock-in.',
      },
      {
        icon: (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 5H13M3 8H13M3 11H10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.6"/>
          </svg>
        ),
        title: 'Shared state coordination',
        desc: 'The shared-state MCP server lets agents read and write a common knowledge store synchronously.',
      },
    ],
  },
];

const COMPARISON_ROWS = [
  { feature: 'Full verbatim transcript', er: true, yt: 'Partial captions', otter: true, manual: false },
  { feature: 'AI event extraction', er: true, yt: false, otter: false, manual: false },
  { feature: 'Action item detection', er: true, yt: false, otter: 'Add-on', manual: 'Manual' },
  { feature: 'Video chat / Q&A', er: true, yt: false, otter: false, manual: false },
  { feature: 'Sentiment analysis', er: true, yt: false, otter: false, manual: false },
  { feature: 'Topic segmentation', er: true, yt: 'Chapters only', otter: false, manual: false },
  { feature: 'Notion / Slack export', er: true, yt: false, otter: 'Otter only', manual: false },
  { feature: 'REST API', er: true, yt: false, otter: true, manual: false },
  { feature: 'MCP agent dispatch', er: true, yt: false, otter: false, manual: false },
  { feature: 'Auto-deploy from tutorial', er: true, yt: false, otter: false, manual: false },
  { feature: 'Free tier', er: true, yt: true, otter: true, manual: true },
];

// ─── Sub-components ────────────────────────────────────────────────────────────

function CompCell({ value }: { value: boolean | string }) {
  if (value === true) {
    return (
      <div className="flex justify-center">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-teal-400">
          <path d="M2.5 7L5.5 10L11.5 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
    );
  }
  if (value === false) {
    return <div className="flex justify-center"><span className="text-white/15 text-sm font-mono">—</span></div>;
  }
  return <div className="text-xs text-center text-white/35 font-mono">{value}</div>;
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

export default function FeaturesPage() {
  const [activeSection, setActiveSection] = useState<string | null>(null);

  return (
    <div className="min-h-screen text-white overflow-x-hidden">

      <LandingNav />

      {/* ── Hero ────────────────────────────────────────────────────────────── */}
      <section className="relative pt-32 pb-16 px-6 text-center max-w-4xl mx-auto">
        <div
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-[11px] text-white/40 font-semibold uppercase tracking-widest mb-7 animate-fade-in-up opacity-0"
          style={{ animationDelay: '0ms', animationFillMode: 'forwards' }}
        >
          <span className="w-1 h-1 rounded-full bg-teal-400 opacity-70" />
          Platform Features
        </div>

        <h1
          className="text-5xl md:text-6xl font-black leading-[1.05] tracking-tight mb-5 animate-fade-in-up opacity-0 font-heading text-balance"
          style={{ animationDelay: '80ms', animationFillMode: 'forwards' }}
        >
          Packed with features
          <br />
          <span className="gradient-text">that actually matter</span>
        </h1>

        <p
          className="text-base text-white/45 max-w-xl mx-auto mb-10 leading-relaxed animate-fade-in-up opacity-0"
          style={{ animationDelay: '160ms', animationFillMode: 'forwards' }}
        >
          UVAI goes beyond transcription — extracting structured intelligence, dispatching AI agents,
          and integrating with the tools your team already uses. In under 60 seconds.
        </p>

        <div
          className="flex flex-wrap items-center justify-center gap-3 animate-fade-in-up opacity-0"
          style={{ animationDelay: '240ms', animationFillMode: 'forwards' }}
        >
          <Link href="/dashboard" className="btn btn-primary py-3 px-7 text-sm shadow-lg shadow-primary-500/25">
            Try it free
          </Link>
          <Link href="/pricing" className="btn btn-secondary py-3 px-6 text-sm">
            View pricing
          </Link>
        </div>

        {/* Section nav pills */}
        <div
          className="flex flex-wrap items-center justify-center gap-2 mt-10 animate-fade-in-up opacity-0"
          style={{ animationDelay: '320ms', animationFillMode: 'forwards' }}
        >
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              onClick={() => setActiveSection(s.id)}
              className={clsx(
                'px-3 py-1.5 rounded-full border text-xs font-medium transition-all font-mono tracking-tight',
                activeSection === s.id
                  ? s.tagColor
                  : 'bg-white/[0.03] border-white/[0.06] text-white/35 hover:text-white/60 hover:border-white/[0.1]'
              )}
            >
              {s.tag}
            </a>
          ))}
        </div>
      </section>

      {/* ── Feature Sections ──────────────────────────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-6 space-y-24 mb-28 pt-8">
        {SECTIONS.map((section, sectionIdx) => {
          const isEven = sectionIdx % 2 === 0;
          return (
            <section key={section.id} id={section.id}>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-14 items-center">

                {/* Mockup panel */}
                <div
                  className={clsx(
                    'animate-fade-in-up opacity-0',
                    !isEven && 'lg:order-2'
                  )}
                  style={{ animationDelay: `${sectionIdx * 40}ms`, animationFillMode: 'forwards' }}
                >
                  {/* Window chrome wrapper */}
                  <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] overflow-hidden shadow-2xl">
                    {/* Faux title bar */}
                    <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06] bg-white/[0.01]">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-white/[0.08] border border-white/[0.06]" />
                        <span className="w-2.5 h-2.5 rounded-full bg-white/[0.08] border border-white/[0.06]" />
                        <span className="w-2.5 h-2.5 rounded-full bg-white/[0.08] border border-white/[0.06]" />
                      </div>
                      <div className="flex-1 flex justify-center">
                        <span className={clsx(
                          'text-[10px] px-2.5 py-1 rounded-md border font-mono tracking-wide',
                          section.tagColor
                        )}>
                          {section.tag}
                          {section.isExperimental && (
                            <span className="ml-1.5 text-pink-300/70">· experimental</span>
                          )}
                        </span>
                      </div>
                    </div>
                    <div className="p-4">
                      {section.mockup}
                    </div>
                  </div>
                </div>

                {/* Text panel */}
                <div
                  className={clsx(
                    'animate-fade-in-up opacity-0',
                    !isEven && 'lg:order-1'
                  )}
                  style={{ animationDelay: `${sectionIdx * 40 + 60}ms`, animationFillMode: 'forwards' }}
                >
                  <div className={clsx('inline-flex items-center gap-2 px-2.5 py-1 rounded-md border text-[11px] font-semibold mb-5 font-mono tracking-wide', section.tagColor)}>
                    {section.tag}
                  </div>
                  <h2 className="text-3xl md:text-[2.25rem] font-black tracking-tight mb-4 leading-[1.1] font-heading text-balance">
                    {section.title}
                  </h2>
                  <p className="text-white/45 leading-relaxed mb-8 text-sm max-w-md">
                    {section.subtitle}
                  </p>

                  <ul className="space-y-4">
                    {section.bullets.map((b) => (
                      <li key={b.title} className="flex gap-3.5 group">
                        <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.07] flex items-center justify-center text-white/50 flex-shrink-0 mt-0.5 group-hover:border-white/[0.12] group-hover:text-white/70 transition-all">
                          {b.icon}
                        </div>
                        <div>
                          <div className="font-semibold text-white/90 text-sm mb-0.5">{b.title}</div>
                          <div className="text-xs text-white/40 leading-relaxed">{b.desc}</div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </section>
          );
        })}
      </div>

      {/* ── Stats strip ─────────────────────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 mb-24">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px rounded-2xl overflow-hidden border border-white/[0.06]">
          {[
            { value: '< 60s', label: 'Avg processing time' },
            { value: '94%', label: 'Action item accuracy' },
            { value: '90+', label: 'Languages supported' },
            { value: '12+', label: 'Export integrations' },
          ].map((stat, i) => (
            <div
              key={stat.label}
              className="text-center px-6 py-8 bg-white/[0.02] hover:bg-white/[0.04] transition-colors animate-fade-in-up opacity-0"
              style={{ animationDelay: `${i * 60}ms`, animationFillMode: 'forwards' }}
            >
              <div className="text-3xl font-black gradient-text mb-1.5 font-heading tabular-nums">{stat.value}</div>
              <div className="text-xs text-white/35 font-mono">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Template gallery ────────────────────────────────────────────────── */}
      <TemplatesSection />

      {/* ── Comparison table ─────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 mb-24">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-[11px] text-white/35 font-semibold uppercase tracking-widest mb-5 font-mono">
            vs. Alternatives
          </div>
          <h2 className="text-3xl font-black tracking-tight mb-3 font-heading">
            How UVAI stacks up
          </h2>
          <p className="text-white/35 max-w-sm mx-auto text-sm leading-relaxed">
            Against YouTube auto-chapters, Otter.ai, and the old-fashioned way.
          </p>
        </div>

        <div className="rounded-2xl border border-white/[0.07] overflow-hidden">
          {/* Header row */}
          <div className="grid grid-cols-5 border-b border-white/[0.06] bg-white/[0.02]">
            <div className="p-4 text-xs font-mono text-white/30 uppercase tracking-wider">Feature</div>
            <div className="p-4 text-center">
              <div className="inline-flex flex-col items-center gap-1">
                <span className="text-sm font-bold text-teal-400 font-heading">UVAI</span>
                <span className="px-1.5 py-0.5 rounded-md bg-teal-500/10 text-teal-400 text-[10px] border border-teal-500/20 font-mono">you</span>
              </div>
            </div>
            <div className="p-4 text-xs font-mono font-semibold text-center text-white/30">YT Chapters</div>
            <div className="p-4 text-xs font-mono font-semibold text-center text-white/30">Otter.ai</div>
            <div className="p-4 text-xs font-mono font-semibold text-center text-white/30">Manual</div>
          </div>

          {COMPARISON_ROWS.map((row, i) => (
            <div
              key={row.feature}
              className={clsx(
                'grid grid-cols-5 border-b border-white/[0.04] last:border-0 items-center',
                i % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.01]'
              )}
            >
              <div className="p-4 text-xs text-white/50 font-sans">{row.feature}</div>
              <div className="p-4"><CompCell value={row.er} /></div>
              <div className="p-4"><CompCell value={row.yt} /></div>
              <div className="p-4"><CompCell value={row.otter} /></div>
              <div className="p-4"><CompCell value={row.manual} /></div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Testimonials ────────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 mb-24">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-[11px] text-white/35 font-semibold uppercase tracking-widest mb-5 font-mono">
            Early Users
          </div>
          <h2 className="text-3xl font-black tracking-tight font-heading">What people are saying</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              quote: "Saved 3 hours this week. Used to take notes during every meeting — now I just process the recording.",
              name: 'Sarah K.',
              role: 'Engineering Manager',
              initial: 'S',
              accent: 'bg-violet-500/20 border-violet-500/30 text-violet-300',
            },
            {
              quote: "We process every product demo and conference talk. The event extraction feeds directly into our roadmap.",
              name: 'Marcus T.',
              role: 'Head of Product',
              initial: 'M',
              accent: 'bg-blue-500/20 border-blue-500/30 text-blue-300',
            },
            {
              quote: "The deploy feature is insane. Watched a YouTube tutorial and had a running prototype in 4 minutes.",
              name: 'Priya N.',
              role: 'Founding Engineer',
              initial: 'P',
              accent: 'bg-teal-500/20 border-teal-500/30 text-teal-300',
            },
          ].map((t, i) => (
            <div
              key={t.name}
              className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.1] transition-all animate-fade-in-up opacity-0 flex flex-col"
              style={{ animationDelay: `${i * 100}ms`, animationFillMode: 'forwards' }}
            >
              {/* Stars */}
              <div className="flex gap-0.5 mb-4">
                {[...Array(5)].map((_, j) => (
                  <svg key={j} width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M6 1L7.5 4.5L11.5 5L8.5 8L9 12L6 10L3 12L3.5 8L0.5 5L4.5 4.5L6 1Z" fill="rgb(250 204 21 / 0.8)"/>
                  </svg>
                ))}
              </div>
              <p className="text-white/60 text-sm leading-relaxed mb-5 flex-1">&quot;{t.quote}&quot;</p>
              <div className="flex items-center gap-3">
                <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs border', t.accent)}>
                  {t.initial}
                </div>
                <div>
                  <div className="text-xs font-semibold text-white/80">{t.name}</div>
                  <div className="text-[11px] text-white/30">{t.role}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 pb-24 text-center">
        <div className="p-12 rounded-2xl border border-white/[0.08] bg-white/[0.02] relative overflow-hidden">
          {/* subtle glow */}
          <div className="absolute inset-0 bg-gradient-to-br from-teal-500/[0.06] via-transparent to-cyan-500/[0.04] pointer-events-none" />
          <div className="relative">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/20 text-[11px] text-teal-400 font-semibold tracking-wide mb-6 font-mono">
              Get started free
            </div>
            <h2 className="text-3xl md:text-4xl font-black mb-4 font-heading tracking-tight text-balance">
              See every feature in action
            </h2>
            <p className="text-white/40 mb-8 max-w-md mx-auto text-sm leading-relaxed">
              Paste any YouTube URL and get structured AI intelligence in under 60 seconds.
              No account required. Free forever for personal use.
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              <Link
                href="/dashboard"
                className="btn btn-primary py-3.5 px-8 text-sm shadow-xl shadow-primary-500/20"
              >
                Start analyzing for free
              </Link>
              <Link
                href="/pricing"
                className="btn btn-secondary py-3.5 px-7 text-sm"
              >
                View pricing
              </Link>
            </div>
            <p className="text-[11px] text-white/20 mt-5 font-mono">No credit card required.</p>
          </div>
        </div>
      </section>

      <Footer variant="full" />
    </div>
  );
}
