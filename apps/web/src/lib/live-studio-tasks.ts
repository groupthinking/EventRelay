import { inspectGroundedSpec } from '@/lib/grounded-build-spec';
import { projectStudioBoundTasks } from '@/lib/studio-bound-tasks';
import type { EmittedVideoPack } from '@/lib/emit-video-pack';
import type { VideoPackKeyframe } from '@/lib/video-pack';
import type { VideoPackActionItem, VideoPackChapter, VideoPackStackTool } from '@/lib/video-pack-types';

export const LIVE_TASK_OWNERS = ['builder', 'researcher', 'prompt', 'qa'] as const;
export type LiveTaskOwner = (typeof LIVE_TASK_OWNERS)[number];

export const LIVE_TASK_OWNER_LABELS: Record<LiveTaskOwner, string> = {
  builder: 'Builder agent',
  researcher: 'Research agent',
  prompt: 'Prompt agent',
  qa: 'QA agent',
};

export interface LiveTaskSource {
  startSeconds: number;
  endSeconds: number;
  /** `cited` comes from the grounded spec; `chapter-match` is a heuristic binding. */
  basis: 'cited' | 'chapter-match';
  quote: string | null;
  label: string;
}

export interface LiveTask {
  id: string;
  origin: 'grounded-spec' | 'action-item';
  title: string;
  spec: string;
  check: string;
  owner: LiveTaskOwner;
  source: LiveTaskSource | null;
  keyframe: VideoPackKeyframe | null;
  edited: boolean;
}

export interface LiveTaskEdit {
  title?: string;
  spec?: string;
  check?: string;
  owner?: LiveTaskOwner;
}

export type LiveTaskEdits = Record<string, LiveTaskEdit>;

export function isLiveTaskOwner(value: unknown): value is LiveTaskOwner {
  return typeof value === 'string' && (LIVE_TASK_OWNERS as readonly string[]).includes(value);
}

const OWNER_BY_ACTION_TYPE: Record<string, LiveTaskOwner> = {
  explore: 'researcher',
  research: 'researcher',
  read: 'researcher',
  prompt: 'prompt',
  prototype: 'builder',
  build: 'builder',
  implement: 'builder',
  setup: 'builder',
  test: 'qa',
  verify: 'qa',
};

export function inferOwner(text: string, actionType?: string | null): LiveTaskOwner {
  const mapped = actionType ? OWNER_BY_ACTION_TYPE[actionType.toLowerCase()] : undefined;
  if (mapped) return mapped;
  if (/\b(prompt|query|ask)\b/i.test(text)) return 'prompt';
  if (/\b(test|verify|validate|assert)\b/i.test(text)) return 'qa';
  if (/\b(research|explore|investigate|compare)\b/i.test(text)) return 'researcher';
  return 'builder';
}

export function formatTimestamp(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = h > 0 ? String(m).padStart(2, '0') : String(m);
  return `${h > 0 ? `${h}:` : ''}${mm}:${String(s).padStart(2, '0')}`;
}

export function nearestKeyframe(keyframes: readonly VideoPackKeyframe[] | undefined, seconds: number): VideoPackKeyframe | null {
  let best: VideoPackKeyframe | null = null;
  for (const frame of keyframes ?? []) {
    if (!best || Math.abs(frame.t_s - seconds) < Math.abs(best.t_s - seconds)) best = frame;
  }
  return best;
}

const STOPWORDS = new Set(['the', 'and', 'for', 'with', 'into', 'from', 'that', 'this', 'your', 'click', 'select', 'video', 'review']);

function tokens(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((word) => word.length > 3 && !STOPWORDS.has(word)),
  );
}

export function bestChapterMatch(
  chapters: readonly VideoPackChapter[] | undefined,
  text: string,
): { chapter: VideoPackChapter; index: number } | null {
  const wanted = tokens(text);
  let best: { chapter: VideoPackChapter; index: number } | null = null;
  let bestScore = 0;
  const list = chapters ?? [];
  for (let index = 0; index < list.length; index += 1) {
    const chapter = list[index];
    const have = tokens(`${chapter.topic} ${chapter.key_points.join(' ')}`);
    let score = 0;
    for (const word of wanted) if (have.has(word)) score += 1;
    if (score > bestScore) {
      best = { chapter, index };
      bestScore = score;
    }
  }
  return best;
}

function matchingToolCheck(tools: readonly VideoPackStackTool[] | undefined, text: string): string {
  const haystack = text.toLowerCase();
  const tool = (tools ?? []).find((item) => item.check && haystack.includes(item.name.toLowerCase()));
  return tool?.check ?? '';
}

