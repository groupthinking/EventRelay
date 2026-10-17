/**
 * Runbook compiler.
 *
 * Turns a Video Pack (plus the optional linked SOP) into a 1-of-N runbook whose
 * steps are anchored to the video timeline using ONLY evidence already on the
 * pack: extractor-reported ranges, validated grounded-spec citations,
 * transcript segments that quote the named tool evidence or share distinctive
 * vocabulary with the step, chapter topics, and visual events. A step the pack
 * cannot anchor keeps `timestamp_range: null` and says so — nothing is invented
 * (Zero-Sim). No React, no I/O.
 */

import { formatSeconds } from '@/lib/timestamp';
import {
  deriveSopTimestampFromPackFields,
  visualEventsFromPack,
  type AppBuilderChapter,
  type AppBuilderVisualEvent,
} from '@/lib/emit-app-builder-sandbox';
import type { LinkedSop } from '@/lib/linked-sop';
import type { GroundedSpecRecord } from '@/lib/grounded-build-spec';
import type {
  VideoPackCodeSnippet,
  VideoPackKeyframe,
  VideoPackRequirement,
  VideoPackTranscriptSegment,
  VideoPackVisualContext,
} from '@/lib/video-pack';
import type {
  VideoPackActionItem,
  VideoPackArchitecture,
  VideoPackArtifact,
  VideoPackChapter,
  VideoPackStack,
} from '@/lib/video-pack-types';

export const RUNBOOK_VERSION = 'runbook-v1' as const;
export const RUNBOOK_MARKDOWN_FILENAME = 'RUNBOOK.md' as const;

export type RunbookStepKind =
  | 'terminal_command'
  | 'code_snippet'
  | 'architecture_decision'
  | 'verification_check'
  | 'action';

export type RunbookAnchor =
  | 'extracted'
  | 'event'
  | 'grounded_spec'
  | 'transcript'
  | 'chapter'
  | 'visual'
  | 'none';

export type RunbookVerificationSource = 'grounded_spec' | 'stack_check' | 'none';
export type RunbookPrerequisiteKind = 'tool' | 'stack_check' | 'access' | 'runtime';

export interface RunbookPrerequisite {
  id: string;
  kind: RunbookPrerequisiteKind;
  title: string;
  detail: string | null;
  href: string | null;
  evidence: string | null;
}

export interface RunbookKeyframe {
  t_s: number;
  image_path: string | null;
  desc: string | null;
}

export interface RunbookSnippet {
  path_hint: string | null;
  lang: string | null;
  content: string;
}

export interface RunbookStep {
  id: string;
  step_number: number;
  title: string;
  kind: RunbookStepKind;
  /** Seconds on the video timeline; null when no pack evidence anchors the step. */
  timestamp_range: [number, number] | null;
  anchor: RunbookAnchor;
  content_markdown: string;
  verification: string;
  verification_source: RunbookVerificationSource;
  detail: string;
  inputs: string[];
  outputs: string[];
  tags: string[];
  priority: string | null;
  difficulty: string | null;
  command: string | null;
  snippet: RunbookSnippet | null;
  architecture_stage: string | null;
  evidence: { quote?: string; keyframe: RunbookKeyframe | null };
  source: { kind: 'requirement' | 'action_item' | 'sop_step'; id: string };
}

export interface Runbook {
  version: typeof RUNBOOK_VERSION;
  videoId: string;
  packId: string;
  sourceUrl: string;
  sourceHash: string;
  durationSeconds: number | null;
  prerequisites: RunbookPrerequisite[];
  steps: RunbookStep[];
  coverage: { anchored: number; total: number };
}

export interface RunbookProgress {
  version: 1;
  checkedPrerequisites: string[];
  completedSteps: string[];
  updatedAt?: string;
}

/** Structural pack input satisfied by both the stored v0 pack and the client citation pack. */
export interface RunbookPackInput {
  id: string;
  video_id: string;
  source_url: string;
  provenance: { source_hash: string };
  transcript?: {
    language?: string | null;
    full_text: string;
    segments?: VideoPackTranscriptSegment[];
  } | null;
  chapters?: VideoPackChapter[] | null;
  requirements?: VideoPackRequirement[] | null;
  action_items?: VideoPackActionItem[] | null;
  code_snippets?: VideoPackCodeSnippet[] | null;
  stack?: VideoPackStack | null;
  architecture?: VideoPackArchitecture | null;
  artifacts?: VideoPackArtifact[] | null;
  keyframes?: VideoPackKeyframe[] | null;
  visual_context?: VideoPackVisualContext | null;
  grounded_spec?: GroundedSpecRecord;
}

