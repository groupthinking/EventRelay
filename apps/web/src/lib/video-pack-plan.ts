import type { VideoPackV0Json } from '@/lib/video-pack';

export type VideoPlanInterviewAnswers = {
  useCase: string;
  trigger: string;
  tools: string[];
  constraints: string;
  successSignal: string;
};

type Evidence = { source: string; text: string };

const PLAN_RE = /\bsparkle\s*pills?\b|\b(?:build|plan|implement|design|create)\b.{0,80}\b(?:video|pack)\b|\b(?:video|pack)\b.{0,80}\b(?:build|plan|implement|architecture)\b/i;

const ARCHITECTURE_AREAS = [
  ['Frontend', /\b(?:front[ -]?end|ui|interface|react|browser)\b/i],
  ['Backend', /\b(?:back[ -]?end|server|api|endpoint)\b/i],
  ['Middleware', /\b(?:middleware|auth(?:entication|orization)?|rate limit)\b/i],
  ['Database', /\b(?:database|postgres|sql|redis|storage)\b/i],
  ['LSP', /\b(?:lsp|language server)\b/i],
  ['MCP', /\b(?:mcp|model context protocol)\b/i],
  ['Tools', /\b(?:tool|cli|sdk|integration)\b/i],
  ['Environment', /\b(?:environment|env var|secret|runtime|deployment)\b/i],
] as const;

function compact(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function compactList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => (typeof entry === 'string' ? entry.trim() : ''))
    .filter((entry) => entry.length > 0);
}

function parseAnswers(value: unknown): VideoPlanInterviewAnswers | null {
  if (!value || typeof value !== 'object') return null;
  const source = value as Record<string, unknown>;
  const useCase = compact(source.useCase);
  const trigger = compact(source.trigger);
  const tools = compactList(source.tools);
  const constraints = compact(source.constraints);
  const successSignal = compact(source.successSignal);
  if (!useCase || !trigger || tools.length === 0 || !constraints || !successSignal) return null;
  return { useCase, trigger, tools, constraints, successSignal };
}

export function isVideoPackPlanRequest(query: string): boolean {
  return PLAN_RE.test(query);
}

export function videoPlanInterviewQuestions(): string[] {
  return [
    'What exact deliverable should the agent build from this video?',
    'What event, schedule, or manual action should start the workflow?',
    'Which tools or systems are available in the target codebase?',
    'What constraints must the implementation respect?',
    'What observable test or result will prove the deliverable works?',
  ];
}

function excerpt(value: string, pattern?: RegExp): string {
  const normalized = value.replace(/\s+/g, ' ').trim();
  if (normalized.length <= 240) return normalized;
  const matchAt = pattern?.exec(normalized)?.index ?? 0;
  const start = Math.max(0, matchAt - 80);
  const slice = normalized.slice(start, start + 240);
  return `${start > 0 ? '…' : ''}${slice}${start + 240 < normalized.length ? '…' : ''}`;
}

function packEvidence(pack: VideoPackV0Json): Evidence[] {
  return [
    ...pack.requirements.map((item) => ({
      source: `requirement ${item.id}`,
      text: [item.title, item.detail].filter(Boolean).join(' — '),
    })),
    ...pack.action_items.map((item) => ({
      source: `action ${item.id}`,
      text: [item.title, item.description].filter(Boolean).join(' — '),
    })),
    ...(pack.transcript.segments.length > 0
      ? pack.transcript.segments.map((item) => ({
      source: `transcript ${item.start_s}s`,
      text: item.text,
      }))
      : [{ source: 'transcript', text: pack.transcript.full_text }]),
    ...(pack.visual_context?.visual_elements ?? []).map((item) => ({
      source: `visual ${item.timestamp}s`,
      text: item.content,
    })),
    ...pack.stack.tools.map((item) => ({
      source: `pack tool ${item.name}`,
      text: [item.name, item.evidence].filter(Boolean).join(' — '),
    })),
  ].filter((item) => item.text.trim().length > 0);
}

function buildPlan(pack: VideoPackV0Json, interview: VideoPlanInterviewAnswers): string {
  const evidence = packEvidence(pack);
  const architecture = ARCHITECTURE_AREAS.map(([area, pattern]) => {
    const matches = evidence.filter((item) =>
      (area === 'Tools' && item.source.startsWith('pack tool ')) || pattern.test(item.text),
    );
    const displayed = area === 'Tools' ? matches : matches.slice(0, 3);
    return matches.length > 0
      ? `- ${area}: ${displayed.map((item) => `[${item.source}] ${excerpt(item.text, pattern)}`).join(' | ')}${matches.length > displayed.length ? ` | ${matches.length - displayed.length} more cited cues in the pack` : ''}`
      : `- ${area}: No explicit evidence in this pack; inspect the target repository before selecting an implementation.`;
  });
  const sourceExamples = evidence.slice(0, 8).map((item) =>
    `- [${item.source}] ${excerpt(item.text)}`,
  );

  return [
    'Video Pack Build Plan',
    `Source: ${pack.id} (${pack.source_url}); source hash: ${pack.provenance.source_hash}`,
    'Pack-extracted cues below are planning inputs, not verified implementation or deployment receipts.',
    '',
    'Interview (user supplied)',
    `- Deliverable: ${interview.useCase}`,
    `- Trigger: ${interview.trigger}`,
    `- Available tools: ${interview.tools.join(', ')}`,
    `- Constraints: ${interview.constraints}`,
    `- Acceptance signal: ${interview.successSignal}`,
    '',
    'Video Pack evidence to verify',
    ...(sourceExamples.length ? sourceExamples : ['- No source excerpts are available in this pack.']),
    '',
    'Architecture evidence by area',
    ...architecture,
    '',
    'Build sequence',
    '1. Verify the cited pack excerpts against the source video and inspect the target repository, build scripts, tests, and environment.',
    '2. Map only supported video requirements to frontend, backend, middleware, database, LSP, MCP, tools, and environment decisions; record unknowns before coding.',
    '3. Implement one end-to-end slice in the target repository, then run its build and relevant tests.',
    `4. Check the result against the user acceptance signal: ${interview.successSignal}`,
    'No codebase change, test result, or live deployment is claimed by this plan.',
  ].join('\n');
}

export function resolveVideoPackPlanResponse(input: {
  query: string;
  planIntent?: unknown;
  planInterview?: unknown;
  pack: VideoPackV0Json;
}):
  | { answer: string; requiresInterview: true; interviewQuestions: string[] }
  | { answer: string; requiresInterview: false; provider: 'video-pack-planner'; interview: VideoPlanInterviewAnswers }
  | null {
  if (!isVideoPackPlanRequest(input.query) && input.planIntent !== true) return null;
  const interview = parseAnswers(input.planInterview);
  if (!interview) {
    return {
      answer: 'Before I plan from this Video Pack, I need a short use-case interview so the build targets your actual codebase and acceptance test.',
      requiresInterview: true,
      interviewQuestions: videoPlanInterviewQuestions(),
    };
  }
  return {
    answer: buildPlan(input.pack, interview),
    requiresInterview: false,
    provider: 'video-pack-planner',
    interview,
  };
}
