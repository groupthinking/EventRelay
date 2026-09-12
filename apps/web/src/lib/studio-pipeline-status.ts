import type { VideoPackCitation } from '@/lib/emit-video-pack';
import {
  stackChecksFromPackTools,
  type ChecklistItem,
  type LinkedEntity,
} from '@/lib/linked-sop';
import type {
  VideoPackArchitecture,
  VideoPackArtifact,
  VideoPackStackTool,
} from '@/lib/video-pack-types';

export type StudioRunQuality = 'idle' | 'live' | 'draft';

export interface StudioPipelineCheck {
  ok: boolean;
  status: number;
  pipeline?: string;
  jobId?: string;
  message?: string;
}

const LIVE_PIPELINES = new Set(['backend-async', 'backend', 'gemini-only']);

/** Live means we have analysis payload, not that a kickoff returned a job id. */
export function studioRunQuality(
  check: StudioPipelineCheck | null,
  unsafe: boolean,
  hasVideo: boolean,
  payload?: { transcript?: string | null; eventCount?: number },
): StudioRunQuality {
  if (!hasVideo || unsafe) return 'draft';
  const transcript = payload?.transcript?.trim() ?? '';
  const events = payload?.eventCount ?? 0;
  if (transcript.length >= 40 || events > 0) return 'live';
  if (!check) return 'draft';
  if (check.jobId) return 'draft';
  if (check.ok && check.pipeline && LIVE_PIPELINES.has(check.pipeline)) return 'draft';
  return 'draft';
}

export function studioStatusLabel(
  quality: StudioRunQuality,
  runState: 'idle' | 'working' | 'ready',
): string {
  if (runState === 'working') return 'Working';
  if (runState === 'idle') return 'Idle';
  if (runState === 'ready' && quality === 'live') return 'Analysis ready';
  if (runState === 'ready') return 'No transcript yet';
  return 'Idle';
}

export function studioStatusMessage(
  quality: StudioRunQuality,
  runState: 'idle' | 'working' | 'ready',
  outcomeLabel: string,
  unsafe: boolean,
): string {
  if (unsafe) {
    return 'Safe alternative prepared. Harmful instructions stay out of the output.';
  }
  if (runState === 'working') {
    return `Analyzing the video — transcript and events will appear here.`;
  }
  if (runState === 'ready' && quality === 'live') {
    return `${outcomeLabel} ready. Act, export, or save from this same run.`;
  }
  if (runState === 'ready') {
    return `No usable transcript or events came back. Try another public video or sign in if the enrich path is gated.`;
  }
  return 'Paste a YouTube URL. UVAI transcribes it, extracts events, then you can act.';
}

export function studioPackCitation(pack: VideoPackCitation): string {
  return `cite:youtube:${pack.videoId} · ${pack.version} · ${pack.sourceHash} · ${pack.sourceUrl}`;
}

export function studioPackFormation(pack: VideoPackCitation | null | undefined): {
  tools: VideoPackStackTool[];
  checks: ChecklistItem[];
  architecture: VideoPackArchitecture | null;
  artifacts: VideoPackArtifact[];
} {
  const tools = pack?.pack.stack?.tools ?? [];
  return {
    tools,
    checks: stackChecksFromPackTools(tools),
    architecture: pack?.pack.architecture ?? null,
    artifacts: pack?.pack.artifacts ?? [],
  };
}

export function studioFormationSupplementalEntities(
  tools: VideoPackStackTool[] | null | undefined,
  entities: LinkedEntity[] | null | undefined,
): LinkedEntity[] {
  if ((tools?.length ?? 0) > 0) return [];
  return entities ?? [];
}