export interface CompileRunbookInput {
  pack: RunbookPackInput;
  /** Studio-compiled SOP; used for steps only when the pack has no requirements/action_items. */
  linkedSop?: LinkedSop | null;
}

// ── Tokenization ────────────────────────────────────────────────────────────

const STOPWORDS = new Set([
  'about', 'above', 'actually', 'after', 'again', 'against', 'also', 'another', 'anything', 'around',
  'back', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'came', 'come', 'could',
  'does', 'doing', 'done', 'down', 'during', 'each', 'even', 'ever', 'every', 'everything', 'from',
  'further', 'genuinely', 'getting', 'going', 'gonna', 'have', 'having', 'here', 'into', 'just',
  'keep', 'know', 'like', 'literally', 'made', 'make', 'many', 'more', 'most', 'much', 'need',
  'never', 'nothing', 'okay', 'once', 'only', 'onto', 'other', 'over', 'people', 'person', 'really',
  'right', 'same', 'should', 'since', 'some', 'something', 'still', 'such', 'take', 'than', 'that',
  'their', 'them', 'then', 'there', 'these', 'they', 'thing', 'things', 'think', 'this', 'those',
  'through', 'under', 'until', 'upon', 'used', 'using', 'very', 'want', 'well', 'were', 'what',
  'when', 'where', 'which', 'while', 'will', 'with', 'within', 'without', 'would', 'yeah', 'your',
  'yours', 'yourself',
]);

