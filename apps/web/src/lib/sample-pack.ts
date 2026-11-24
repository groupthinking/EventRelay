import samplePackEnvelope from '@/lib/sample-pack/auJzb1D-fag.pack.json';
import { verifyIdentityPack, type EmittedVideoPack, type VideoPackCitation } from '@/lib/emit-video-pack';
import { studioPackExtractedEvents } from '@/lib/studio-pipeline-status';
import type { ExtractedEvent } from '@/lib/types';
import type { Video } from '@/store/dashboard-types';

export const SAMPLE_VIDEO_ID = 'auJzb1D-fag';
export const SAMPLE_WATCH_URL = `https://www.youtube.com/watch?v=${SAMPLE_VIDEO_ID}`;
export const SAMPLE_LABEL = 'Cached sample · replayed in pipeline order';
/** When the bundled pack was produced by the live extraction pipeline. */
export const SAMPLE_CAPTURED_AT = '2026-10-16T07:19:03.888Z';

const SAMPLE_FRAME_PREFIX = `/api/video/pack/frames/${SAMPLE_VIDEO_ID}/`;

export type SampleStageId =
  | 'identity'
  | 'transcript'
  | 'chapters'
  | 'keyframes'
  | 'events'
  | 'formation'
  | 'spec'
  | 'actions';

export interface SampleReplayStep {
  stage: SampleStageId;
  label: string;
  progress: number;
  pack: EmittedVideoPack;
}

/**
 * The bundled pack is the unmodified GET /api/video/pack response for the
 * fixture video. Keyframe stills are served from /public so the sample also
 * works offline and on previews without the Upstash pack store.
 */
function localizedEnvelope(): unknown {
  const envelope = structuredClone(samplePackEnvelope) as {
    data: { keyframes?: Array<{ image_path?: string | null }> };
  };
  for (const frame of envelope.data.keyframes ?? []) {
    if (frame.image_path?.startsWith(SAMPLE_FRAME_PREFIX)) {
      frame.image_path = `/sample-pack/${SAMPLE_VIDEO_ID}/${frame.image_path.slice(SAMPLE_FRAME_PREFIX.length)}.jpg`;
    }
  }
  return envelope;
}

export function loadSamplePack(): VideoPackCitation {
  return verifyIdentityPack(localizedEnvelope());
}

const TRANSCRIPT_CHUNKS = 4;

/**
 * Cumulative pack snapshots in the order the extraction pipeline produces
 * them. Each step only adds fields; no step invents data the pack lacks.
 */
export function sampleReplaySteps(citation: VideoPackCitation): SampleReplayStep[] {
  const full = citation.pack;
  const identity: EmittedVideoPack = {
    version: full.version,
    id: full.id,
    video_id: full.video_id,
    source_url: full.source_url,
    provenance: full.provenance,
  };
  const steps: SampleReplayStep[] = [
    { stage: 'identity', label: 'Pack identity verified', progress: 5, pack: identity },
  ];
  let current = identity;
  const push = (stage: SampleStageId, label: string, progress: number, patch: Partial<EmittedVideoPack>) => {
    current = { ...current, ...patch };
    steps.push({ stage, label, progress, pack: current });
  };

  const segments = full.transcript?.segments ?? [];
  if (full.transcript) {
    const size = Math.max(1, Math.ceil(segments.length / TRANSCRIPT_CHUNKS));
    for (let end = size; end < segments.length + size; end += size) {
      const slice = segments.slice(0, Math.min(end, segments.length));
      push('transcript', `Transcript ${slice.length}/${segments.length} segments`, 10 + Math.round((slice.length / Math.max(segments.length, 1)) * 30), {
        transcript: {
          language: full.transcript.language,
          full_text: slice.map((segment) => segment.text).join(' '),
          segments: slice,
        },
      });
    }
    if (segments.length === 0) {
      push('transcript', 'Transcript', 40, { transcript: full.transcript });
    }
  }
  if (full.chapters?.length) push('chapters', `${full.chapters.length} chapters`, 50, { chapters: full.chapters });
  if (full.keyframes?.length) push('keyframes', `${full.keyframes.length} keyframes`, 60, { keyframes: full.keyframes });
  if (full.visual_context) push('events', `${full.visual_context.visual_elements.length} visual events`, 70, { visual_context: full.visual_context });
  push('formation', 'Requirements, stack and architecture', 80, {
    ...(full.requirements ? { requirements: full.requirements } : {}),
    ...(full.stack ? { stack: full.stack } : {}),
    ...(full.architecture ? { architecture: full.architecture } : {}),
    ...(full.artifacts ? { artifacts: full.artifacts } : {}),
    ...(full.code_snippets ? { code_snippets: full.code_snippets } : {}),
  });
  if (full.grounded_spec) push('spec', 'Grounded spec, tasks and checks', 90, { grounded_spec: full.grounded_spec });
  if (full.action_items?.length) push('actions', `${full.action_items.length} action items`, 95, { action_items: full.action_items });
  // Guarantee the final snapshot is exactly the verified pack.
  steps[steps.length - 1] = { ...steps[steps.length - 1], pack: full };
  return steps;
}

export function sampleEvents(pack: EmittedVideoPack, _recordId: string): ExtractedEvent[] {
  return studioPackExtractedEvents(pack);
}

export function sampleCompletionPatch(citation: VideoPackCitation, recordId: string): Partial<Video> {
  const pack = citation.pack;
  const firstChapter = pack.chapters?.[0]?.topic;
  return {
    status: 'complete',
    progress: 100,
    title: firstChapter ? `Sample · ${firstChapter}` : `Sample · ${citation.videoId}`,
    processedAt: new Date().toISOString(),
    transcript: pack.transcript?.full_text,
    events: sampleEvents(pack, recordId),
    videoPack: citation,
    insights: {
      summary: pack.architecture?.summary ?? '',
      actions: (pack.action_items ?? []).map((item) => ({
        title: item.title,
        description: item.description,
        category: item.type ?? 'recommended',
      })),
      sentiment: 'Unscored',
      topics: (pack.chapters ?? []).map((chapter) => chapter.topic),
    },
  };
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  signal?.throwIfAborted();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(signal?.reason);
    };
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

/**
 * Replays the cached sample into the store one pipeline stage at a time.
 * Display pacing only: every value comes from the bundled real pack.
 */
export async function replaySamplePack({
  recordId,
  citation,
  apply,
  stepDelayMs = 650,
  signal,
}: {
  recordId: string;
  citation: VideoPackCitation;
  apply: (patch: Partial<Video>) => void;
  stepDelayMs?: number;
  signal?: AbortSignal;
}): Promise<void> {
  for (const step of sampleReplaySteps(citation)) {
    await wait(stepDelayMs, signal);
    apply({
      status: 'processing',
      failure: undefined,
      progress: step.progress,
      videoPack: { ...citation, pack: step.pack },
      transcript: step.pack.transcript?.full_text,
    });
  }
  await wait(stepDelayMs, signal);
  apply(sampleCompletionPatch(citation, recordId));
}