export function studioEventsEmptyMessage(input: {
  busy: boolean;
  hasCompletedRun: boolean;
  eventCount: number;
  hasTranscript?: boolean;
  hasArchitecture: boolean;
  artifactCount: number;
  toolCount: number;
}): string {
  if (input.eventCount > 0) return '';
  if (input.busy) return 'Extracting events…';
  if (!input.hasCompletedRun) return 'Events show up after Run.';
  const packReady =
    input.hasArchitecture || input.artifactCount > 0 || input.toolCount > 0;
  if (packReady) {
    return 'This pack has no extracted events. Architecture, artifacts, and stack from the video are below — export them from this page.';
  }
  if (input.hasTranscript) {
    return 'This run has no extracted events. Transcript and pack identity stay on this page.';
  }
  return 'This run has no extracted events. Pack identity stays on this page.';
}

export function studioPromotePackWorkbench(input: {
  eventCount: number;
  hasArchitecture: boolean;
  artifactCount: number;
  toolCount: number;
}): boolean {
  if (input.eventCount > 0) return false;
  return input.hasArchitecture || input.artifactCount > 0 || input.toolCount > 0;
}

export function studioCanExport(input: {
  transcript?: string | null;
  eventCount?: number;
  hasArchitecture?: boolean;
  artifactCount?: number;
  toolCount?: number;
  hasLinkedSopSteps?: boolean;
  hasProjectScaffold?: boolean;
}): boolean {
  const transcript = input.transcript?.trim() ?? '';
  return (
    transcript.length >= 40 ||
    (input.eventCount ?? 0) > 0 ||
    Boolean(input.hasArchitecture) ||
    (input.artifactCount ?? 0) > 0 ||
    (input.toolCount ?? 0) > 0 ||
    Boolean(input.hasLinkedSopSteps) ||
    Boolean(input.hasProjectScaffold)
  );
}

export function studioInvalidHandoffMessage(raw: string): string {
  const preview = raw.trim() || 'that input';
  return `Need a valid YouTube URL. "${preview}" is not a watchable video.`;
}

export function studioPasteOutcomeMessage(input: {
  hasUsableTranscript: boolean;
  packCitation?: string | null;
}): string {
  if (input.hasUsableTranscript) {
    return 'Ready — run tools, export, or save from this page.';
  }
  if (input.packCitation) {
    return `Identity pack ${input.packCitation}. No usable transcript.`;
  }
  return 'Pack emit failed: verification failed (source_url + source_hash required).';
}

export const STUDIO_PRODUCT_TAGLINE =
  'Paste a YouTube URL. UVAI builds a Video Pack you can export and act on.';

export const STUDIO_TRANSCRIPT_TYPICAL_SECONDS = 45;

export type StudioTranscriptStageId =
  | 'idle'
  | 'pack'
  | 'captions'
  | 'transcript'
  | 'events'
  | 'ready'
  | 'failed';

export function studioTranscriptStage(input: {
  busy: boolean;
  elapsedSeconds: number;
  progress?: number;
  hasPack?: boolean;
  hasTranscript?: boolean;
  hasFailed?: boolean;
}): { id: StudioTranscriptStageId; label: string } {
  if (input.hasFailed) {
    return { id: 'failed', label: 'Transcript failed' };
  }
  if (input.hasTranscript && !input.busy) {
    return { id: 'ready', label: 'Transcript ready' };
  }
  if (!input.busy) {
    return { id: 'idle', label: 'Waiting for a video' };
  }
  if (input.hasTranscript) {
    return { id: 'events', label: 'Extracting events' };
  }
  const progress = input.progress ?? 0;
  if (progress >= 10 || input.elapsedSeconds >= 18) {
    return { id: 'transcript', label: 'Building transcript' };
  }
  if (input.hasPack || progress >= 5 || input.elapsedSeconds >= 6) {
    return { id: 'captions', label: 'Fetching captions' };
  }
  return { id: 'pack', label: 'Pack identity' };
}

export function studioTranscriptEtaLabel(
  elapsedSeconds: number,
  typicalSeconds = STUDIO_TRANSCRIPT_TYPICAL_SECONDS,
): string {
  const remaining = Math.max(0, typicalSeconds - Math.max(0, elapsedSeconds));
  if (remaining === 0) {
    return 'Still working — typical run is about 45s';
  }
  return `About ${remaining}s left (typical ~45s)`;
}