function groundedTasks(pack: EmittedVideoPack): LiveTask[] {
  const view = projectStudioBoundTasks(inspectGroundedSpec(pack));
  if (view.status !== 'available') return [];
  return view.tasks.map((task) => {
    const citation = task.citations.find((item) => item.kind === 'transcript') ?? task.citations[0];
    const source: LiveTaskSource | null = citation
      ? {
          startSeconds: citation.startSeconds,
          endSeconds: citation.endSeconds,
          basis: 'cited',
          quote: citation.quote,
          label: `${citation.kind === 'transcript' ? 'Transcript' : 'Visual'} #${citation.index}`,
        }
      : null;
    return {
      id: task.id,
      origin: 'grounded-spec',
      title: task.title,
      spec: task.detail,
      check: task.checks.map((check) => `Given ${check.given}, when ${check.when}, then ${check.then}.`).join('\n'),
      owner: inferOwner(`${task.title} ${task.detail}`),
      source,
      keyframe: source ? nearestKeyframe(pack.keyframes, source.startSeconds) : null,
      edited: false,
    };
  });
}

function actionTask(pack: EmittedVideoPack, item: VideoPackActionItem): LiveTask {
  const text = `${item.title} ${item.description}`;
  const match = bestChapterMatch(pack.chapters, text);
  const source: LiveTaskSource | null = match
    ? {
        startSeconds: match.chapter.start,
        endSeconds: match.chapter.end,
        basis: 'chapter-match',
        quote: null,
        label: `Chapter ${match.index + 1} · ${match.chapter.topic}`,
      }
    : null;
  return {
    id: item.id,
    origin: 'action-item',
    title: item.title,
    spec: item.description,
    check: matchingToolCheck(pack.stack?.tools, text),
    owner: inferOwner(text, item.type),
    source,
    keyframe: source ? nearestKeyframe(pack.keyframes, source.startSeconds) : null,
    edited: false,
  };
}

/** Grounded-spec requirements first (cited), then pack action items (chapter-matched). */
export function deriveLiveTasks(pack: EmittedVideoPack | undefined): LiveTask[] {
  if (!pack) return [];
  return [...groundedTasks(pack), ...(pack.action_items ?? []).map((item) => actionTask(pack, item))];
}

export function applyTaskEdits(tasks: readonly LiveTask[], edits: LiveTaskEdits | undefined): LiveTask[] {
  if (!edits) return [...tasks];
  return tasks.map((task) => {
    const edit = edits[task.id];
    if (!edit) return task;
    return {
      ...task,
      title: edit.title ?? task.title,
      spec: edit.spec ?? task.spec,
      check: edit.check ?? task.check,
      owner: edit.owner ?? task.owner,
      edited: true,
    };
  });
}

/**
 * Store only fields that differ from the derived task. A blank title keeps the
 * derived title so a task never loses its name. Returns null when nothing changed.
 */
export function normalizeTaskEdit(base: LiveTask, draft: LiveTaskEdit): LiveTaskEdit | null {
  const edit: LiveTaskEdit = {};
  const title = draft.title?.trim();
  if (title && title !== base.title) edit.title = title;
  const spec = draft.spec?.trim();
  if (spec !== undefined && spec !== base.spec) edit.spec = spec;
  const check = draft.check?.trim();
  if (check !== undefined && check !== base.check) edit.check = check;
  if (draft.owner && draft.owner !== base.owner) edit.owner = draft.owner;
  return Object.keys(edit).length > 0 ? edit : null;
}

export function sourceWatchUrl(videoId: string, seconds: number): string {
  const url = new URL('https://www.youtube.com/watch');
  url.searchParams.set('v', videoId);
  url.searchParams.set('t', `${Math.floor(seconds)}s`);
  return url.toString();
}

export interface LiveDispatchRequest {
  job_id?: string;
  events: Array<{
    id: string;
    type: 'action';
    title: string;
    description: string;
    timestamp?: string;
    owner_agent: LiveTaskOwner;
    source_url?: string;
    timestamp_basis?: LiveTaskSource['basis'];
  }>;
  transcript?: string;
  agent_types: LiveTaskOwner[];
}

export function buildDispatchRequest({
  tasks,
  videoId,
  jobId,
  transcript,
}: {
  tasks: readonly LiveTask[];
  videoId: string | null;
  jobId?: string;
  transcript?: string;
}): LiveDispatchRequest {
  return {
    ...(jobId ? { job_id: jobId } : {}),
    events: tasks.map((task) => ({
      id: task.id,
      type: 'action',
      title: task.title,
      description: task.check ? `${task.spec}\n\nCheck: ${task.check}` : task.spec,
      owner_agent: task.owner,
      ...(task.source
        ? {
            timestamp: formatTimestamp(task.source.startSeconds),
            timestamp_basis: task.source.basis,
            ...(videoId ? { source_url: sourceWatchUrl(videoId, task.source.startSeconds) } : {}),
          }
        : {}),
    })),
    ...(transcript?.trim() ? { transcript } : {}),
    agent_types: Array.from(new Set(tasks.map((task) => task.owner))),
  };
}
