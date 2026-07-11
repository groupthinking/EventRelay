'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { clsx } from 'clsx';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Code2,
  ExternalLink,
  FileWarning,
  Play,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  Video,
  Workflow,
} from 'lucide-react';
import AgentFlowVisualizer from '@/components/AgentFlowVisualizer';
import TracePanel from '@/components/TracePanel';
import { Badge, Button, Card, CardContent, CardHeader, Input } from '@/components/ui';
import type { AgentConnection, AgentNode, NodePositionMap, TraceStep } from '@/lib/agent-types';

type ScenarioId = 'happy' | 'fallback' | 'schema';
type ScreenId = 'intake' | 'fallback' | 'context' | 'validation' | 'orchestration' | 'launch';

const DEFAULT_VIDEO_URL = 'https://www.youtube.com/watch?v=ASABxNenD_U';

const NOTE_SIGNALS = [
  'Extract solving context from transcript data, not just raw playback.',
  'Generate code or workflow outputs directly from the extracted context.',
  'Use agents to set up, test, and publish outputs with error capture in the loop.',
];

const FLOW_SUMMARY = [
  'Paste a video URL and define the target output.',
  'Review the extracted solving context before generation runs.',
  'Let the agent pipeline scaffold, verify, and package the result.',
];

const ACCEPTANCE_CRITERIA = [
  'A user can move from URL intake to a launch-ready package in one guided flow.',
  'The system surfaces structured context: concepts, pseudocode, and build targets.',
  'Generation is never silent: the prototype always exposes the active agent stage and trace.',
  'Two critical failures are recoverable in-flow: missing transcript data and invalid build schema.',
];

const SCREEN_LABELS: Record<ScreenId, string> = {
  intake: 'Source intake',
  fallback: 'Transcript fallback',
  context: 'Context review',
  validation: 'Schema repair',
  orchestration: 'Agent execution',
  launch: 'Launch package',
};

const SCENARIOS: Record<
  ScenarioId,
  {
    label: string;
    description: string;
    assumption: string;
    sequence: ScreenId[];
  }
> = {
  happy: {
    label: 'Happy path',
    description: 'A complete tutorial-to-app run with no intervention required.',
    assumption: 'Assumption: the first prototype optimizes for one video URL and one generated app scaffold.',
    sequence: ['intake', 'context', 'orchestration', 'launch'],
  },
  fallback: {
    label: 'No captions',
    description: 'The user hits a transcript gap and chooses the STT fallback path.',
    assumption: 'Assumption: when captions are missing, OpenAI speech-to-text is the default fallback rather than blocking the run.',
    sequence: ['intake', 'fallback', 'context', 'orchestration', 'launch'],
  },
  schema: {
    label: 'Schema mismatch',
    description: 'The generated build plan fails validation and is regenerated before execution.',
    assumption: 'Assumption: strict JSON/schema validation gates agent execution before tests or deployment begin.',
    sequence: ['intake', 'context', 'validation', 'orchestration', 'launch'],
  },
};

const NODE_POSITIONS: NodePositionMap = {
  intake: { x: 24, y: 24, width: 180, height: 96 },
  context: { x: 260, y: 24, width: 180, height: 96 },
  scaffold: { x: 496, y: 24, width: 180, height: 96 },
  verify: { x: 142, y: 196, width: 180, height: 96 },
  launch: { x: 378, y: 196, width: 180, height: 96 },
};

const BASE_AGENTS = {
  intake: {
    id: 'intake',
    name: 'Source intake',
    role: 'orchestrator' as const,
    description: 'Normalize the URL, infer the output target, and open a runnable job.',
  },
  context: {
    id: 'context',
    name: 'Context extractor',
    role: 'transcript_analyst' as const,
    description: 'Distill concepts, pseudocode, and project structure from transcript evidence.',
  },
  scaffold: {
    id: 'scaffold',
    name: 'Scaffold generator',
    role: 'action_generator' as const,
    description: 'Turn the extracted context into a structured build plan and starter code.',
  },
  verify: {
    id: 'verify',
    name: 'Verification loop',
    role: 'quality_checker' as const,
    description: 'Run schema validation, tests, and fix-forward checks before release.',
  },
  launch: {
    id: 'launch',
    name: 'Launch router',
    role: 'router' as const,
    description: 'Package the approved scaffold as a preview app and deployment handoff.',
  },
};