function normalizeProse(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function proseTokens(text: string): string[] {
  const seen = new Set<string>();
  for (const token of normalizeProse(text).split(/\s+/)) {
    if (token.length <= 3 || STOPWORDS.has(token) || /^\d+$/.test(token)) continue;
    seen.add(token);
  }
  return [...seen];
}

/** Identifiers in code are camelCase; split them so `fundingUsd` meets prose `funding`. */
function codeTokens(snippet: RunbookSnippet): string[] {
  const split = `${snippet.path_hint ?? ''} ${snippet.content}`.replace(/([a-z0-9])([A-Z])/g, '$1 $2');
  return proseTokens(split);
}

function sharedTokens(a: Iterable<string>, b: Set<string>): string[] {
  const out: string[] = [];
  for (const token of a) if (b.has(token)) out.push(token);
  return out;
}

function slug(value: string): string {
  return normalizeProse(value).replace(/\s+/g, '-') || 'item';
}

// ── Transcript index ────────────────────────────────────────────────────────

interface SegmentRow {
  position: number;
  start: number;
  end: number;
  text: string;
  tokens: Set<string>;
}

interface SegmentIndex {
  rows: SegmentRow[];
  df: Map<string, number>;
  distinctiveMax: number;
}

function buildSegmentIndex(segments: VideoPackTranscriptSegment[] | undefined): SegmentIndex {
  const rows: SegmentRow[] = [];
  for (const segment of segments ?? []) {
    const text = (segment.text ?? '').trim();
    if (!text || !Number.isFinite(segment.start_s) || !Number.isFinite(segment.end_s)) continue;
    rows.push({
      position: rows.length,
      start: Math.max(0, segment.start_s),
      end: Math.max(segment.start_s, segment.end_s),
      text,
      tokens: new Set(proseTokens(text)),
    });
  }
  const df = new Map<string, number>();
  for (const row of rows) {
    for (const token of row.tokens) df.set(token, (df.get(token) ?? 0) + 1);
  }
  return { rows, df, distinctiveMax: Math.max(2, Math.ceil(rows.length * 0.05)) };
}

const MAX_EXTEND_PER_SIDE = 2;
const MAX_RANGE_SECONDS = 60;
const KEYFRAME_NEAR_SECONDS = 10;

interface SegmentMatch {
  position: number;
  score: number;
  candidate: boolean;
}

function scoreSegments(
  index: SegmentIndex,
  stepTokens: Set<string>,
  titleTokens: Set<string>,
  bonuses: Map<number, number>,
): SegmentMatch[] {
  return index.rows.map((row) => {
    const shared = sharedTokens(row.tokens, stepTokens);
    const distinct = shared.filter((token) => (index.df.get(token) ?? 0) <= index.distinctiveMax);
    let score = 0;
    for (const token of shared) {
      score += (titleTokens.has(token) ? 2 : 1) * (distinct.includes(token) ? 2 : 1);
    }
    const bonus = bonuses.get(row.position) ?? 0;
    const candidate =
      bonus >= 3 || shared.length >= 3 || (shared.length >= 2 && distinct.length >= 1);
    return { position: row.position, score: score + bonus, candidate };
  });
}

function extendRange(index: SegmentIndex, matches: SegmentMatch[], core: number): [number, number] {
  const rows = index.rows;
  let first = core;
  let last = core;
  const within = () => rows[last].end - rows[first].start <= MAX_RANGE_SECONDS;
  for (let step = 1; step <= MAX_EXTEND_PER_SIDE; step += 1) {
    const next = core + step;
    if (!rows[next] || !matches[next].candidate) break;
    last = next;
    if (!within()) {
      last = next - 1;
      break;
    }
  }
  for (let step = 1; step <= MAX_EXTEND_PER_SIDE; step += 1) {
    const prev = core - step;
    if (!rows[prev] || !matches[prev].candidate) break;
    first = prev;
    if (!within()) {
      first = prev + 1;
      break;
    }
  }
  return [rows[first].start, rows[last].end];
}

function containingSegment(index: SegmentIndex, seconds: number): SegmentRow | null {
  return index.rows.find((row) => row.start <= seconds && seconds <= row.end) ?? null;
}

// ── Pack evidence helpers ───────────────────────────────────────────────────

interface ToolEvidence {
  name: string;
  nameTokens: string[];
  quotes: string[];
  check: string | null;
  kind: string | null;
  evidence: string | null;
}

function toolEvidence(stack: VideoPackStack | null | undefined): ToolEvidence[] {
  return (stack?.tools ?? []).flatMap((tool) => {
    const name = tool.name.trim();
    if (!name) return [];
    const quotes: string[] = [];
    for (const match of (tool.evidence ?? '').matchAll(/['"“‘]([^'"”’]{12,})['"”’]/g)) {
      quotes.push(match[1].trim());
    }
    return [
      {
        name,
        nameTokens: proseTokens(name),
        quotes,
        check: tool.check?.trim() || null,
        kind: tool.kind?.trim() || null,
        evidence: tool.evidence?.trim() || null,
      },
    ];
  });
}

function toolNamedIn(normalizedText: string, tool: ToolEvidence): boolean {
  if (tool.nameTokens.length > 0) {
    return tool.nameTokens.every((token) => new RegExp(`(^|\\s)${token}(\\s|$)`).test(normalizedText));
  }
  const whole = normalizeProse(tool.name);
  return whole.length > 0 && new RegExp(`(^|\\s)${whole}(\\s|$)`).test(normalizedText);
}

interface GroundedCitation {
  requirementId: string;
  requirementTitle: string;
  quote: string;
}

interface GroundedIndex {
  byPosition: Map<number, GroundedCitation[]>;
  acceptance: Array<{ requirementId: string; given: string; when: string; then: string }>;
}

function groundedIndex(spec: GroundedSpecRecord | undefined, index: SegmentIndex): GroundedIndex {
  const byPosition = new Map<number, GroundedCitation[]>();
  if (!spec || spec.status !== 'available') return { byPosition, acceptance: [] };
  for (const requirement of spec.spec.requirements) {
    for (const ref of requirement.citations) {
      if (ref.kind !== 'transcript') continue;
      const row = index.rows.find(
        (candidate) => candidate.start === ref.startSeconds && candidate.end === ref.endSeconds,
      );
      if (!row) continue;
      const list = byPosition.get(row.position) ?? [];
      list.push({ requirementId: requirement.id, requirementTitle: requirement.title, quote: ref.quote });
      byPosition.set(row.position, list);
    }
  }
  return { byPosition, acceptance: spec.spec.acceptanceCriteria };
}

function titlesAlign(left: string, right: string): boolean {
  const a = normalizeProse(left);
  const b = normalizeProse(right);
  if (!a || !b) return false;
  return a === b || (a.length >= 8 && b.includes(a)) || (b.length >= 8 && a.includes(b));
}

function pickKeyframe(
  keyframes: VideoPackKeyframe[] | null | undefined,
  range: [number, number] | null,
): RunbookKeyframe | null {
  if (!range || !keyframes?.length) return null;
  const rows = keyframes
    .filter((frame) => Number.isFinite(frame.t_s))
    .map((frame) => ({ t_s: frame.t_s, image_path: frame.image_path ?? null, desc: frame.desc ?? null }));
  const inside = rows
    .filter((frame) => frame.t_s >= range[0] && frame.t_s <= range[1])
    .sort((a, b) => a.t_s - b.t_s);
  if (inside[0]) return inside[0];
  let nearest: RunbookKeyframe | null = null;
  for (const frame of rows) {
    const distance = Math.abs(frame.t_s - range[0]);
    if (distance > KEYFRAME_NEAR_SECONDS) continue;
    if (!nearest || distance < Math.abs(nearest.t_s - range[0])) nearest = frame;
  }
  return nearest;
}

// ── Step classification ─────────────────────────────────────────────────────

const COMMAND_BINARIES =
  'npm|npx|pnpm|yarn|bun|pip3?|python3?|node|git|curl|wget|docker|brew|apt-get|vercel|gcloud|aws|shopify|cargo|uvx?|deno|gh|kubectl|terraform';
const BACKTICK_COMMAND_RE = new RegExp(`\`((?:sudo\\s+)?(?:${COMMAND_BINARIES})\\s+[^\`\\n]+)\``, 'i');
const BARE_COMMAND_RE = new RegExp(
  `(?:^|\\s)((?:sudo\\s+)?(?:${COMMAND_BINARIES})\\s+(?:install|run|ci|init|exec|test|start|build|dev|deploy|login|link|clone|add|commit|push|pull|checkout|compose|auth|config|app|theme|env|create|-{1,2}[a-z])[^\\n.;]*)`,
  'i',
);
const VERIFICATION_TITLE_RE = /^(verify|check|test|confirm|validate|ensure|make sure|assert)\b/i;
const VERIFICATION_TAGS = new Set(['test', 'tests', 'testing', 'verify', 'verification', 'qa', 'validation']);
const ARCHITECTURE_RE =
  /\b(architecture|architect(?:ure|ural)?|design decision|decide|decision|choose|choice|trade-?offs?|pattern|schema|data model|topology)\b/i;

function detectCommand(text: string): string | null {
  const ticked = BACKTICK_COMMAND_RE.exec(text);
  if (ticked) return ticked[1].trim();
  const bare = BARE_COMMAND_RE.exec(text);
  return bare ? bare[1].trim() : null;
}

function classifyKind(input: {
  title: string;
  detail: string;
  tags: string[];
  command: string | null;
  snippet: RunbookSnippet | null;
}): RunbookStepKind {
  if (input.command) return 'terminal_command';
  const text = `${input.title} ${input.detail}`;
  if (
    VERIFICATION_TITLE_RE.test(input.title.trim()) ||
    input.tags.some((tag) => VERIFICATION_TAGS.has(tag.toLowerCase()))
  ) {
    return 'verification_check';
  }
  if (ARCHITECTURE_RE.test(text)) return 'architecture_decision';
  if (input.snippet) return 'code_snippet';
  return 'action';
}

export function runbookStepKindLabel(kind: RunbookStepKind): string {
  switch (kind) {
    case 'terminal_command':
      return 'Terminal command';
    case 'code_snippet':
      return 'Code snippet';
    case 'architecture_decision':
      return 'Architecture decision';
    case 'verification_check':
      return 'Verification check';
    case 'action':
      return 'Action';
    default: {
      const _exhaustive: never = kind;
      return _exhaustive;
    }
  }
}

export function runbookAnchorLabel(anchor: RunbookAnchor): string {
  switch (anchor) {
    case 'extracted':
      return 'Extractor-reported range';
    case 'event':
      return 'Timed event';
    case 'grounded_spec':
      return 'Grounded-spec citation';
    case 'transcript':
      return 'Transcript segment';
    case 'chapter':
      return 'Chapter';
    case 'visual':
      return 'Visual event';
    case 'none':
      return 'No verified timestamp';
    default: {
      const _exhaustive: never = anchor;
      return _exhaustive;
    }
  }
}

// ── Candidates ──────────────────────────────────────────────────────────────

interface StepCandidate {
  source: RunbookStep['source'];
  title: string;
  detail: string;
  tags: string[];
  priority: string | null;
  difficulty: string | null;
  explicitRange: [number, number] | null;
  eventSeconds: number | null;
}

function explicitRange(row: { start_s?: number | null; end_s?: number | null }): [number, number] | null {
  const start = row.start_s;
  const end = row.end_s;
  if (typeof start !== 'number' || typeof end !== 'number') return null;
  if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end < start) return null;
  return [start, end];
}