export function studioCanRetryTranscript(input: {
  busy: boolean;
  hasFailed?: boolean;
  retryable?: boolean;
  elapsedSeconds?: number;
}): boolean {
  if (input.busy) {
    return (input.elapsedSeconds ?? 0) >= 90;
  }
  return Boolean(input.hasFailed && input.retryable !== false);
}

const STUDIO_IN_FLIGHT_DEPLOY_STATUSES = new Set(['pending', 'running', 'queued', 'in_progress']);

/** A real deploy receipt is a parseable https URL with a hostname. */
export function studioVerifiedLiveUrl(liveUrl?: string | null): string | null {
  const raw = liveUrl?.trim();
  if (!raw) return null;
  try {
    const parsed = new URL(raw);
    if (parsed.protocol !== 'https:') return null;
    if (!parsed.hostname || !/[a-z0-9]/i.test(parsed.hostname)) return null;
    return raw;
  } catch {
    return null;
  }
}

const PREFERRED_LIVE_HOST = /\.(vercel\.app|netlify\.app|fly\.dev)$/i;
const BARE_LIVE_HOST = /^(?:[a-z0-9-]+\.)+(?:vercel\.app|netlify\.app|fly\.dev)$/i;
const REJECTED_LIVE_HOST = /^(?:www\.)?(?:github\.com|vercel\.com)$/i;

function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return '';
  }
}

function asLiveRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

/** Pass through a backend-supplied hostname only — never invent one. */
function asBackendLiveCandidate(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const raw = value.trim();
  if (!raw) return null;
  const verified = studioVerifiedLiveUrl(raw);
  if (verified) return verified;
  if (BARE_LIVE_HOST.test(raw)) {
    return studioVerifiedLiveUrl(`https://${raw}`);
  }
  return null;
}

function collectLiveUrlCandidates(record: Record<string, unknown>): unknown[] {
  const deployment = asLiveRecord(record.deployment);
  const outputs = asLiveRecord(record.outputs);
  const result = asLiveRecord(record.result);
  const metadata = asLiveRecord(record.metadata);
  const data = asLiveRecord(record.data);
  const urls =
    asLiveRecord(deployment?.urls) ||
    asLiveRecord(record.urls) ||
    asLiveRecord(asLiveRecord(outputs?.deployment)?.urls);
  const summary = asLiveRecord(deployment?.summary) || asLiveRecord(record.summary);
  const summaryUrls = asLiveRecord(summary?.deployment_urls);
  const outDep = asLiveRecord(outputs?.deployment);
  return [
    record.live_url,
    data?.live_url,
    result?.live_url,
    metadata?.live_url,
    deployment?.live_url,
    deployment?.url,
    outDep?.live_url,
    outDep?.url,
    urls?.vercel,
    urls?.netlify,
    urls?.fly,
    deployment?.alias,
    record.alias,
    summary?.primary_url,
    ...(summaryUrls ? Object.values(summaryUrls) : []),
    ...(urls ? Object.values(urls) : []),
    ...(Array.isArray(deployment?.aliases) ? deployment.aliases : []),
    ...(Array.isArray(deployment?.automaticAliases) ? deployment.automaticAliases : []),
    ...(Array.isArray(record.aliases) ? record.aliases : []),
    record.url,
    data,
    result,
    metadata,
    deployment,
    outputs,
    outDep,
    urls,
    summary,
  ];
}

/**
 * Pass through a backend-supplied verified https hostname only — never invent one.
 * Prefer explicit live_url / vercel|netlify|fly hosts over a GitHub repo URL.
 */