const BASE_CONNECTIONS = [
  { id: 'c1', from: 'intake', to: 'context', label: 'source brief' },
  { id: 'c2', from: 'context', to: 'scaffold', label: 'build plan' },
  { id: 'c3', from: 'scaffold', to: 'verify', label: 'checks' },
  { id: 'c4', from: 'verify', to: 'launch', label: 'preview bundle' },
];

function buildAgents(screen: ScreenId): Record<string, AgentNode> {
  const statusMap = {
    intake: { intake: 'running', context: 'idle', scaffold: 'idle', verify: 'idle', launch: 'idle' },
    fallback: { intake: 'complete', context: 'error', scaffold: 'idle', verify: 'idle', launch: 'idle' },
    context: { intake: 'complete', context: 'complete', scaffold: 'pending', verify: 'idle', launch: 'idle' },
    validation: { intake: 'complete', context: 'complete', scaffold: 'error', verify: 'pending', launch: 'idle' },
    orchestration: { intake: 'complete', context: 'complete', scaffold: 'complete', verify: 'running', launch: 'pending' },
    launch: { intake: 'complete', context: 'complete', scaffold: 'complete', verify: 'complete', launch: 'complete' },
  } as const;

  const progressMap = {
    intake: { intake: 36, context: 0, scaffold: 0, verify: 0, launch: 0 },
    fallback: { intake: 100, context: 64, scaffold: 0, verify: 0, launch: 0 },
    context: { intake: 100, context: 100, scaffold: 18, verify: 0, launch: 0 },
    validation: { intake: 100, context: 100, scaffold: 82, verify: 16, launch: 0 },
    orchestration: { intake: 100, context: 100, scaffold: 100, verify: 72, launch: 22 },
    launch: { intake: 100, context: 100, scaffold: 100, verify: 100, launch: 100 },
  } as const;

  return Object.fromEntries(
    Object.entries(BASE_AGENTS).map(([key, agent]) => [
      key,
      {
        ...agent,
        status: statusMap[screen][key as keyof typeof BASE_AGENTS],
        progress: progressMap[screen][key as keyof typeof BASE_AGENTS],
      },
    ]),
  );
}

function buildConnections(screen: ScreenId): AgentConnection[] {
  return BASE_CONNECTIONS.map((connection) => {
    if (screen === 'intake') {
      return {
        ...connection,
        active: connection.id === 'c1',
        dataFlowing: connection.id === 'c1',
      };
    }

    if (screen === 'fallback') {
      return {
        ...connection,
        active: connection.id === 'c1',
        dataFlowing: false,
      };
    }

    if (screen === 'context') {
      return {
        ...connection,
        active: connection.id === 'c1' || connection.id === 'c2',
        dataFlowing: connection.id === 'c2',
      };
    }

    if (screen === 'validation') {
      return {
        ...connection,
        active: connection.id === 'c1' || connection.id === 'c2' || connection.id === 'c3',
        dataFlowing: false,
      };
    }

    if (screen === 'orchestration') {
      return {
        ...connection,
        active: true,
        dataFlowing: connection.id === 'c3',
      };
    }

    return {
      ...connection,
      active: true,
      dataFlowing: connection.id === 'c4',
    };
  });
}