function collectCandidates(pack: RunbookPackInput, linkedSop: LinkedSop | null | undefined): StepCandidate[] {
  const out: StepCandidate[] = [];
  for (const requirement of pack.requirements ?? []) {
    const title = requirement.title?.trim() ?? '';
    if (!title) continue;
    out.push({
      source: { kind: 'requirement', id: requirement.id || `req-${out.length + 1}` },
      title,
      detail: requirement.detail?.trim() ?? '',
      tags: (requirement.tags ?? []).filter((tag) => tag.trim().length > 0),
      priority: requirement.priority?.trim() || null,
      difficulty: null,
      explicitRange: explicitRange(requirement),
      eventSeconds: null,
    });
  }
  for (const item of pack.action_items ?? []) {
    const title = item.title?.trim() ?? '';
    if (!title) continue;
    if (out.some((existing) => titlesAlign(existing.title, title))) continue;
    out.push({
      source: { kind: 'action_item', id: item.id || `action-${out.length + 1}` },
      title,
      detail: item.description?.trim() ?? '',
      tags: item.type ? [item.type] : [],
      priority: item.priority ?? null,
      difficulty: item.difficulty ?? null,
      explicitRange: explicitRange(item),
      eventSeconds: null,
    });
  }
  if (out.length > 0 || !linkedSop) return out;
  for (const step of linkedSop.steps) {
    const title = step.title.trim();
    if (!title) continue;
    out.push({
      source: { kind: 'sop_step', id: step.id },
      title,
      detail: step.description?.trim() ?? '',
      tags: [],
      priority: null,
      difficulty: null,
      explicitRange: null,
      eventSeconds: Number.isFinite(step.timestamp) ? (step.timestamp as number) : null,
    });
  }
  return out;
}