export function extractBackendLiveUrl(...values: unknown[]): string | null {
  const preferred: string[] = [];
  const other: string[] = [];
  const queue: unknown[] = [...values];
  const seen = new Set<unknown>();
  while (queue.length) {
    const value = queue.shift();
    if (value == null || seen.has(value)) continue;
    if (typeof value === 'object') seen.add(value);
    const verified = asBackendLiveCandidate(value);
    if (verified) {
      const host = hostnameOf(verified);
      if (REJECTED_LIVE_HOST.test(host)) {
        continue;
      }
      if (PREFERRED_LIVE_HOST.test(host) || host.endsWith('.vercel.app')) {
        preferred.push(verified);
      } else if (host !== 'github.com' && host !== 'www.github.com') {
        other.push(verified);
      }
      continue;
    }
    const rec = asLiveRecord(value);
    if (rec) queue.push(...collectLiveUrlCandidates(rec));
  }
  return preferred[0] ?? other[0] ?? null;
}

/** A real deploy receipt is an https live URL. Workflow "completed" is not. */
export function studioHasDeployReceipt(liveUrl?: string | null): boolean {
  return studioVerifiedLiveUrl(liveUrl) !== null;
}

/** Receipts stay on the video that produced them. Switching videos or a malformed URL clears them. */
export function studioDeployReceiptForSelection(input: {
  selectedVideoId?: string | null;
  receiptVideoId?: string | null;
  liveUrl?: string | null;
}): string | null {
  if (!input.selectedVideoId || input.selectedVideoId !== input.receiptVideoId) {
    return null;
  }
  return studioVerifiedLiveUrl(input.liveUrl);
}

export const STUDIO_DEPLOY_ABORT_RETRY_MESSAGE =
  'Deploy kickoff timed out before a verified live URL. Waiting for the origin job — not aborting the attempt.';

/** Honest HOLD when kickoff abort/524 never returned a pollable job id. */
export const STUDIO_ORIGIN_KICKOFF_NO_JOB_HOLD =
  'Studio transcript was reused. Origin video-to-software kickoff returned no job id after the EventRelay wait budget.';

/** Honest HOLD after reuse — Origin/deploy finished and no backend-supplied https hostname. */
export const STUDIO_ORIGIN_NO_HOSTNAME_HOLD =
  'Studio transcript was reused. Origin deploy finished without a backend-supplied https hostname.';

/** Honest HOLD when the client poll budget ended while the WDK run is still running. */
export const STUDIO_ORIGIN_STILL_POLLABLE_HOLD =
  'Studio deploy run is still in progress after the EventRelay poll budget. Origin job remains pollable.';

/** Retired #1893 in-flight copy — must not be a terminal G.A.T.E. residual. */
export const STUDIO_DEPLOY_ATTEMPT_STARTED_HOLD =
  'Deploy attempt started. Waiting for a verified https live URL.';

export function isStudioDeployAbortTimeout(value: unknown): boolean {
  if (typeof value === 'string') {
    return /aborted due to timeout/i.test(value);
  }
  if (!value || typeof value !== 'object') return false;
  const rec = value as { name?: unknown; code?: unknown; message?: unknown };
  if (rec.name === 'TimeoutError') return true;
  if (rec.code === 23 || rec.code === 'TIMEOUT_ERR') return true;
  return typeof rec.message === 'string' && /aborted due to timeout/i.test(rec.message);
}

