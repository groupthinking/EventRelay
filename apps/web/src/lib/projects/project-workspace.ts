import type { EmittedVideoPack } from '@/lib/emit-video-pack';
import { studioPackExtractedEvents } from '@/lib/studio-pipeline-status';
import { formatSeconds, parseTimestampToSeconds, parseTranscriptSegments } from '@/lib/timestamp';
import { resolveCaptionSourceLabel, type CaptionSourceLabel } from '@/lib/transcript-export';
import type { ProjectRecord } from './project-types';

/** Deterministic, client-safe Project workspace helpers. Nothing here invents pack content. */

export const PROJECT_VIEWS = ['brief', 'run', 'elements', 'canvas'] as const;
export type ProjectView = (typeof PROJECT_VIEWS)[number];

export function parseProjectView(raw: string | null | undefined): ProjectView {
  return (PROJECT_VIEWS as readonly string[]).includes(raw ?? '') ? (raw as ProjectView) : 'brief';
}

/** Whole non-negative seconds, or null. */
export function parseProjectTime(raw: string | null | undefined): number | null {
  if (raw == null || !/^\d{1,7}$/.test(raw.trim())) return null;
  return Number(raw.trim());
}

export interface TranscriptRow {
  idx: number;
  start: number;
  duration: number;
  text: string;
}

const IDENTITY_STUB = /^cite:youtube:/i;

export function packHasTranscriptText(pack: EmittedVideoPack | null | undefined): boolean {
  const text = pack?.transcript?.full_text?.trim() ?? '';
  return text.length > 0 && !IDENTITY_STUB.test(text);
}

/** Real timed rows only: pack segments first, then timestamped full_text. Never synthesizes timings. */
export function resolvePackTranscriptSegments(pack: EmittedVideoPack | null | undefined): TranscriptRow[] {
  if (!pack) return [];
  const segments = pack.transcript?.segments ?? [];
  if (segments.length > 0) {
    return segments
      .filter((seg) => typeof seg.text === 'string' && seg.text.trim())
      .map((seg, index) => ({
        idx: typeof seg.idx === 'number' ? seg.idx : index,
        start: Math.max(0, seg.start_s),
        duration: Math.max(1, seg.end_s - seg.start_s),
        text: seg.text.trim(),
      }));
  }
  if (!packHasTranscriptText(pack)) return [];
  const parsed = parseTranscriptSegments(pack.transcript?.full_text);
  if (!parsed.hasTimings) return [];
  return parsed.segments.map((seg, index) => ({
    idx: index,
    start: Math.max(0, seg.startTime),
    duration: Math.max(1, seg.endTime - seg.startTime),
    text: seg.text,
  }));
}

export interface ProjectFolder {
  id: string;
  label: string;
  topic: string;
  start: number | null;
  end: number | null;
  /** The last chapter includes its end second; earlier ones stop before the next chapter. */
  inclusiveEnd: boolean;
  keyframeCount: number;
  eventCount: number;
  /** Tasks carry no timestamps in the pack, so only the "all" folder reports them. */
  taskCount: number | null;
  assetCount: number;
}

export function folderContains(folder: ProjectFolder | null | undefined, seconds: number): boolean {
  if (!folder || folder.start == null || folder.end == null) return true;
  if (seconds < folder.start) return false;
  return folder.inclusiveEnd ? seconds <= folder.end : seconds < folder.end;
}

export function buildProjectFolders(pack: EmittedVideoPack | null | undefined): ProjectFolder[] {
  const keyframes = pack?.keyframes ?? [];
  const events = studioPackExtractedEvents(pack);
  const requirements = pack?.requirements ?? [];
  const actionItems = pack?.action_items ?? [];
  const taskCount = requirements.length + actionItems.length;

  const all: ProjectFolder = {
    id: 'all',
    label: 'All assets',
    topic: 'All extracted assets',
    start: null,
    end: null,
    inclusiveEnd: true,
    keyframeCount: keyframes.length,
    eventCount: events.length,
    taskCount,
    assetCount: keyframes.length + events.length + taskCount,
  };

  const chapters = pack?.chapters ?? [];
  const folders = chapters.map((chapter, index): ProjectFolder => {
    const folder: ProjectFolder = {
      id: `ch-${index + 1}`,
      label: `CH${index + 1}`,
      topic: chapter.topic,
      start: chapter.start,
      end: chapter.end,
      inclusiveEnd: index === chapters.length - 1,
      keyframeCount: 0,
      eventCount: 0,
      taskCount: null,
      assetCount: 0,
    };
    folder.keyframeCount = keyframes.filter((frame) => folderContains(folder, frame.t_s)).length;
    folder.eventCount = events.filter((event) => {
      const t = parseTimestampToSeconds(event.timestamp);
      return t != null && folderContains(folder, t);
    }).length;
    folder.assetCount = folder.keyframeCount + folder.eventCount;
    return folder;
  });
  return [all, ...folders];
}

export function resolveProjectFolder(folders: readonly ProjectFolder[], id: string | null | undefined): ProjectFolder {
  return folders.find((folder) => folder.id === id) ?? folders[0];
}

