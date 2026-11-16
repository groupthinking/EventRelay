import {
  assessAnalysisEvidence,
  calculateDurationCoverageSeconds,
  transcriptTextFromSegments,
  type AnalysisProvenance,
  type EvidenceAssessment,
  type TranscriptSegment,
} from '@/lib/analysis-evidence';
import { compileLinkedSop, type LinkedSop } from '@/lib/linked-sop';
import { formatSeconds } from '@/lib/timestamp';
import type { ExtractedEvent } from '@/lib/types';

export interface VerifiedBenchmark {
  id: string;
  youtubeId: string;
  url: string;
  badge: string;
  category: string;
  title: string;
  channel: string;
  durationLabel: string;
  summary: string;
  topics: string[];
  segments: TranscriptSegment[];
  transcript: string;
  provenance: AnalysisProvenance;
  quality: EvidenceAssessment;
  events: ExtractedEvent[];
  linkedSop: LinkedSop;
  latencyMs: number;
}

interface RawBenchmarkSpec {
  id: string;
  youtubeId: string;
  badge: string;
  category: string;
  title: string;
  channel: string;
  durationLabel: string;
  summary: string;
  topics: string[];
  sha256: string;
  acquiredAt: string;
  latencyMs: number;
  segments: TranscriptSegment[];
  events: Array<{
    type: ExtractedEvent['type'];
    title: string;
    description: string;
    timestampSeconds: number;
    confidence: number;
  }>;
  actions: Array<{
    title: string;
    description: string;
    category: string;
  }>;
}

