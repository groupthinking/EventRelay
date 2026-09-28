import 'server-only';

import {
  mergeSectionVideoPackSpecs,
  type MergedVideoPackSectionSpec,
} from '@/lib/video-pack-extract-merge';
import type { TranscriptChunkEvidence } from '@/lib/transcript-team';
import {
  decideExtractNext,
  type JevExtractAction,
  type JevExtractDecision,
  type JevExtractEvaluate,
} from '@/lib/video-pack-extract-jev';

/**
 * Gate 4 consolidator. Merges shard specs and transcript evidence into one
 * tree, then scores the code 0/1. Jev may suggest a next action on that
 * merged state; it never sets `ok`. Sandbox build stays off unless the
 * caller sets the flag and the app passed.
 */

export const SANDBOX_BUILD_DEFAULT = false;

const POST_CHECK_ACTIONS = [
  'retry',
  'consolidate',
  'request-more-evidence',
  'stop',
] as const satisfies readonly JevExtractAction[];

const NODE_BUILTINS = new Set([
  'assert',
  'buffer',
  'child_process',
  'cluster',
  'console',
  'constants',
  'crypto',
  'dgram',
  'dns',
  'events',
  'fs',
  'http',
  'http2',
  'https',
  'module',
  'net',
  'os',
  'path',
  'perf_hooks',
  'process',
  'querystring',
  'readline',
  'stream',
  'string_decoder',
  'timers',
  'tls',
  'tty',
  'url',
  'util',
  'v8',
  'vm',
  'worker_threads',
  'zlib',
]);

const DEPENDENCY_FIELDS = [
  'dependencies',
  'devDependencies',
  'peerDependencies',
  'optionalDependencies',
] as const;

const FROM_SPECIFIER = /\bfrom\s+['"]([^'"]+)['"]/g;
const SIDE_EFFECT_SPECIFIER = /\bimport\s+['"]([^'"]+)['"]/g;
const REQUIRE_SPECIFIER = /\brequire\(\s*['"]([^'"]+)['"]\s*\)/g;
const DYNAMIC_SPECIFIER = /\bimport\(\s*['"]([^'"]+)['"]\s*\)/g;

export interface ConsolidatedVideoPackTree extends MergedVideoPackSectionSpec {
  transcript_evidence?: TranscriptChunkEvidence[];
}

export interface ConsolidatedAppCheck {
  ok: 0 | 1;
  failures: string[];
}

export interface ConsolidateShardExtractInput {
  videoId: string;
  specs: MergedVideoPackSectionSpec[];
  transcriptEvidence?: TranscriptChunkEvidence[];
  durationSeconds?: number | null;
  attempt?: number;
  sandboxBuild?: boolean;
}

export interface ConsolidateShardExtractDeps {
  decide?: typeof decideExtractNext;
  buildSandbox?: (tree: ConsolidatedVideoPackTree) => void | Promise<void>;
  evaluateFn?: JevExtractEvaluate;
}

export interface ConsolidateShardExtractResult {
  tree: ConsolidatedVideoPackTree;
  app: ConsolidatedAppCheck;
  decision: JevExtractDecision | null;
  sandboxBuilt: boolean;
}

function isPackageJsonPath(pathHint: string): boolean {
  const base = pathHint.split(/[/\\]/).pop();
  return base === 'package.json';
}

function snippetPath(
  snippet: { path_hint?: string | null },
  index: number,
): string {
  const hint = snippet.path_hint?.trim();
  return hint && hint.length > 0 ? hint : `snippet-${index}.txt`;
}

function packageNameFromSpecifier(specifier: string): string | null {
  if (
    specifier.startsWith('.') ||
    specifier.startsWith('/') ||
    specifier.startsWith('node:')
  ) {
    return null;
  }
  const name = specifier.startsWith('@')
    ? specifier.split('/').slice(0, 2).join('/')
    : (specifier.split('/')[0] ?? specifier);
  if (!name || NODE_BUILTINS.has(name)) return null;
  return name;
}

function specifiersIn(content: string): string[] {
  const found: Array<{ index: number; specifier: string }> = [];
  for (const pattern of [
    FROM_SPECIFIER,
    SIDE_EFFECT_SPECIFIER,
    REQUIRE_SPECIFIER,
    DYNAMIC_SPECIFIER,
  ]) {
    pattern.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(content)) !== null) {
      const specifier = match[1];
      if (!specifier) continue;
      found.push({ index: match.index, specifier });
    }
  }
  found.sort((a, b) => a.index - b.index);
  return found.map((item) => item.specifier);
}

