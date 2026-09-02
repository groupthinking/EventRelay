export interface VideoPackCitation {
  version: string;
  videoId: string;
  packId: string;
  sourceHash: string;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

export async function emitVideoPack(url: string): Promise<VideoPackCitation> {
  const response = await fetch('/api/video/pack', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
    signal: AbortSignal.timeout(15_000),
  });
  const payload = asRecord(await response.json().catch(() => null));
  const data = asRecord(payload?.data);
  const provenance = asRecord(data?.provenance);
  const sourceHash = typeof provenance?.source_hash === 'string' ? provenance.source_hash : '';
  const videoId = typeof data?.video_id === 'string' ? data.video_id : '';
  const version = typeof data?.version === 'string' ? data.version : '';
  const packId = typeof data?.id === 'string' ? data.id : '';

  if (!response.ok || payload?.status !== 'success' || !sourceHash || !videoId || version !== 'v0') {
    const error = typeof payload?.error === 'string' ? payload.error : 'Video pack emit failed.';
    throw new Error(error);
  }

  return { version, videoId, packId, sourceHash };
}