function buildTrace(screen: ScreenId, videoUrl: string): TraceStep[] {
  const now = new Date('2026-03-20T11:42:00.000Z');
  const at = (seconds: number) => new Date(now.getTime() + seconds * 1000).toISOString();

  const baseTrace: TraceStep[] = [
    {
      id: 'trace-1',
      agentId: 'intake',
      agentName: 'Source intake',
      agentRole: 'orchestrator',
      status: 'complete',
      timestamp: at(0),
      durationMs: 420,
      input: {
        type: 'video_url',
        preview: videoUrl,
      },
      output: {
        type: 'brief',
        preview: 'Target: turn a tutorial video into a launchable starter app with visible execution trace.',
      },
    },
  ];

  if (screen === 'intake') {
    return [
      ...baseTrace,
      {
        id: 'trace-2',
        agentId: 'context',
        agentName: 'Context extractor',
        agentRole: 'transcript_analyst',
        status: 'running',
        timestamp: at(1),
        input: {
          type: 'transcript_probe',
          preview: 'Checking YouTube transcript availability and transcript quality...',
        },
      },
    ];
  }

  if (screen === 'fallback') {
    return [
      ...baseTrace,
      {
        id: 'trace-2',
        agentId: 'context',
        agentName: 'Context extractor',
        agentRole: 'transcript_analyst',
        status: 'error',
        timestamp: at(1),
        durationMs: 1180,
        error: 'Native captions unavailable. Prompt user to continue with speech-to-text fallback.',
      },
    ];
  }

  const contextTrace: TraceStep[] = [
    ...baseTrace,
    {
      id: 'trace-2',
      agentId: 'context',
      agentName: 'Context extractor',
      agentRole: 'transcript_analyst',
      status: 'complete',
      timestamp: at(1),
      durationMs: 2840,
      output: {
        type: 'solving_context',
        preview: 'Extracted a four-step build flow, core entities, test hooks, and a launch checklist.',
      },
    },
  ];

  if (screen === 'context') {
    return contextTrace;
  }

  if (screen === 'validation') {
    return [
      ...contextTrace,
      {
        id: 'trace-3',
        agentId: 'scaffold',
        agentName: 'Scaffold generator',
        agentRole: 'action_generator',
        status: 'error',
        timestamp: at(4),
        durationMs: 910,
        output: {
          type: 'build_plan',
          preview: 'Generated plan missing required field "verification_steps".',
        },
        error: 'Schema validation failed. Required keys: solving_context, scaffold_targets, verification_steps.',
      },
    ];
  }

  const orchestrationTrace: TraceStep[] = [
    ...contextTrace,
    {
      id: 'trace-3',
      agentId: 'scaffold',
      agentName: 'Scaffold generator',
      agentRole: 'action_generator',
      status: 'complete',
      timestamp: at(4),
      durationMs: 1310,
      output: {
        type: 'build_plan',
        preview: 'Structured plan regenerated with routing, tests, and preview output definitions.',
      },
    },
    {
      id: 'trace-4',
      agentId: 'verify',
      agentName: 'Verification loop',
      agentRole: 'quality_checker',
      status: screen === 'launch' ? 'complete' : 'running',
      timestamp: at(6),
      durationMs: screen === 'launch' ? 2270 : undefined,
      output: {
        type: 'checks',
        preview: screen === 'launch' ? 'Schema + smoke checks passed. Ready to package preview build.' : 'Running smoke test against generated route map and starter components...',
      },
    },
  ];

  if (screen === 'orchestration') {
    return orchestrationTrace;
  }

  return [
    ...orchestrationTrace,
    {
      id: 'trace-5',
      agentId: 'launch',
      agentName: 'Launch router',
      agentRole: 'router',
      status: 'complete',
      timestamp: at(9),
      durationMs: 640,
      output: {
        type: 'preview_bundle',
        preview: 'Preview package created with deploy note, route map, and handoff URL.',
      },
    },
  ];
}

function getFocusAgent(screen: ScreenId): string {
  if (screen === 'fallback') return 'context';
  if (screen === 'validation') return 'scaffold';
  if (screen === 'launch') return 'launch';
  if (screen === 'orchestration') return 'verify';
  return screen === 'context' ? 'context' : 'intake';
}

function getActionLabel(screen: ScreenId): string {
  if (screen === 'fallback') return 'Use STT fallback';
  if (screen === 'validation') return 'Regenerate structured plan';
  if (screen === 'launch') return 'Restart prototype';
  if (screen === 'intake') return 'Extract solving context';
  if (screen === 'context') return 'Generate scaffold';
  return 'Review launch package';
}

/**
 * Returns the descriptive panel content for the current screen.
 *
 * @param screen - The current prototype screen
 * @returns The title, summary, badge, and left/right content for the screen
 */