function textFailures(pathHint: string, content: string): string[] {
  const failures: string[] = [];
  if (/\bplaceholder\b/i.test(content)) {
    failures.push(`${pathHint}: contains placeholder`);
  }
  if (content.includes('...') || content.includes('…') || /\bellipsis\b/i.test(content)) {
    failures.push(`${pathHint}: contains ellipsis`);
  }
  if (/rest of code here/i.test(content)) {
    failures.push(`${pathHint}: contains "rest of code here"`);
  }
  return failures;
}

function dependencyNames(content: string, pathHint: string, failures: string[]): Set<string> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(content) as unknown;
  } catch {
    failures.push(`${pathHint}: package.json is not valid JSON`);
    return new Set();
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    failures.push(`${pathHint}: package.json is not valid JSON`);
    return new Set();
  }
  const record = parsed as Record<string, unknown>;
  const names = new Set<string>();
  for (const field of DEPENDENCY_FIELDS) {
    const block = record[field];
    if (block === null || typeof block !== 'object' || Array.isArray(block)) continue;
    for (const name of Object.keys(block)) {
      names.add(name);
    }
  }
  return names;
}

export function checkConsolidatedApp(
  snippets: MergedVideoPackSectionSpec['code_snippets'],
): ConsolidatedAppCheck {
  const failures: string[] = [];
  const declared = new Set<string>();
  snippets.forEach((snippet, index) => {
    const pathHint = snippetPath(snippet, index);
    if (!isPackageJsonPath(pathHint)) return;
    for (const name of dependencyNames(snippet.content, pathHint, failures)) {
      declared.add(name);
    }
  });

  snippets.forEach((snippet, index) => {
    const pathHint = snippetPath(snippet, index);
    failures.push(...textFailures(pathHint, snippet.content));
    if (isPackageJsonPath(pathHint)) return;
    const seen = new Set<string>();
    for (const specifier of specifiersIn(snippet.content)) {
      const name = packageNameFromSpecifier(specifier);
      if (!name || seen.has(name)) continue;
      seen.add(name);
      if (!declared.has(name)) {
        failures.push(`${pathHint}: import '${name}' is missing from package.json`);
      }
    }
  });

  return { ok: failures.length === 0 ? 1 : 0, failures };
}

function mergeTranscriptEvidence(
  rows: TranscriptChunkEvidence[] | undefined,
): TranscriptChunkEvidence[] | undefined {
  if (!rows || rows.length === 0) return undefined;
  const sorted = [...rows].sort((a, b) => a.index - b.index || a.start_s - b.start_s);
  const seen = new Set<number>();
  const merged: TranscriptChunkEvidence[] = [];
  for (const row of sorted) {
    if (seen.has(row.index)) continue;
    seen.add(row.index);
    merged.push(row);
  }
  return merged;
}

function isPostCheckAction(action: JevExtractAction): action is (typeof POST_CHECK_ACTIONS)[number] {
  return (POST_CHECK_ACTIONS as readonly string[]).includes(action);
}

export async function consolidateShardExtract(
  input: ConsolidateShardExtractInput,
  deps: ConsolidateShardExtractDeps = {},
): Promise<ConsolidateShardExtractResult> {
  const merged = mergeSectionVideoPackSpecs(input.specs);
  const transcriptEvidence = mergeTranscriptEvidence(input.transcriptEvidence);
  const tree: ConsolidatedVideoPackTree = transcriptEvidence
    ? { ...merged, transcript_evidence: transcriptEvidence }
    : { ...merged };
  const app = checkConsolidatedApp(tree.code_snippets);
  const rawDecision = await (deps.decide ?? decideExtractNext)(
    {
      videoId: input.videoId,
      shardCount: input.specs.length,
      durationSeconds: input.durationSeconds ?? 0,
      costUnits: 0,
      costBoundUnits: 0,
      validationFailures: app.failures,
      attempt: input.attempt ?? 1,
      stage: 'merged',
    },
    {
      actions: POST_CHECK_ACTIONS,
      ...(deps.evaluateFn ? { evaluateFn: deps.evaluateFn } : {}),
    },
  );
  const decision = rawDecision && isPostCheckAction(rawDecision.action) ? rawDecision : null;
  const sandboxBuild = input.sandboxBuild ?? SANDBOX_BUILD_DEFAULT;
  let sandboxBuilt = false;
  if (
    sandboxBuild &&
    app.ok === 1 &&
    decision?.action !== 'stop' &&
    deps.buildSandbox
  ) {
    await deps.buildSandbox(tree);
    sandboxBuilt = true;
  }
  return { tree, app, decision, sandboxBuilt };
}