export function filterTranscriptRows(
  rows: readonly TranscriptRow[],
  folder: ProjectFolder | null | undefined,
  query: string,
): TranscriptRow[] {
  const needle = query.trim().toLowerCase();
  return rows.filter(
    (row) => folderContains(folder, row.start) && (!needle || row.text.toLowerCase().includes(needle)),
  );
}

export function formatTranscriptJson(rows: readonly TranscriptRow[], videoId: string): string {
  return `${JSON.stringify(
    {
      video_id: videoId,
      segments: rows.map((row) => ({ start_s: row.start, end_s: row.start + row.duration, text: row.text })),
    },
    null,
    2,
  )}\n`;
}

export function formatTranscriptMarkdown(rows: readonly TranscriptRow[], title: string, sourceUrl: string): string {
  const lines = [`# ${title}`, '', `Source: ${sourceUrl}`, ''];
  for (const row of rows) lines.push(`- **[${formatSeconds(row.start)}]** ${row.text}`);
  return `${lines.join('\n')}\n`;
}

export interface ProjectBrief {
  title: string;
  videoId: string;
  sourceUrl: string;
  sourceHash: string;
  hasPack: boolean;
  summary: string | null;
  chapters: Array<{ number: number; start: number; end: number; topic: string; keyPoints: string[] }>;
  stack: Array<{ name: string; kind: string | null; evidence: string | null }>;
  actionItems: Array<{ title: string; description: string; priority: string | null }>;
  openQuestions: string[];
  captionSource: CaptionSourceLabel;
}

export function buildProjectBrief(
  project: Pick<ProjectRecord, 'title' | 'videoId' | 'sourceUrl' | 'sourceHash'>,
  pack: EmittedVideoPack | null | undefined,
): ProjectBrief {
  const rows = resolvePackTranscriptSegments(pack);
  const stack = (pack?.stack?.tools ?? []).flatMap((tool) => {
    const name = tool.name?.trim();
    return name ? [{ name, kind: tool.kind?.trim() || null, evidence: tool.evidence?.trim() || null }] : [];
  });
  const openQuestions: string[] = [];
  if (pack) {
    if ((pack.chapters ?? []).length === 0) openQuestions.push('No chapters were extracted for this video.');
    if (rows.length === 0) openQuestions.push('No timed captions are available, so timestamps cannot be verified.');
    for (const tool of stack) {
      if (!tool.evidence) openQuestions.push(`No evidence was captured for ${tool.name}.`);
    }
  }
  return {
    title: project.title,
    videoId: project.videoId,
    sourceUrl: project.sourceUrl,
    sourceHash: pack?.provenance?.source_hash || project.sourceHash || '',
    hasPack: Boolean(pack),
    summary: pack?.architecture?.summary?.trim() || pack?.visual_context?.summary?.trim() || null,
    chapters: (pack?.chapters ?? []).map((chapter, index) => ({
      number: index + 1,
      start: chapter.start,
      end: chapter.end,
      topic: chapter.topic,
      keyPoints: chapter.key_points ?? [],
    })),
    stack,
    actionItems: (pack?.action_items ?? []).map((item) => ({
      title: item.title,
      description: item.description,
      priority: item.priority ?? null,
    })),
    openQuestions,
    captionSource: resolveCaptionSourceLabel({
      timedSegmentCount: rows.length,
      hasTranscriptText: packHasTranscriptText(pack),
    }),
  };
}

export function formatProjectBriefMarkdown(brief: ProjectBrief): string {
  const lines: string[] = [`# ${brief.title}`, '', `- Source: ${brief.sourceUrl}`, `- Video ID: ${brief.videoId}`];
  if (brief.sourceHash) lines.push(`- Source hash: ${brief.sourceHash}`);
  lines.push(`- Captions: ${brief.captionSource}`, '');

  lines.push('## Summary', '', brief.summary ?? '_No summary was extracted._', '');

  lines.push('## Chapters', '');
  if (brief.chapters.length === 0) lines.push('_No chapters were extracted._');
  for (const chapter of brief.chapters) {
    lines.push(`${chapter.number}. [${formatSeconds(chapter.start)}–${formatSeconds(chapter.end)}] ${chapter.topic}`);
    for (const point of chapter.keyPoints) lines.push(`   - ${point}`);
  }
  lines.push('');

  lines.push('## Detected stack', '');
  if (brief.stack.length === 0) lines.push('_No tools were detected._');
  for (const tool of brief.stack) {
    const meta = [tool.kind, tool.evidence].filter(Boolean).join(' — ');
    lines.push(`- ${tool.name}${meta ? ` (${meta})` : ''}`);
  }
  lines.push('');

  lines.push('## Action items', '');
  if (brief.actionItems.length === 0) lines.push('_No action items were extracted._');
  for (const item of brief.actionItems) {
    lines.push(`- **${item.title}**${item.priority ? ` [${item.priority}]` : ''}: ${item.description}`);
  }
  lines.push('');

  lines.push('## Open questions', '');
  if (brief.openQuestions.length === 0) lines.push('_None recorded._');
  for (const question of brief.openQuestions) lines.push(`- ${question}`);

  return `${lines.join('\n')}\n`;
}