export function studioDeployOutcomeMessage(input: {
  liveUrl?: string | null;
  runStatus?: string | null;
  error?: string | null;
  kind?: string | null;
  message?: string | null;
  jobId?: string | null;
  jobStatus?: string | null;
}): string {
  const rawError = input.error?.trim();
  const error = rawError && isStudioDeployAbortTimeout(rawError)
    ? STUDIO_DEPLOY_ABORT_RETRY_MESSAGE
    : rawError;
  if (error) return error;
  const receipt = studioVerifiedLiveUrl(input.liveUrl);
  if (receipt) {
    return `Deploy receipt: ${receipt}`;
  }
  const jobId = input.jobId?.trim();
  const jobStatus = input.jobStatus?.trim();
  const terminalJob = new Set(['complete', 'completed', 'succeeded', 'failed', 'error', 'cancelled']);
  if (jobId && jobStatus && !terminalJob.has(jobStatus.toLowerCase())) {
    return `Deploy job ${jobId} still ${jobStatus}`;
  }
  const status = (input.runStatus || '').toLowerCase();
  if (STUDIO_IN_FLIGHT_DEPLOY_STATUSES.has(status)) {
    return `Deploy still ${status}. Waiting for a verified https live URL.`;
  }
  if (status === 'failed' || status === 'cancelled' || status === 'error') {
    return `Deploy ${status}. No verified live URL.`;
  }
  const detail = input.message?.trim();
  if ((input.kind === 'handoff' || input.kind === 'job') && detail) return detail;
  return 'Deploy attempt ended. No verified deploy receipt.';
}

export function studioDeployButtonLabel(_hasReceipt: boolean): string {
  return 'Attempt deploy';
}

export function studioDeployEnabledHint(hasReceipt: boolean): string {
  if (hasReceipt) return 'A live URL was returned. That is the receipt — not the enabled button.';
  return 'Starts an attempt. UNKNOWN checks are not a deploy receipt.';
}

export type StudioPlayerPhase = 'empty' | 'loading' | 'ready' | 'error';

export function studioPlayerPhase(input: {
  videoId?: string | null;
  loaded?: boolean;
  failed?: boolean;
  timedOut?: boolean;
}): StudioPlayerPhase {
  if (!input.videoId) return 'empty';
  if (input.failed) return 'error';
  if (input.loaded) return 'ready';
  if (input.timedOut) return 'error';
  return 'loading';
}

export function studioPlayerOverlay(phase: StudioPlayerPhase): string | null {
  if (phase === 'loading') return 'Loading video…';
  if (phase === 'error') return 'Video did not load. Retry or open on YouTube.';
  return null;
}

export type StudioExportToastKind = 'pack' | 'sop' | 'scaffold' | 'empty';

export function studioExportFilename(projectName?: string | null): string {
  const base = (projectName || 'uvai-project').trim() || 'uvai-project';
  return base.toLowerCase().endsWith('.zip') ? base : `${base}.zip`;
}

export function studioActionCard(action: {
  tool: string;
  status: string;
  result?: string;
}): {
  title: string;
  statusLabel: string;
  detail: string;
  kind: 'review' | 'tool';
} {
  const isReview = action.tool === 'review_action';
  const statusLabel =
    action.status === 'proposed'
      ? 'Needs review'
      : action.status === 'completed'
        ? 'Done'
        : action.status === 'failed'
          ? 'Failed'
          : action.status;
  const title = isReview
    ? 'Review this result'
    : action.tool
        .split('_')
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' ');
  const detail =
    action.result?.trim() ||
    (isReview ? 'Open the evidence on this page before you act.' : 'No detail from this tool.');
  return {
    title,
    statusLabel,
    detail,
    kind: isReview ? 'review' : 'tool',
  };
}

export function studioExportToastMessage(input: {
  ok: boolean;
  kind?: StudioExportToastKind;
  error?: string;
  filename?: string;
}): { tone: 'success' | 'error'; text: string } {
  const file = input.filename?.trim();
  const fileBit = file ? ` (${file})` : '';
  if (!input.ok || input.kind === 'empty') {
    return {
      tone: 'error',
      text: `${input.error || 'Export failed — nothing to export yet.'}${fileBit}`,
    };
  }
  if (input.kind === 'pack') {
    return { tone: 'success', text: `Pack exported${fileBit} — check your downloads.` };
  }
  if (input.kind === 'sop') {
    return {
      tone: 'success',
      text: `SOP and deploy files exported${fileBit} — check your downloads.`,
    };
  }
  return { tone: 'success', text: `Export downloaded${fileBit}.` };
}