function getScreenContent(screen: ScreenId) {
  switch (screen) {
    case 'intake':
      return {
        title: 'Lock the job before any generation starts',
        summary: 'The first screen translates the note into a concrete intake flow: URL in, build target defined, and a visible agent trace from the start.',
        badge: { label: 'Flow step 1', variant: 'primary' as const },
        left: (
          <div className="space-y-4">
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/35">Target output</p>
              <p className="mt-2 text-sm text-white/75">
                Turn the tutorial into a launchable starter app with route map, scaffolded UI, and deployment handoff.
              </p>
            </div>
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/35">Why this exists</p>
              <ul className="mt-3 space-y-2 text-sm text-white/70">
                {NOTE_SIGNALS.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="text-primary-400">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ),
        right: (
          <div className="rounded-2xl border border-primary-500/20 bg-primary-500/10 p-5">
            <div className="flex items-center gap-2 text-primary-300">
              <Video className="h-4 w-4" />
              <p className="text-sm font-semibold">Primary happy-path question</p>
            </div>
            <p className="mt-3 text-sm leading-7 text-white/75">
              Can a user paste a single tutorial link and immediately see a trustworthy build brief instead of a blank loading state?
            </p>
          </div>
        ),
      };
    case 'fallback':
      return {
        title: 'Recover when source transcript data is missing',
        summary: 'The note emphasizes error capture and fallback. This edge state makes the recovery step explicit instead of burying it in logs.',
        badge: { label: 'Edge state', variant: 'warning' as const },
        left: (
          <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/10 p-5">
            <div className="flex items-center gap-2 text-yellow-300">
              <AlertCircle className="h-4 w-4" />
              <p className="text-sm font-semibold">Native captions were unavailable</p>
            </div>
            <p className="mt-3 text-sm leading-7 text-white/75">
              Instead of blocking the run, the user gets one direct choice: continue with speech-to-text and preserve the same downstream flow.
            </p>
          </div>
        ),
        right: (
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/35">Resolution criteria</p>
            <ul className="mt-3 space-y-2 text-sm text-white/70">
              <li className="flex gap-2"><span className="text-yellow-300">•</span><span>The user understands why the fallback is needed.</span></li>
              <li className="flex gap-2"><span className="text-yellow-300">•</span><span>Choosing fallback preserves the same artifact structure and trace.</span></li>
            </ul>
          </div>
        ),
      };
    case 'context':
      return {
        title: 'Review the solving context before code generation',
        summary: 'This screen translates the note’s core requirement into a product checkpoint: extracted concepts, pseudocode, and build targets are visible before agents act.',
        badge: { label: 'Flow step 2', variant: 'primary' as const },
        left: (
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/35">Key concepts</p>
              <ul className="mt-3 space-y-2 text-sm text-white/70">
                <li className="flex gap-2"><span className="text-accent-400">•</span><span>Transcript-to-context distillation</span></li>
                <li className="flex gap-2"><span className="text-accent-400">•</span><span>Strict build plan schema</span></li>
                <li className="flex gap-2"><span className="text-accent-400">•</span><span>Agent trace and verification loop</span></li>
              </ul>
            </div>
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/35">Pseudocode</p>
              <pre className="mt-3 overflow-x-auto text-xs leading-6 text-white/70">
{`brief = analyze(video_url)
context = distill(transcript)
plan = generate_build_plan(context)
verify(plan)
package_preview(plan)`}
              </pre>
            </div>
          </div>
        ),
        right: (
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4">
            <div className="flex items-center gap-2 text-emerald-300">
              <CheckCircle2 className="h-4 w-4" />
              <p className="text-sm font-semibold">Context extraction accepted</p>
            </div>
            <p className="mt-3 text-sm leading-7 text-white/75">
              The extracted brief is precise enough to generate a starter app without replaying the full video or guessing the output shape.
            </p>
          </div>
        ),
      };
    case 'validation':
      return {
        title: 'Repair the generated plan before orchestration continues',
        summary: 'The note calls out schema validation and error capture as a requirement. This edge state exposes the bad payload and the single recovery action.',
        badge: { label: 'Edge state', variant: 'error' as const },
        left: (
          <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-5">
            <div className="flex items-center gap-2 text-red-300">
              <FileWarning className="h-4 w-4" />
              <p className="text-sm font-semibold">Schema validation failed</p>
            </div>
            <ul className="mt-4 space-y-2 text-sm text-white/75">
              <li className="flex gap-2"><span className="text-red-300">•</span><span>Missing required field: <code className="font-mono text-red-200">verification_steps</code></span></li>
              <li className="flex gap-2"><span className="text-red-300">•</span><span>Preview route was generated without a smoke-test target.</span></li>
            </ul>
          </div>
        ),
        right: (
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/35">Recovery rule</p>
            <p className="mt-3 text-sm leading-7 text-white/70">
              The user never edits JSON directly in this first prototype. One action regenerates a valid plan and keeps the flow moving.
            </p>
          </div>
        ),
      };
    case 'orchestration':
      return {
        title: 'Run scaffold + verification as one guided agent phase',
        summary: 'This is the core prototype moment: generation, smoke tests, and packaging are visible as one connected run instead of separate tools.',
        badge: { label: 'Flow step 3', variant: 'primary' as const },
        left: (
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/35">Generated scaffold</p>
              <pre className="mt-3 overflow-x-auto text-xs leading-6 text-white/70">
{`app/
  page.tsx
  prototype/page.tsx
components/
  ContextReview.tsx
  ExecutionTrace.tsx`}
              </pre>
            </div>
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/35">Running checks</p>
              <ul className="mt-3 space-y-2 text-sm text-white/70">
                <li className="flex gap-2"><span className="text-emerald-300">•</span><span>Schema contract</span></li>
                <li className="flex gap-2"><span className="text-emerald-300">•</span><span>Route smoke test</span></li>
                <li className="flex gap-2"><span className="text-emerald-300">•</span><span>Preview packaging</span></li>
              </ul>
            </div>
          </div>
        ),
        right: (
          <div className="rounded-2xl border border-primary-500/20 bg-primary-500/10 p-4">
            <div className="flex items-center gap-2 text-primary-300">
              <Workflow className="h-4 w-4" />
              <p className="text-sm font-semibold">Why this matters</p>
            </div>
            <p className="mt-3 text-sm leading-7 text-white/75">
              The product promise is not just analysis. It is analysis that flows directly into a tested, packageable output.
            </p>
          </div>
        ),
      };
    case 'launch':
      return {
        title: 'Hand off a launch-ready preview, not just analysis',
        summary: 'The final state reflects the note’s outcome: a packaged starter app, deployment target, and enough trace data to trust what happened.',
        badge: { label: 'Flow step 4', variant: 'success' as const },
        left: (
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-200/80">Preview output</p>
              <p className="mt-3 text-sm text-white/75">Preview URL: <span className="font-mono text-emerald-200">https://preview.eventrelay.app/build/vid-2041</span></p>
              <p className="mt-2 text-sm text-white/75">Package contains route map, generated UI shell, trace export, and deployment notes.</p>
            </div>
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/35">Launch checks</p>
              <ul className="mt-3 space-y-2 text-sm text-white/70">
                <li className="flex gap-2"><span className="text-emerald-300">•</span><span>Starter app generated</span></li>
                <li className="flex gap-2"><span className="text-emerald-300">•</span><span>Verification completed</span></li>
                <li className="flex gap-2"><span className="text-emerald-300">•</span><span>Preview handoff ready</span></li>
              </ul>
            </div>
          </div>
        ),
        right: (
          <div className="rounded-2xl border border-accent-500/20 bg-cyan-500/10 p-4">
            <div className="flex items-center gap-2 text-cyan-300">
              <ExternalLink className="h-4 w-4" />
              <p className="text-sm font-semibold">Prototype output promise</p>
            </div>
            <p className="mt-3 text-sm leading-7 text-white/75">
              Users leave this flow with something runnable, inspectable, and easy to hand off for implementation.
            </p>
          </div>
        ),
      };
  }
}

/**
 * Renders the interactive video-to-software prototype page.
 */
export default function PrototypePage() {
  const [scenario, setScenario] = useState<ScenarioId>('happy');
  const [stepIndex, setStepIndex] = useState(0);
  const [videoUrl, setVideoUrl] = useState(DEFAULT_VIDEO_URL);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(getFocusAgent('intake'));

  const sequence = SCENARIOS[scenario].sequence;
  const currentScreen = sequence[stepIndex];

  const agents = useMemo(() => buildAgents(currentScreen), [currentScreen]);
  const connections = useMemo(() => buildConnections(currentScreen), [currentScreen]);
  const trace = useMemo(() => buildTrace(currentScreen, videoUrl), [currentScreen, videoUrl]);
  const screenContent = useMemo(() => getScreenContent(currentScreen), [currentScreen]);

  useEffect(() => {
    setSelectedAgentId(getFocusAgent(currentScreen));
  }, [currentScreen]);

  const isLastStep = stepIndex === sequence.length - 1;

  const handleScenarioChange = (nextScenario: ScenarioId) => {
    setScenario(nextScenario);
    setStepIndex(0);
  };

  const handlePrimaryAction = () => {
    if (isLastStep) {
      setStepIndex(0);
      return;
    }

    setStepIndex((current) => Math.min(current + 1, sequence.length - 1));
  };

  return (
    <div className="min-h-screen text-white">
      <nav className="border-b border-white/[0.05] bg-surface-950/80 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 font-black shadow-lg shadow-primary-500/20">
                U
              </div>
              <div>
                <p className="text-sm font-semibold tracking-tight">UVAI</p>
                <p className="text-xs text-white/40">Interactive prototype</p>
              </div>
            </Link>
            <div className="hidden h-8 w-px bg-white/[0.08] md:block" />
            <Link href="/dashboard" className="hidden text-sm text-white/45 transition hover:text-white/80 md:block">
              Dashboard
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <Badge variant="primary" size="lg">
              Interactive prototype
            </Badge>
          </div>
        </div>
      </nav>

      <main className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-6 py-8 lg:px-8">
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 px-5 py-4 text-sm text-amber-100/90">
          <p>
            <span className="font-semibold text-amber-50">Design preview only.</span>
            {' '}
            This page runs scripted happy-path, fallback, and schema scenarios — it does not call production
            {' '}
            <code className="rounded bg-black/20 px-1 py-0.5 text-xs">/api/pipeline</code>
            {' '}
            or
            {' '}
            <code className="rounded bg-black/20 px-1 py-0.5 text-xs">/api/pipeline/stream</code>.
            {' '}
            For live analysis use{' '}
            <Link href="/dashboard" className="font-semibold text-amber-50 underline underline-offset-2">
              Dashboard
            </Link>
            ; for local planning drafts use{' '}
            <Link href="/" className="font-semibold text-amber-50 underline underline-offset-2">
              Studio
            </Link>
            .
          </p>
        </div>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <Card variant="gradient" padding="lg">
            <CardHeader
              title="Video-to-software prototype"
              subtitle="The smallest end-to-end clickable flow: URL in, structured context out, agent pipeline runs, launch package ready."
            />
            <CardContent className="space-y-6">
              <div className="flex flex-wrap items-center gap-3">
                <Badge variant={screenContent.badge.variant} size="lg" icon={<Sparkles className="h-3.5 w-3.5" />}>
                  {screenContent.badge.label}
                </Badge>
                <Badge variant="default" size="lg">
                  Current screen: {SCREEN_LABELS[currentScreen]}
                </Badge>
              </div>

              <div>
                <h1 className="max-w-3xl text-3xl font-black tracking-tight md:text-4xl">
                  {screenContent.title}
                </h1>
                <p className="mt-3 max-w-3xl text-base leading-8 text-white/60">
                  {screenContent.summary}
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-[1.2fr_0.8fr]">
                <Input
                  label="Prototype source URL"
                  value={videoUrl}
                  onChange={(event) => setVideoUrl(event.target.value)}
                  helperText="Assumption: this first prototype starts from a single tutorial or walkthrough URL."
                  leftIcon={<Video className="h-4 w-4" />}
                />
                <div className="flex flex-col justify-end gap-3 sm:flex-row md:flex-col">
                  <Button
                    variant="primary"
                    size="lg"
                    onClick={handlePrimaryAction}
                    leftIcon={isLastStep ? <RefreshCcw className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                    rightIcon={!isLastStep ? <ArrowRight className="h-4 w-4" /> : undefined}
                    fullWidth
                  >
                    {getActionLabel(currentScreen)}
                  </Button>
                  <Button
                    variant="ghost"
                    size="lg"
                    onClick={() => setStepIndex((current) => Math.max(current - 1, 0))}
                    disabled={stepIndex === 0}
                    fullWidth
                  >
                    Previous step
                  </Button>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                {Object.entries(SCENARIOS).map(([key, item]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => handleScenarioChange(key as ScenarioId)}
                    className={clsx(
                      'rounded-2xl border px-4 py-3 text-left transition-all duration-200',
                      scenario === key
                        ? 'border-primary-500/40 bg-primary-500/10 shadow-lg shadow-primary-500/10'
                        : 'border-white/[0.08] bg-white/[0.03] hover:border-white/[0.16] hover:bg-white/[0.05]',
                    )}
                  >
                    <p className="text-sm font-semibold">{item.label}</p>
                    <p className="mt-1 max-w-xs text-xs leading-6 text-white/45">{item.description}</p>
                  </button>
                ))}
              </div>

              <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                {screenContent.left}
                {screenContent.right}
              </div>
            </CardContent>
          </Card>

          <Card variant="glass" padding="lg">
            <CardHeader title="Assumptions and extracted criteria" subtitle="Ambiguity from the notes is resolved with the simplest viable product shape." />
            <CardContent className="space-y-6">
              <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-white/80">
                  <ShieldCheck className="h-4 w-4 text-emerald-300" />
                  Acceptance criteria
                </div>
                <ul className="mt-4 space-y-3 text-sm leading-7 text-white/65">
                  {ACCEPTANCE_CRITERIA.map((criterion) => (
                    <li key={criterion} className="flex gap-3">
                      <CheckCircle2 className="mt-1 h-4 w-4 flex-none text-emerald-300" />
                      <span>{criterion}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-white/80">
                  <Code2 className="h-4 w-4 text-primary-300" />
                  Core user flow
                </div>
                <ul className="mt-4 space-y-3 text-sm leading-7 text-white/65">
                  {FLOW_SUMMARY.map((item) => (
                    <li key={item} className="flex gap-3">
                      <span className="mt-1 h-2 w-2 flex-none rounded-full bg-primary-400" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/10 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-yellow-200">
                  <AlertCircle className="h-4 w-4" />
                  Assumption
                </div>
                <p className="mt-3 text-sm leading-7 text-white/70">{SCENARIOS[scenario].assumption}</p>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <Card variant="glass" padding="lg">
            <CardHeader
              title="Pipeline view"
              subtitle="A clickable simulation of the orchestrated multi-agent flow."
            />
            <CardContent className="space-y-6">
              <div className="flex flex-wrap gap-2">
                {sequence.map((screen, index) => (
                  <button
                    key={`${screen}-${index}`}
                    type="button"
                    onClick={() => setStepIndex(index)}
                    className={clsx(
                      'rounded-full border px-4 py-2 text-sm transition-all duration-200',
                      stepIndex === index
                        ? 'border-primary-500/40 bg-primary-500/15 text-primary-200'
                        : 'border-white/[0.08] bg-white/[0.03] text-white/50 hover:border-white/[0.16] hover:text-white/80',
                    )}
                  >
                    {index + 1}. {SCREEN_LABELS[screen]}
                  </button>
                ))}
              </div>

              <div className="rounded-[28px] border border-white/[0.08] bg-surface-950/70 p-4">
                <AgentFlowVisualizer
                  agents={agents}
                  connections={connections}
                  positions={NODE_POSITIONS}
                  selectedAgentId={selectedAgentId}
                  onSelectAgent={setSelectedAgentId}
                  className="min-h-[440px]"
                />
              </div>
            </CardContent>
          </Card>

          <Card variant="glass" padding="none" className="overflow-hidden">
            <TracePanel
              steps={trace}
              selectedAgentId={selectedAgentId}
              onSelectAgent={setSelectedAgentId}
              className="h-[620px]"
            />
          </Card>
        </section>
      </main>
    </div>
  );
}
