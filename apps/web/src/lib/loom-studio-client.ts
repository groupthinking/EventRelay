export type LoomProBuildResponse = {
  ok: true;
  loomId: string;
  shareUrl: string;
  transcript: string;
  duration: number;
  answer: string;
  provider: 'xai';
  model: string;
  sttModel: string;
  audioSource: string;
  plan: 'pro';
};

function isBuildResponse(value: unknown): value is LoomProBuildResponse {
  if (!value || typeof value !== 'object') return false;
  const record = value as Partial<LoomProBuildResponse>;
  return (
    record.ok === true
    && record.provider === 'xai'
    && typeof record.transcript === 'string'
    && record.transcript.trim().length > 0
    && typeof record.duration === 'number'
    && record.duration > 0
    && typeof record.answer === 'string'
    && record.answer.trim().length > 0
    && typeof record.shareUrl === 'string'
    && typeof record.loomId === 'string'
  );
}

/**
 * Studio client for POST /api/loom/build. Pro session is enforced on the server.
 */
export async function requestLoomProBuild(shareUrl: string): Promise<LoomProBuildResponse> {
  const response = await fetch('/api/loom/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: shareUrl }),
    signal: AbortSignal.timeout(300_000),
  });
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch (err) {
    console.error('loom build response was not JSON', err);
  }
  if (!response.ok || !isBuildResponse(payload)) {
    const message = payload && typeof payload === 'object' && 'error' in payload
      && typeof (payload as { error?: unknown }).error === 'string'
      ? (payload as { error: string }).error
      : 'Loom build failed.';
    throw new Error(message);
  }
  return payload;
}
