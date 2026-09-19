import { hostedSpecLivePath } from '@/lib/compiled-spec-host';
import { studioVerifiedLiveUrl } from '@/lib/studio-pipeline-status';

export const PACK_BUILD_LIVE_CUT = 'pack→App Builder build→hosted live URL' as const;

export function packBuildLivePath(videoId: string): string {
  return hostedSpecLivePath(videoId);
}

/** Absolute https URL for the compiled pack viewer on this deployment. */
export function packBuildLiveUrl(origin: string, videoId: string): string | null {
  const id = videoId.trim();
  if (!id) return null;
  try {
    const absolute = new URL(packBuildLivePath(id), origin.endsWith('/') ? origin : `${origin}/`);
    return studioVerifiedLiveUrl(absolute.href);
  } catch {
    return null;
  }
}

export type PackBuildLiveHealthPayload = {
  videoId?: string;
  live_url?: string;
  health?: { ok?: boolean; status?: number; detail?: string; reason_code?: string };
  factory_deliver?: { ready?: boolean; reason_code?: string };
  error?: string;
};

export type PackBuildLiveResult =
  | { ok: true; liveUrl: string; reasonCode: string }
  | { ok: false; message: string };

function healthFailureMessage(payload: PackBuildLiveHealthPayload, status: number): string {
  const detail = payload.health?.detail?.trim();
  if (detail) return detail;
  const error = payload.error?.trim();
  if (error) return error;
  const reason = payload.health?.reason_code;
  if (reason === 'HOSTED_PACK_NOT_FOUND') {
    return 'Video pack not found. Run analysis on this URL before Build live.';
  }
  if (reason === 'HOSTED_PACK_PROCESSING') {
    return 'Video pack is still processing. Try again when the pack is ready.';
  }
  if (status === 404) {
    return 'Video pack not found. Run analysis on this URL before Build live.';
  }
  if (status === 202) {
    return 'Video pack is still processing. Try again when the pack is ready.';
  }
  return `Hosted build health check failed (HTTP ${status}).`;
}

async function confirmStoredPackOnServer(input: {
  videoId: string;
  sourceHash?: string | null;
  signal?: AbortSignal;
}): Promise<boolean> {
  const sourceHash = input.sourceHash?.trim();
  const params = new URLSearchParams();
  if (sourceHash && /^[a-f0-9]{64}$/.test(sourceHash)) {
    params.set('source_hash', sourceHash);
  } else {
    params.set('video_id', input.videoId);
  }
  const response = await fetch(`/api/video/sandbox?${params.toString()}`, {
    method: 'GET',
    credentials: 'same-origin',
    signal: input.signal ?? AbortSignal.timeout(20_000),
  });
  if (!response.ok) {
    return false;
  }
  try {
    const payload = (await response.json()) as { status?: string };
    return payload.status === 'success';
  } catch {
    return false;
  }
}

/**
 * Compile-from-pack health probe at `/d/{videoId}/health`.
 * Does not start Origin studio.deploy or external provider deploy.
 */
export async function verifyPackBuildLive(input: {
  videoId: string;
  sourceHash?: string | null;
  origin?: string;
  signal?: AbortSignal;
}): Promise<PackBuildLiveResult> {
  const videoId = input.videoId.trim();
  if (!videoId) {
    return { ok: false, message: 'Analyze a video before Build live.' };
  }

  const origin =
    input.origin?.trim() ||
    (typeof window !== 'undefined' ? window.location.origin : 'https://uvai.io');
  const fallbackLive = packBuildLiveUrl(origin, videoId);
  if (!fallbackLive) {
    return { ok: false, message: 'Could not resolve a hosted live URL for this video.' };
  }

  const signal = input.signal ?? AbortSignal.timeout(20_000);

  const fetchHealth = async (): Promise<{ response: Response; payload: PackBuildLiveHealthPayload }> => {
    const response = await fetch(`${packBuildLivePath(videoId)}/health`, {
      method: 'GET',
      credentials: 'same-origin',
      signal,
    });
    let payload: PackBuildLiveHealthPayload = {};
    try {
      payload = (await response.json()) as PackBuildLiveHealthPayload;
    } catch {
      payload = {};
    }
    return { response, payload };
  };

  let { response, payload } = await fetchHealth();

  if (payload.health?.ok !== true) {
    const shouldRetry =
      !payload.health?.ok &&
      (response.status === 404 ||
        payload.health?.reason_code === 'HOSTED_PACK_NOT_FOUND' ||
        !response.ok);
    if (shouldRetry && (input.sourceHash || videoId)) {
      const confirmed = await confirmStoredPackOnServer({
        videoId,
        sourceHash: input.sourceHash,
        signal,
      });
      if (confirmed) {
        ({ response, payload } = await fetchHealth());
      }
    }
  }

  if (!response.ok || payload.health?.ok !== true) {
    return { ok: false, message: healthFailureMessage(payload, response.status) };
  }

  const liveUrl = fallbackLive;
  const reasonCode = payload.factory_deliver?.reason_code ?? 'FACTORY_DELIVER_READY';

  return { ok: true, liveUrl, reasonCode };
}

export function packBuildLiveOutcomeMessage(result: PackBuildLiveResult): string {
  if (result.ok) {
    return `Built from Video Pack. Open the hosted app: ${result.liveUrl}`;
  }
  return result.message;
}

export function studioPackLiveReceiptForSelection(input: {
  selectedVideoId?: string | null;
  receiptVideoId?: string | null;
  liveUrl?: string | null;
}): string | null {
  if (!input.selectedVideoId || input.selectedVideoId !== input.receiptVideoId) {
    return null;
  }
  return studioVerifiedLiveUrl(input.liveUrl);
}