// ── Prerequisites (Step 0) ──────────────────────────────────────────────────

const ACCESS_RE =
  /((?:\b[A-Z][\w.+-]*\s+){0,2}(?:[Aa][Pp][Ii] [Kk]eys?|[Aa][Pp][Ii] [Tt]okens?|[Aa]ccess [Tt]okens?|[Cc]redentials|[Ss]ervice [Aa]ccounts?|[Ss]ign-?[Ii]n|[Ll]og-?[Ii]n))/g;
const RUNTIME_RE = /\b(Node(?:\.js)?|Python|npm|pnpm|Bun|Deno|Rust|TypeScript)\s*v?(\d+(?:\.\d+)*)\b/gi;

function sentenceAround(text: string, index: number): string {
  const start = Math.max(text.lastIndexOf('. ', index) + 1, 0);
  const endDot = text.indexOf('. ', index);
  const end = endDot === -1 ? text.length : endDot + 1;
  return text.slice(start, end).trim().slice(0, 160);
}

function compilePrerequisites(
  pack: RunbookPackInput,
  tools: ToolEvidence[],
  linkedSop: LinkedSop | null | undefined,
): RunbookPrerequisite[] {
  const out: RunbookPrerequisite[] = [];
  const ids = new Set<string>();
  const push = (row: RunbookPrerequisite) => {
    let id = row.id;
    let n = 2;
    while (ids.has(id)) id = `${row.id}-${n++}`;
    ids.add(id);
    out.push({ ...row, id });
  };

  for (const tool of tools) {
    const entity = linkedSop?.entities.find((row) => row.name.toLowerCase() === tool.name.toLowerCase());
    push({
      id: `prereq-tool-${slug(tool.name)}`,
      kind: 'tool',
      title: tool.name,
      detail: tool.check ?? tool.kind,
      href: entity?.docsUrl ?? entity?.officialUrl ?? null,
      evidence: tool.evidence,
    });
  }

  for (const item of linkedSop?.checklist ?? []) {
    if (item.source !== 'stack' || item.id.startsWith('chk_tool_')) continue;
    push({
      id: `prereq-check-${slug(item.id)}`,
      kind: 'stack_check',
      title: item.title,
      detail: item.stack ? `Official ${item.stack} check` : null,
      href: item.href ?? null,
      evidence: null,
    });
  }

  const scanned = [
    ...(pack.requirements ?? []).map((row) => `${row.title}. ${row.detail ?? ''}`),
    ...(pack.action_items ?? []).map((row) => `${row.title}. ${row.description}`),
    ...tools.map((tool) => tool.evidence ?? ''),
  ];
  const seenAccess = new Set<string>();
  for (const text of scanned) {
    for (const match of text.matchAll(ACCESS_RE)) {
      const phrase = match[1].replace(/\s+/g, ' ').trim();
      const key = normalizeProse(phrase);
      if (!key || seenAccess.has(key)) continue;
      seenAccess.add(key);
      push({
        id: `prereq-access-${slug(phrase)}`,
        kind: 'access',
        title: `Access: ${phrase}`,
        detail: sentenceAround(text, match.index ?? 0),
        href: null,
        evidence: null,
      });
    }
  }
  const runtimes = new Map<string, { label: string; version: string; detail: string }>();
  for (const text of scanned) {
    for (const match of text.matchAll(RUNTIME_RE)) {
      const label = match[1];
      const version = match[2];
      const family = label.toLowerCase().replace(/\.js$/, '');
      const existing = runtimes.get(family);
      if (!existing || version.length > existing.version.length) {
        runtimes.set(family, { label, version, detail: sentenceAround(text, match.index ?? 0) });
      }
    }
  }
  for (const runtime of runtimes.values()) {
    push({
      id: `prereq-runtime-${slug(`${runtime.label} ${runtime.version}`)}`,
      kind: 'runtime',
      title: `Runtime: ${runtime.label} v${runtime.version}`,
      detail: runtime.detail,
      href: null,
      evidence: null,
    });
  }
  return out;
}

// ── Compile ─────────────────────────────────────────────────────────────────

