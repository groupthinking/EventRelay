import 'server-only';

import type { GroundedSpecExtraction } from '@/lib/grounded-build-spec';
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

function dedupeBy<T>(items: T[], keyFn: (item: T) => string): T[] {
  const seen = new Set<string>();
  const out: T[] = [];
  for (const item of items) {
    const key = normalizeKey(keyFn(item));
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}

function mergeTranscript(
  specs: MergedVideoPackSectionSpec[],
): MergedVideoPackSectionSpec['transcript'] {
  const language =
    specs.map((spec) => spec.transcript.language).find((lang) => typeof lang === 'string' && lang) ??
    null;
  const segments = specs
    .flatMap((spec) => spec.transcript.segments)
    .sort((a, b) => a.start_s - b.start_s || a.idx - b.idx);
  const seenSegment = new Set<string>();
  const uniqueSegments = segments.filter((segment) => {
    const key = `${segment.start_s}:${segment.end_s}:${normalizeKey(segment.text)}`;
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

function mergeGroundedSpec(
  specs: MergedVideoPackSectionSpec[],
): GroundedSpecExtraction | undefined {
  const candidates = specs
    .map((spec) => spec.grounded_spec)
    .filter((value): value is GroundedSpecExtraction => value !== undefined);
  if (candidates.length === 0) return undefined;
  const available = candidates.filter((item) => item.status === 'available');
  const pool = available.length > 0 ? available : candidates;
  return pool[pool.length - 1];
}

function mergeVisualContext(
  specs: MergedVideoPackSectionSpec[],
): MergedVideoPackSectionSpec['visual_context'] {
  const contexts = specs.filter((spec) => spec.visual_context);
  if (contexts.length === 0) return null;
  const visual_elements = dedupeBy(
    contexts.flatMap((spec) => spec.visual_context?.visual_elements ?? []),
    (element) => `${element.timestamp}:${normalizeKey(element.content)}`,
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

  const transcript = mergeTranscript(specs);
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

  return {
    ...(spec_json_salvaged ? { spec_json_salvaged: true } : {}),
    grounded_spec: mergeGroundedSpec(specs),
    transcript,
    keyframes,
    concepts,
    requirements,
    code_snippets,
    architecture: mergeArchitecture(specs),
    artifacts,
    stack,
    visual_context: mergeVisualContext(specs),
    chapters,
    action_items,
  };
}