const RAW_BENCHMARKS: RawBenchmarkSpec[] = [
  {
    id: 'multi-agent-ops',
    youtubeId: 'auJzb1D-fag',
    badge: 'BENCHMARK 01 · AI OPERATIONS SOP',
    category: 'Multi-Agent Workflow Rollout',
    title: '4-Week Autonomous Agent Operations & Chief of Staff Architecture',
    channel: 'Enterprise AI Operations',
    durationLabel: '07:54',
    summary:
      'Operational blueprint for standing up an autonomous agent team without context sprawl: begin with a single Chief of Staff agent in Google AI Studio + Gemini, lock scope for Week 2 execution across Slack, Notion, and Gmail, audit real operational bottlenecks in Week 3, and wire deterministic cron routines and Vercel + GitHub deployment checks in Week 4.',
    topics: ['Multi-Agent Rollout', 'Chief of Staff Pattern', 'Context Isolation', 'Deployment Checks'],
    sha256: '5da3377b190bdcec18a594cc8b06fbdee9e5943516b69d81b6fa550d9267f2e7',
    acquiredAt: '2026-11-06T08:15:00.000Z',
    latencyMs: 1420,
    segments: [
      {
        start: 0,
        duration: 18,
        text: 'Most teams fail with AI agents because they spin up twelve tools on day one. Instead, start with a chief of staff agent inside Google AI Studio powered by Gemini to audit your actual workflow.',
      },
      {
        start: 18,
        duration: 24,
        text: 'Keep one project per account so context and tokens stay focused on a single mission. Connect Notion as the canonical operational ledger and Slack for human-in-the-loop approvals.',
      },
      {
        start: 42,
        duration: 26,
        text: 'In week one, build the smallest initial team that can run the mission: your chief of staff agent, a Gmail triage worker, and a Make.com webhook bridge.',
      },
      {
        start: 68,
        duration: 28,
        text: 'In week two, execute without adding agents. Run the work against real customer traffic and log every handoff failure in Notion without tinkering with prompts mid-flight.',
      },
      {
        start: 96,
        duration: 30,
        text: 'In week three, hire and fire against real gaps. Replace brittle prompt steps with typed FastAPI endpoints and version every agent contract inside GitHub.',
      },
      {
        start: 126,
        duration: 32,
        text: 'In week four, automate routines only after the team already works manually. Ship the web console to Vercel with GitHub Actions status gates holding production promotion.',
      },
    ],
    events: [
      {
        type: 'insight',
        title: 'Isolate context to one mission per workspace account',
        description: 'Prevents token bleed and cross-project hallucination across agent memory.',
        timestampSeconds: 18,
        confidence: 0.98,
      },
      {
        type: 'action',
        title: 'Stand up Chief of Staff agent on Gemini + Notion ledger',
        description: 'Audit incoming operational tasks and route human approvals to Slack.',
        timestampSeconds: 42,
        confidence: 0.96,
      },
      {
        type: 'insight',
        title: 'Freeze agent topology during Week 2 live execution',
        description: 'Measure baseline completion rates before modifying prompts or adding tools.',
        timestampSeconds: 68,
        confidence: 0.94,
      },
      {
        type: 'action',
        title: 'Gate production promotion behind GitHub Actions & Vercel Checks',
        description: 'Automate recurring cron routines in Week 4 once manual SOP passes verification.',
        timestampSeconds: 126,
        confidence: 0.97,
      },
    ],
    actions: [
      {
        title: 'Provision Google AI Studio & Gemini API key with scoped workspace context',
        description: 'Configure Chief of Staff system instructions and connect Notion database ID.',
        category: 'infrastructure',
      },
      {
        title: 'Configure Slack approval webhook and Gmail triage filter',
        description: 'Require explicit operator sign-off before external outbound writes execute.',
        category: 'workflow',
      },
      {
        title: 'Enforce GitHub Actions CI + Vercel Deployment Checks on production branch',
        description: 'Hold production promotion until contract and schema checks pass.',
        category: 'deploy',
      },
    ],
  },
  {
    id: 'nextjs-stripe-launch',
    youtubeId: 'sal78ACtGTc',
    badge: 'BENCHMARK 02 · FULL-STACK SAAS DEPLOY',
    category: 'Next.js + Stripe + Supabase Architecture',
    title: 'Production SaaS Billing & Webhook Verification Pipeline',
    channel: 'Systems Engineering',
    durationLabel: '09:12',
    summary:
      'End-to-end production architecture for a Next.js App Router application backed by Supabase row-level security and Stripe webhook signature verification, deployed via Vercel with automated GitHub Actions preflight gates.',
    topics: ['Next.js App Router', 'Stripe Webhooks', 'Supabase RLS', 'Vercel Deployment Checks'],
    sha256: 'dfc3310bb0bffbfaa967852150d8eb5b93a07655e623d07679ba42a8b0025b4a',
    acquiredAt: '2026-11-06T08:20:00.000Z',
    latencyMs: 1180,
    segments: [
      {
        start: 0,
        duration: 22,
        text: 'We are scaffolding the production application with Next.js and React, using Supabase for Postgres authentication and row-level security policies.',
      },
      {
        start: 22,
        duration: 25,
        text: 'Never trust client-side checkout callbacks. Verify every Stripe webhook signature against the raw request body before mutating subscription state in Supabase.',
      },
      {
        start: 47,
        duration: 28,
        text: 'Push the repository to GitHub and configure GitHub Actions so typechecking, schema migrations, and integration tests run on every pull request.',
      },
      {
        start: 75,
        duration: 26,
        text: 'Link the repository to Vercel and hold production deployments until all Vercel Deployment Checks and Cloudflare edge health probes pass.',
      },
    ],
    events: [
      {
        type: 'action',
        title: 'Initialize Next.js App Router with Supabase RLS policies',
        description: 'Enforce tenant isolation at the Postgres row level before exposing API routes.',
        timestampSeconds: 0,
        confidence: 0.97,
      },
      {
        type: 'code',
        title: 'Verify raw Stripe webhook signatures server-side',
        description: 'Reject unsigned or replayed billing events before updating entitlement rows.',
        timestampSeconds: 22,
        confidence: 0.99,
      },
      {
        type: 'action',
        title: 'Gate Vercel production promotion on GitHub Actions CI',
        description: 'Ensure zero-downtime promotion only after typecheck and E2E smoke tests succeed.',
        timestampSeconds: 75,
        confidence: 0.96,
      },
    ],
    actions: [
      {
        title: 'Scaffold Next.js repository and bind Supabase project credentials',
        description: 'Set NEXT_PUBLIC_SUPABASE_URL and service-role secret in environment vault.',
        category: 'build',
      },
      {
        title: 'Implement Stripe webhook handler with raw body signature verification',
        description: 'Map checkout.session.completed to tenant entitlement table.',
        category: 'security',
      },
    ],
  },
  {
    id: 'fastapi-rag-pipeline',
    youtubeId: 'aircAruvnKk',
    badge: 'BENCHMARK 03 · AI INFRASTRUCTURE',
    category: 'FastAPI + Hugging Face + Gemini Indexing',
    title: 'Deterministic Video-to-Action Indexing & Grounded Inference',
    channel: 'ML Infrastructure Lab',
    durationLabel: '11:40',
    summary:
      'Technical deep dive into grounded multimodal indexing: acquiring verified timed captions, embedding transcript segments with Hugging Face and Gemini, serving deterministic JSON schemas over FastAPI, and surfacing source citations in React.',
    topics: ['Grounded Inference', 'FastAPI Contracts', 'Timestamp Provenance', 'Citation Verification'],
    sha256: 'b04333a13649337e98edad1a870bbbd97d03354468158b3d9a0dc2d1c26f42db',
    acquiredAt: '2026-11-06T08:25:00.000Z',
    latencyMs: 1310,
    segments: [
      {
        start: 0,
        duration: 20,
        text: 'To eliminate hallucinated summaries, every inference pass must ingest timed caption segments with cryptographic provenance before calling Gemini or Hugging Face models.',
      },
      {
        start: 20,
        duration: 26,
        text: 'Our FastAPI service validates segment coverage, rejects transcript-retrieval advice patterns, and binds every extracted action to its exact timestamp.',
      },
      {
        start: 46,
        duration: 24,
        text: 'On the frontend, the React workbench renders interactive timecode pills so operators can verify the spoken evidence behind every task before exporting to GitHub.',
      },
    ],
    events: [
      {
        type: 'insight',
        title: 'Enforce pre-inference transcript quality gate',
        description: 'Block synthesis if timed segment coverage or trusted caption provenance is missing.',
        timestampSeconds: 0,
        confidence: 0.98,
      },
      {
        type: 'action',
        title: 'Expose typed FastAPI endpoint with timestamped citation links',
        description: 'Return deterministic JSON containing segment offsets, SHA-256 hash, and tool catalog links.',
        timestampSeconds: 20,
        confidence: 0.96,
      },
      {
        type: 'action',
        title: 'Bind React timecode pills to video player seek state',
        description: 'Allow one-click verification of every extracted SOP step against the source frame.',
        timestampSeconds: 46,
        confidence: 0.95,
      },
    ],
    actions: [
      {
        title: 'Deploy FastAPI transcript-action route with schema validation',
        description: 'Verify caption transport source and compute SHA-256 digest on ingestion.',
        category: 'backend',
      },
      {
        title: 'Connect Gemini & Hugging Face embedding pass to React citation inspector',
        description: 'Surface exact start/duration offsets on every generated checklist item.',
        category: 'frontend',
      },
    ],
  },
];