function fence(lang: string | null, body: string): string {
  return `\`\`\`${lang ?? ''}\n${body.replace(/\n+$/, '')}\n\`\`\``;
}

function rangeLabel(range: [number, number] | null): string {
  if (!range) return 'No verified timestamp';
  return `${formatSeconds(range[0])}–${formatSeconds(range[1])}`;
}

export function compileRunbook(input: CompileRunbookInput): Runbook {
  const { pack } = input;
  const linkedSop = input.linkedSop ?? null;
  const segmentIndex = buildSegmentIndex(pack.transcript?.segments);
  const tools = toolEvidence(pack.stack);
  const grounded = groundedIndex(pack.grounded_spec, segmentIndex);
  const chapters: AppBuilderChapter[] = (pack.chapters ?? []).map((chapter) => ({
    start: chapter.start,
    end: chapter.end,
    topic: chapter.topic,
    key_points: chapter.key_points ?? [],
  }));
  const visualEvents: AppBuilderVisualEvent[] = visualEventsFromPack({
    visual_context: pack.visual_context ?? null,
    keyframes: pack.keyframes ?? [],
  });
  const snippets: RunbookSnippet[] = (pack.code_snippets ?? []).flatMap((snippet) => {
    const content = snippet.content?.trim() ?? '';
    if (!content) return [];
    return [{ path_hint: snippet.path_hint ?? null, lang: snippet.lang ?? null, content }];
  });
  const snippetTokens = snippets.map((snippet) => new Set(codeTokens(snippet)));
  const stages = (pack.architecture?.stages ?? []).map((stage) => ({
    name: stage.name,
    tokens: new Set(proseTokens(`${stage.name} ${stage.description ?? ''}`)),
  }));
  const artifacts = (pack.artifacts ?? []).map((artifact) => ({
    path: artifact.path_hint,
    tokens: new Set(proseTokens(`${artifact.path_hint.replace(/[/_.-]/g, ' ')} ${artifact.purpose}`)),
  }));

  const usedIds = new Set<string>();
  const steps: RunbookStep[] = [];

  for (const candidate of collectCandidates(pack, linkedSop)) {
    const text = `${candidate.title} ${candidate.detail}`;
    const normalizedText = normalizeProse(text);
    const stepTokens = new Set(proseTokens(text));
    const titleTokens = new Set(proseTokens(candidate.title));
    const namedTools = tools.filter((tool) => toolNamedIn(normalizedText, tool));

    // Bonuses: segments that quote named-tool evidence (+4) and validated citations (+1, +3 when titles align).
    const bonuses = new Map<number, number>();
    for (const tool of namedTools) {
      for (const quote of tool.quotes) {
        const needle = normalizeProse(quote);
        if (!needle) continue;
        for (const row of segmentIndex.rows) {
          if (normalizeProse(row.text).includes(needle)) {
            bonuses.set(row.position, (bonuses.get(row.position) ?? 0) + 4);
          }
        }
      }
    }
    for (const [position, citations] of grounded.byPosition) {
      const aligned = citations.some((ref) => titlesAlign(ref.requirementTitle, candidate.title));
      bonuses.set(position, (bonuses.get(position) ?? 0) + (aligned ? 3 : 1));
    }

    let range: [number, number] | null = null;
    let anchor: RunbookAnchor = 'none';
    let quote: string | undefined;
    let groundedIds: string[] = [];

    if (candidate.explicitRange) {
      range = candidate.explicitRange;
      anchor = 'extracted';
    } else if (candidate.eventSeconds !== null) {
      const row = containingSegment(segmentIndex, candidate.eventSeconds);
      range = row ? [row.start, row.end] : [candidate.eventSeconds, candidate.eventSeconds];
      anchor = 'event';
      quote = row?.text;
    } else {
      const matches = scoreSegments(segmentIndex, stepTokens, titleTokens, bonuses);
      let best: SegmentMatch | null = null;
      for (const match of matches) {
        if (!match.candidate) continue;
        if (!best || match.score > best.score) best = match;
      }
      if (best) {
        range = extendRange(segmentIndex, matches, best.position);
        const citations = grounded.byPosition.get(best.position) ?? [];
        if (citations.length > 0) {
          anchor = 'grounded_spec';
          quote = citations[0].quote;
          groundedIds = citations.map((ref) => ref.requirementId);
        } else {
          anchor = 'transcript';
          quote = segmentIndex.rows[best.position].text;
        }
      } else {
        const derived = deriveSopTimestampFromPackFields(
          { title: candidate.title, description: candidate.detail },
          chapters,
          visualEvents,
        );
        if (derived !== undefined) {
          const chapter = chapters.find((row) => row.start === derived);
          if (chapter) {
            range = [chapter.start, Math.max(chapter.start, chapter.end)];
            anchor = 'chapter';
          } else {
            range = [derived, derived];
            anchor = 'visual';
          }
        }
      }
    }

    const command = detectCommand(text);
    let snippet: RunbookSnippet | null = null;
    let snippetScore = 0;
    for (let index = 0; index < snippets.length; index += 1) {
      const score = sharedTokens(snippetTokens[index], stepTokens).length;
      if (score >= 2 && score > snippetScore) {
        snippet = snippets[index];
        snippetScore = score;
      }
    }
    let architectureStage: string | null = null;
    let stageScore = 0;
    for (const stage of stages) {
      const score = sharedTokens(stage.tokens, stepTokens).length;
      if (score >= 2 && score > stageScore) {
        architectureStage = stage.name;
        stageScore = score;
      }
    }
    const outputs = artifacts
      .filter((artifact) => sharedTokens(artifact.tokens, stepTokens).length >= 2)
      .map((artifact) => artifact.path);
    const inputs = namedTools.map((tool) => tool.name);
    const kind = classifyKind({ title: candidate.title, detail: candidate.detail, tags: candidate.tags, command, snippet });

    let verification: string;
    let verificationSource: RunbookVerificationSource;
    const acceptance = grounded.acceptance.filter((row) => groundedIds.includes(row.requirementId));
    const checks = namedTools.filter((tool) => tool.check);
    if (acceptance.length > 0) {
      verification = acceptance
        .map((row) => `Given: ${row.given} · When: ${row.when} · Then: ${row.then}`)
        .join('\n');
      verificationSource = 'grounded_spec';
    } else if (checks.length > 0) {
      verification = checks.map((tool) => `${tool.name}: ${tool.check}`).join('\n');
      verificationSource = 'stack_check';
    } else if (range) {
      verification = `Compare your result with the video at ${rangeLabel(range)}. The pack has no explicit check for this step.`;
      verificationSource = 'none';
    } else {
      verification =
        'The pack has no explicit check and no verified timestamp for this step; compare against the source video.';
      verificationSource = 'none';
    }

    const attachedSnippet = snippet;
    const contentBlocks: string[] = [];
    if (candidate.detail) contentBlocks.push(candidate.detail);
    const meta = [
      candidate.priority ? `Priority: ${candidate.priority}` : null,
      candidate.difficulty ? `Difficulty: ${candidate.difficulty}` : null,
      candidate.tags.length ? `Tags: ${candidate.tags.join(', ')}` : null,
    ].filter((row): row is string => Boolean(row));
    if (meta.length) contentBlocks.push(meta.join(' · '));
    if (quote) contentBlocks.push(`> "${quote}" — ${rangeLabel(range)}`);
    if (command) contentBlocks.push(fence('bash', command));
    if (attachedSnippet) {
      contentBlocks.push(
        `${attachedSnippet.path_hint ? `Snippet: ${attachedSnippet.path_hint}\n` : ''}${fence(attachedSnippet.lang, attachedSnippet.content)}`,
      );
    }

    let id = `rb-${slug(candidate.source.id)}`;
    let n = 2;
    while (usedIds.has(id)) id = `rb-${slug(candidate.source.id)}-${n++}`;
    usedIds.add(id);

    steps.push({
      id,
      step_number: steps.length + 1,
      title: candidate.title,
      kind,
      timestamp_range: range,
      anchor,
      content_markdown: contentBlocks.join('\n\n'),
      verification,
      verification_source: verificationSource,
      detail: candidate.detail,
      inputs,
      outputs,
      tags: candidate.tags,
      priority: candidate.priority,
      difficulty: candidate.difficulty,
      command,
      snippet: attachedSnippet,
      architecture_stage: architectureStage,
      evidence: { ...(quote ? { quote } : {}), keyframe: pickKeyframe(pack.keyframes, range) },
      source: candidate.source,
    });
  }

  let duration = 0;
  for (const row of segmentIndex.rows) duration = Math.max(duration, row.end);
  for (const chapter of chapters) duration = Math.max(duration, chapter.end);

  return {
    version: RUNBOOK_VERSION,
    videoId: pack.video_id,
    packId: pack.id,
    sourceUrl: pack.source_url,
    sourceHash: pack.provenance.source_hash,
    durationSeconds: duration > 0 ? duration : null,
    prerequisites: compilePrerequisites(pack, tools, linkedSop),
    steps,
    coverage: {
      anchored: steps.filter((step) => step.timestamp_range !== null).length,
      total: steps.length,
    },
  };
}

