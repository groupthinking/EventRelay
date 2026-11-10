import 'server-only';

import {
  rebaseGroundedCitations,
  type GroundedSpecCandidate,
  type GroundedSpecExtraction,
} from '@/lib/grounded-build-spec';
import {
  parseArchitecture,
  parseArtifacts,
  parsePackActionItems,
  parsePackChapters,
  parseStack,
  type VideoPackActionItem,
  type VideoPackChapter,
} from '@/lib/video-pack-types';

/** Structural slice merged from sectional extracts (avoids circular import with extractor). */
export interface MergedVideoPackSectionSpec {
  spec_json_salvaged?: boolean;
  grounded_spec?: GroundedSpecExtraction;
  transcript: {
    language: string | null;
    full_text: string;
    segments: Array<{ idx: number; start_s: number; end_s: number; text: string }>;
  };
  keyframes: Array<{ t_s: number; image_path?: string | null; desc?: string | null }>;
  concepts: string[];
  requirements: Array<{
    id: string;
    title: string;
    detail?: string | null;
    priority?: string | null;
    tags?: string[];
  }>;
  code_snippets: Array<{ path_hint?: string | null; lang?: string | null; content: string }>;
  architecture?: ReturnType<typeof parseArchitecture>;
  artifacts: ReturnType<typeof parseArtifacts>;
  stack: ReturnType<typeof parseStack>;
  visual_context: {
    visual_elements: Array<{
      timestamp: number;
      element_type: string;
      content: string;
      confidence?: number;
      frame_path?: string | null;
    }>;
    summary?: string | null;
    frame_analysis_count?: number;
    processing_timestamp?: string | null;
  } | null;
  chapters?: VideoPackChapter[];
  action_items?: VideoPackActionItem[];
}

function normalizeKey(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
}

function dedupeStrings(values: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const value of values) {
    const trimmed = value.trim();
    if (!trimmed) continue;
    const key = normalizeKey(trimmed);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(trimmed);
  }
  return out;
}

