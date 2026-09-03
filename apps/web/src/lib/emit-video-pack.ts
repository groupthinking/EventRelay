export interface EmittedVideoPack {
  version: string;
  id: string;
  video_id: string;
  source_url: string;
  provenance: { source_hash: string };
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
    },
  };
}

export function identityPackJson(pack: VideoPackCitation): string {
  return JSON.stringify(pack.pack, null, 2);
}

export async function emitVideoPack(url: string): Promise<VideoPackCitation> {
  const response = await fetch('/api/video/pack', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
    signal: AbortSignal.timeout(120_000),
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const envelope = asRecord(payload);
    const error = typeof envelope?.error === 'string' ? envelope.error : 'Video pack emit failed.';
    throw new Error(error);
  }
  return verifyIdentityPack(payload);
}