// ── Chat grounding handoff ──────────────────────────────────────────────────

/** Bounded step slice sent with /api/chat so the assistant re-grounds to one step. */
export interface ChatStepContext {
  id: string;
  step_number: number;
  total_steps?: number;
  title: string;
  kind?: RunbookStepKind;
  timestamp_range?: [number, number] | null;
  content_markdown?: string;
  verification?: string;
  tools?: string[];
}

export const CHAT_STEP_CONTENT_MAX = 4_000;
export const CHAT_STEP_VERIFICATION_MAX = 1_000;

export function runbookStepToChatContext(step: RunbookStep, totalSteps: number): ChatStepContext {
  return {
    id: step.id,
    step_number: step.step_number,
    total_steps: totalSteps,
    title: step.title.slice(0, 160),
    kind: step.kind,
    timestamp_range: step.timestamp_range,
    content_markdown: step.content_markdown.slice(0, CHAT_STEP_CONTENT_MAX),
    verification: step.verification.slice(0, CHAT_STEP_VERIFICATION_MAX),
    tools: step.inputs.slice(0, 32),
  };
}

// ── Lookups ─────────────────────────────────────────────────────────────────

/** First step (in runbook order) whose anchored range contains `seconds`. */
export function runbookStepForTime(runbook: Runbook, seconds: number): RunbookStep | null {
  if (!Number.isFinite(seconds)) return null;
  return (
    runbook.steps.find(
      (step) =>
        step.timestamp_range !== null &&
        step.timestamp_range[0] <= seconds &&
        seconds <= step.timestamp_range[1],
    ) ?? null
  );
}