function dedupeBy<T>(items: T[], keyFn: (item: T) => string, normalize = true): T[] {
  const seen = new Set<string>();
  const out: T[] = [];
  for (const item of items) {
    const rawKey = keyFn(item);
    const key = normalize ? normalizeKey(rawKey) : rawKey;
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}

function mergeTranscript(
  specs: MergedVideoPackSectionSpec[],
  evidenceKey: (text: string) => string,
): MergedVideoPackSectionSpec['transcript'] {
  const language =
    specs.map((spec) => spec.transcript.language).find((lang) => typeof lang === 'string' && lang) ??
    null;
  const segments = specs
    .flatMap((spec) => spec.transcript.segments)
    .sort((a, b) => a.start_s - b.start_s || a.idx - b.idx);
  const seenSegment = new Set<string>();
  const uniqueSegments = segments.filter((segment) => {
    const key = `${segment.start_s}:${segment.end_s}:${evidenceKey(segment.text)}`;
    if (seenSegment.has(key)) return false;
    seenSegment.add(key);
    return true;
  });
  const full_text = uniqueSegments.map((segment) => segment.text).join(' ').trim();
  return {
    language,
    full_text: full_text.length > 0 ? full_text : specs.map((s) => s.transcript.full_text).join(' ').trim(),
    segments: uniqueSegments.map((segment, index) => ({ ...segment, idx: index })),
  };
}

function mergeArchitecture(
  specs: MergedVideoPackSectionSpec[],
): MergedVideoPackSectionSpec['architecture'] {
  const withArch = specs.filter((spec) => spec.architecture);
  if (withArch.length === 0) return null;
  const summary = withArch
    .map((spec) => spec.architecture?.summary?.trim() ?? '')
    .filter((line) => line.length > 0)
    .join(' ');
  const stages = dedupeBy(
    withArch.flatMap((spec) => spec.architecture?.stages ?? []),
    (stage) => stage.id || stage.name,
  );
  const mermaid = withArch
    .map((spec) => spec.architecture?.mermaid?.trim() ?? '')
    .find((line) => line.length > 0);
  return parseArchitecture({
    summary: summary || null,
    stages,
    mermaid: mermaid || null,
  });
}

function namespaceGroundedSpec(
  spec: GroundedSpecCandidate,
  shardIndex: number,
): GroundedSpecCandidate {
  // The ordinal keeps even long IDs with the same truncated prefix distinct.
  const shardId = (id: string, index: number) => `s${shardIndex + 1}-${index + 1}-${id}`.slice(0, 64);
  const scopeRow = <T extends { id: string }>(row: T, index: number): T => ({
    ...row,
    id: shardId(row.id, index),
  });
  const screenIds = new Map(spec.screens.map((row, index) => [row.id, shardId(row.id, index)]));
  const requirementIds = new Map(spec.requirements.map((row, index) => [row.id, shardId(row.id, index)]));
  // Reserve ordinal 0 for a missing reference so it cannot bind to another shard.
  const screenId = (id: string) => screenIds.get(id) ?? shardId(id, -1);
  const requirementId = (id: string) => requirementIds.get(id) ?? shardId(id, -1);
  return {
    ...spec,
    screens: spec.screens.map(scopeRow),
    state: spec.state.map(scopeRow),
    requirements: spec.requirements.map((row, index) => ({ ...scopeRow(row, index), screenId: screenId(row.screenId) })),
    acceptanceCriteria: spec.acceptanceCriteria.map((row, index) => ({ ...scopeRow(row, index), requirementId: requirementId(row.requirementId) })),
    unresolved: spec.unresolved.map((row, index) => ({ ...scopeRow(row, index), requirementIds: row.requirementIds.map(requirementId) })),
    unsupported: spec.unsupported.map((row, index) => ({ ...scopeRow(row, index), requirementIds: row.requirementIds.map(requirementId) })),
  };
}

function mergeAvailableGroundedSpecs(candidates: [GroundedSpecCandidate, ...GroundedSpecCandidate[]]): GroundedSpecCandidate {
  const [first] = candidates;
  return {
    ...first,
    sourceStatus: candidates.every((candidate) => candidate.sourceStatus === 'full') ? 'full' : 'partial',
    confidence: Math.min(...candidates.map((candidate) => candidate.confidence)),
    limitations: dedupeStrings(candidates.flatMap((candidate) => candidate.limitations)),
    screens: candidates.flatMap((candidate) => candidate.screens),
    state: candidates.flatMap((candidate) => candidate.state),
    requirements: candidates.flatMap((candidate) => candidate.requirements),
    acceptanceCriteria: candidates.flatMap((candidate) => candidate.acceptanceCriteria),
    unresolved: candidates.flatMap((candidate) => candidate.unresolved),
    unsupported: candidates.flatMap((candidate) => candidate.unsupported),
  };
}

function mergeGroundedSpec(
  specs: MergedVideoPackSectionSpec[],
  transcript: MergedVideoPackSectionSpec['transcript'],
  visualContext: MergedVideoPackSectionSpec['visual_context'],
): GroundedSpecExtraction | undefined {
  const candidates = specs.flatMap((spec, index) =>
    spec.grounded_spec ? [{ spec, value: spec.grounded_spec, index }] : [],
  );
  const available = candidates.filter(({ value }) => value.status === 'available');
  const merged: GroundedSpecCandidate[] = [];
  for (const { spec, value, index } of available) {
    const rebased = rebaseGroundedCitations(value, spec, { transcript, visual_context: visualContext });
    if (rebased.status !== 'available') return rebased;
    merged.push(available.length > 1 ? namespaceGroundedSpec(rebased.spec, index) : rebased.spec);
  }
  const [first, ...rest] = merged;
  if (first) return { status: 'available', spec: mergeAvailableGroundedSpecs([first, ...rest]) };
  return candidates[candidates.length - 1]?.value;
}

function mergeVisualContext(
  specs: MergedVideoPackSectionSpec[],
  evidenceKey: (text: string) => string,
): MergedVideoPackSectionSpec['visual_context'] {
  const contexts = specs.filter((spec) => spec.visual_context);
  if (contexts.length === 0) return null;
  const visual_elements = dedupeBy(
    contexts.flatMap((spec) => spec.visual_context?.visual_elements ?? []),
    (element) => `${element.timestamp}:${evidenceKey(element.content)}`,
    false,
  ).sort((a, b) => a.timestamp - b.timestamp);
  const summary = contexts
    .map((spec) => spec.visual_context?.summary?.trim() ?? '')
    .filter((line) => line.length > 0)
    .join(' ');
  const frame_analysis_count = visual_elements.length;
  return {
    visual_elements,
    summary: summary || null,
    frame_analysis_count,
    processing_timestamp: contexts[contexts.length - 1]?.visual_context?.processing_timestamp ?? null,
  };
}

/**
 * Merge sectional Video Pack extracts in section order (not completion order).
 */
export function mergeSectionVideoPackSpecs(
  specs: MergedVideoPackSectionSpec[],
): MergedVideoPackSectionSpec {
  if (specs.length === 0) {
    throw new Error('mergeSectionVideoPackSpecs requires at least one sectional spec');
  }
  if (specs.length === 1) {
    return specs[0];
  }

  // A normalized duplicate may differ from the exact quote that was validated.
  const evidenceKey = specs.some((spec) => spec.grounded_spec?.status === 'available')
    ? (text: string) => text.trim()
    : normalizeKey;
  const transcript = mergeTranscript(specs, evidenceKey);
  const keyframes = dedupeBy(
    specs.flatMap((spec) => spec.keyframes),
    (frame) => `${frame.t_s}:${normalizeKey(frame.desc ?? '')}`,
  ).sort((a, b) => a.t_s - b.t_s);
  const concepts = dedupeStrings(specs.flatMap((spec) => spec.concepts));
  const requirements = dedupeBy(
    specs.flatMap((spec) => spec.requirements),
    (req) => req.id || req.title,
  );
  const code_snippets = dedupeBy(
    specs.flatMap((spec) => spec.code_snippets),
    (snippet) => `${snippet.path_hint ?? ''}:${snippet.content.slice(0, 120)}`,
  );
  const artifacts = parseArtifacts(
    dedupeBy(specs.flatMap((spec) => spec.artifacts), (item) => item.path_hint),
  );
  const stack = parseStack({
    tools: dedupeBy(
      specs.flatMap((spec) => spec.stack.tools),
      (tool) => tool.name,
    ),
  });
  const chapters = parsePackChapters(
    dedupeBy(
      specs.flatMap((spec) => spec.chapters ?? []),
      (chapter) => `${chapter.start}:${chapter.topic}`,
    ) as VideoPackChapter[],
  );
  const action_items = parsePackActionItems(
    dedupeBy(
      specs.flatMap((spec) => spec.action_items ?? []),
      (item) => item.id || item.title,
    ) as VideoPackActionItem[],
  );

  const spec_json_salvaged = specs.some((spec) => spec.spec_json_salvaged);
  const visual_context = mergeVisualContext(specs, evidenceKey);

  return {
    ...(spec_json_salvaged ? { spec_json_salvaged: true } : {}),
    grounded_spec: mergeGroundedSpec(specs, transcript, visual_context),
    transcript,
    keyframes,
    concepts,
    requirements,
    code_snippets,
    architecture: mergeArchitecture(specs),
    artifacts,
    stack,
    visual_context,
    chapters,
    action_items,
  };
}
