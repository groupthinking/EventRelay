import { readPackFormation, type VideoPackArchitecture, type VideoPackArtifact, type VideoPackStack } from '@/lib/video-pack-types';

export interface EmittedVideoPack {
  version: string;
  id: string;
  video_id: string;
  source_url: string;
  provenance: { source_hash: string };
  architecture?: VideoPackArchitecture | null;
  artifacts?: VideoPackArtifact[];
  stack?: VideoPackStack;
}

export interface VideoPackCitation {
  version: string;
  videoId: string;
  packId: string;
  sourceUrl: string;
  sourceHash: string;
  pack: EmittedVideoPack;
}

const SOURCE_HASH = /^[a-f0-9]{64}$/;

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

export function verifyIdentityPack(payload: unknown): VideoPackCitation {
  const envelope = asRecord(payload);
  const data = asRecord(envelope?.data);
  const provenance = asRecord(data?.provenance);
  const sourceUrl = typeof data?.source_url === 'string' ? data.source_url.trim() : '';
  const sourceHash = typeof provenance?.source_hash === 'string' ? provenance.source_hash.trim() : '';
  const videoId = typeof data?.video_id === 'string' ? data.video_id : '';
  const version = typeof data?.version === 'string' ? data.version : '';
  const packId = typeof data?.id === 'string' ? data.id : '';

  if (
    envelope?.status !== 'success' ||
    version !== 'v0' ||
    !videoId ||
    !packId ||
    !sourceUrl.startsWith('http') ||
    !SOURCE_HASH.test(sourceHash)
  ) {
    throw new Error(
      'Video pack verification failed: source_url and source_hash are required.',
    );
  }

  const formation = data ? readPackFormation(data) : { architecture: null, artifacts: [], stack: { tools: [] } };

  return {
    version,
    videoId,
    packId,
    sourceUrl,
    sourceHash,
    pack: {
      version,
      id: packId,
      video_id: videoId,
      source_url: sourceUrl,
      provenance: { source_hash: sourceHash },
      ...(formation.architecture ? { architecture: formation.architecture } : {}),
      ...(formation.artifacts.length > 0 ? { artifacts: formation.artifacts } : {}),
      ...(formation.stack.tools.length > 0 ? { stack: formation.stack } : {}),
    },
  };
}

export function identityPackJson(pack: VideoPackCitation): string {
  return JSON.stringify(pack.pack, null, 2);
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function packErrorMessage(payload: unknown, fallback: string): string {
  const envelope = asRecord(payload);
  return typeof envelope?.error === 'string' ? envelope.error : fallback;
}

function processingQuery(payload: unknown, fallbackUrl: string): string {
  const envelope = asRecord(payload);
  const data = asRecord(envelope?.data);
  const provenance = asRecord(data?.provenance);
  const sourceHash = typeof provenance?.source_hash === 'string' ? provenance.source_hash.trim() : '';
  if (SOURCE_HASH.test(sourceHash)) {
    return `source_hash=${encodeURIComponent(sourceHash)}`;
  }
  const videoId = typeof data?.video_id === 'string' ? data.video_id : '';
  if (videoId) {
    return `video_id=${encodeURIComponent(videoId)}`;
  }
  return `url=${encodeURIComponent(fallbackUrl)}`;
}

async function pollReadyPack(
  payload: unknown,
  fallbackUrl: string,
  options: { pollIntervalMs: number; timeoutMs: number },
): Promise<VideoPackCitation> {
  const deadline = Date.now() + options.timeoutMs;
  const query = processingQuery(payload, fallbackUrl);
  while (Date.now() <= deadline) {
    if (options.pollIntervalMs > 0) {
      await delay(options.pollIntervalMs);
    }
    const response = await fetch(`/api/video/pack?${query}`, {
      method: 'GET',
      credentials: 'same-origin',
      signal: AbortSignal.timeout(15_000),
    });
    const next: unknown = await response.json().catch(() => null);
    if (response.status === 200) {
      return verifyIdentityPack(next);
    }
    if (response.status === 202) {
      continue;
    }
    throw new Error(packErrorMessage(next, 'Video pack emit failed.'));
  }
  throw new Error('Video pack emit timed out waiting for spec extract.');
}

export async function emitVideoPack(
  url: string,
  options: { pollIntervalMs?: number; timeoutMs?: number } = {},
): Promise<VideoPackCitation> {
  const pollIntervalMs = options.pollIntervalMs ?? 1_000;
  const timeoutMs = options.timeoutMs ?? 120_000;
  const response = await fetch('/api/video/pack', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
    signal: AbortSignal.timeout(15_000),
  });
  const payload: unknown = await response.json().catch(() => null);
  if (response.status === 200) {
    return verifyIdentityPack(payload);
  }
  if (response.status === 202) {
    return pollReadyPack(payload, url, { pollIntervalMs, timeoutMs });
  }
  throw new Error(packErrorMessage(payload, 'Video pack emit failed.'));
}