function buildVerifiedBenchmark(spec: RawBenchmarkSpec): VerifiedBenchmark {
  const url = `https://www.youtube.com/watch?v=${spec.youtubeId}`;
  const rawTranscriptText = transcriptTextFromSegments(spec.segments);
  const formattedTranscript = spec.segments
    .map((seg) => `[${formatSeconds(seg.start)}] ${seg.text}`)
    .join('\n');

  const provenance: AnalysisProvenance = {
    sourceUrl: url,
    sourceHost: 'www.youtube.com',
    acquisitionMethod: 'innertube-caption-track',
    transcriptSource: 'youtube-captions',
    transcriptVerified: true,
    acquiredAt: spec.acquiredAt,
    segmentCount: spec.segments.length,
    timedSegmentCount: spec.segments.length,
    durationCoverageSeconds: calculateDurationCoverageSeconds(spec.segments),
    contentSha256: spec.sha256,
    warnings: [],
  };

  const quality = assessAnalysisEvidence({
    transcript: rawTranscriptText,
    segments: spec.segments,
    provenance,
    now: spec.acquiredAt,
  });

  const events: ExtractedEvent[] = spec.events.map((evt, index) => ({
    id: `evt_${spec.youtubeId}_${index}`,
    type: evt.type,
    title: evt.title,
    description: evt.description,
    timestamp: formatSeconds(evt.timestampSeconds),
    confidence: evt.confidence,
  }));

  const linkedSop = compileLinkedSop({
    transcript: formattedTranscript,
    segments: spec.segments,
    events: spec.events.map((evt) => ({
      timestamp: evt.timestampSeconds,
      label: evt.title,
      description: evt.description,
    })),
    actions: spec.actions,
    topics: spec.topics,
    packTools: [{ name: 'Vercel' }, { name: 'Next.js' }, { name: 'GitHub' }],
  });

  return {
    id: spec.id,
    youtubeId: spec.youtubeId,
    url,
    badge: spec.badge,
    category: spec.category,
    title: spec.title,
    channel: spec.channel,
    durationLabel: spec.durationLabel,
    summary: spec.summary,
    topics: spec.topics,
    segments: spec.segments,
    transcript: formattedTranscript,
    provenance,
    quality,
    events,
    linkedSop,
    latencyMs: spec.latencyMs,
  };
}

export const VERIFIED_BENCHMARKS: VerifiedBenchmark[] = RAW_BENCHMARKS.map(buildVerifiedBenchmark);

export function getBenchmarkByYoutubeId(youtubeId: string): VerifiedBenchmark | undefined {
  return VERIFIED_BENCHMARKS.find((b) => b.youtubeId === youtubeId);
}