export function runbookStepHash(stepNumber: number): string {
  return `#step-${Math.max(0, Math.floor(stepNumber))}`;
}

/** `#step-N` → N (0 = prerequisites). Anything else → null. */
export function parseRunbookStepHash(hash: string | null | undefined): number | null {
  if (!hash) return null;
  const match = /^#?step-(\d{1,3})$/.exec(hash.trim());
  return match ? Number(match[1]) : null;
}

export function clampRunbookStep(stepNumber: number, totalSteps: number): number {
  if (!Number.isFinite(stepNumber)) return 0;
  return Math.min(Math.max(0, Math.floor(stepNumber)), Math.max(0, totalSteps));
}

// ── Markdown ────────────────────────────────────────────────────────────────

export function renderRunbookMarkdown(
  runbook: Runbook,
  progress?: Pick<RunbookProgress, 'checkedPrerequisites' | 'completedSteps'> | null,
): string {
  const checked = new Set(progress?.checkedPrerequisites ?? []);
  const completed = new Set(progress?.completedSteps ?? []);
  const lines: string[] = [
    `# Runbook — ${runbook.videoId}`,
    '',
    `Source: ${runbook.sourceUrl}`,
    `Pack: ${runbook.packId} · source_hash ${runbook.sourceHash}`,
    `Steps anchored to video evidence: ${runbook.coverage.anchored} / ${runbook.coverage.total}.`,
    'Timestamps come from pack evidence (extractor ranges, grounded-spec citations, transcript segments, chapters, visual events). A step without evidence says "No verified timestamp". A checked box is a local note, not proof the step was performed.',
    '',
    '## Step 0 — Prerequisites & Environment',
    '',
  ];
  if (runbook.prerequisites.length === 0) {
    lines.push('_No prerequisites named in this pack._', '');
  } else {
    for (const row of runbook.prerequisites) {
      const mark = checked.has(row.id) ? 'x' : ' ';
      const detail = row.detail ? ` — ${row.detail}` : '';
      const link = row.href ? ` ([docs](${row.href}))` : '';
      lines.push(`- [${mark}] ${row.title}${detail}${link}`);
    }
    lines.push('');
  }
  if (runbook.steps.length === 0) {
    lines.push('_No runbook steps on this pack._', '');
  }
  for (const step of runbook.steps) {
    const done = completed.has(step.id) ? ' ✓' : '';
    lines.push(`## Step ${step.step_number} — ${step.title} [${rangeLabel(step.timestamp_range)}]${done}`, '');
    lines.push(
      `Type: ${runbookStepKindLabel(step.kind)} · Anchor: ${runbookAnchorLabel(step.anchor)} · Source: ${step.source.id}`,
      '',
    );
    if (step.content_markdown) lines.push(step.content_markdown, '');
    if (step.inputs.length) lines.push(`Inputs: ${step.inputs.join(', ')}`);
    if (step.outputs.length) lines.push(`Outputs: ${step.outputs.join(', ')}`);
    if (step.architecture_stage) lines.push(`Architecture stage: ${step.architecture_stage}`);
    if (step.inputs.length || step.outputs.length || step.architecture_stage) lines.push('');
    lines.push(`Verification: ${step.verification}`, '');
  }
  return lines.join('\n').replace(/\n{3,}/g, '\n\n');
}
