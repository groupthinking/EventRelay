import { hostedSpecLivePath } from '@/lib/compiled-spec-host';
import { resolveYouTubeVideoId } from '@/lib/video-pack';
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

/** YouTube id for `/d/{videoId}` — must come from the pack citation, not the dashboard row UUID. */
export function resolvePackBuildLiveVideoId(input: {
  packVideoId?: string | null;
  watchUrl?: string | null;
}): string | null {
  const fromPack = input.packVideoId?.trim() ?? '';
  if (fromPack && resolveYouTubeVideoId(fromPack)) {
    return fromPack;
  }
  const fromUrl = input.watchUrl?.trim() ? resolveYouTubeVideoId(input.watchUrl) : null;
  if (fromUrl) return fromUrl;
  return fromPack || null;
}

type StoredPackConfirmation = { ok: true; videoId: string } | { ok: false };

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
}): Promise<StoredPackConfirmation> {
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
    return { ok: false };
  }
  try {
    const payload = (await response.json()) as {
      status?: string;
      data?: { videoId?: string; video_id?: string };
    };
    if (payload.status !== 'success') {
      return { ok: false };
    }
    const fromSandbox =
      (typeof payload.data?.videoId === 'string' ? payload.data.videoId.trim() : '') ||
      (typeof payload.data?.video_id === 'string' ? payload.data.video_id.trim() : '');
    const videoId = fromSandbox || input.videoId.trim();
    if (!videoId) {
      return { ok: false };
    }
    return { ok: true, videoId };
  } catch {
    return { ok: false };
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
  if (!packBuildLiveUrl(origin, videoId)) {
    return { ok: false, message: 'Could not resolve a hosted live URL for this video.' };
  }

  const signal = input.signal ?? AbortSignal.timeout(20_000);

  const fetchHealth = async (
    hostVideoId: string,
  ): Promise<{ response: Response; payload: PackBuildLiveHealthPayload }> => {
    const response = await fetch(`${packBuildLivePath(hostVideoId)}/health`, {
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

  let hostVideoId = videoId;
  let { response, payload } = await fetchHealth(hostVideoId);

  if (payload.health?.ok !== true) {
    const shouldConfirmStoredPack =
      Boolean(input.sourceHash?.trim()) ||
      response.status === 404 ||
      payload.health?.reason_code === 'HOSTED_PACK_NOT_FOUND' ||
      !response.ok;
    if (shouldConfirmStoredPack && (input.sourceHash || videoId)) {
      const confirmed = await confirmStoredPackOnServer({
        videoId,
        sourceHash: input.sourceHash,
        signal,
      });
      if (confirmed.ok) {
        hostVideoId = confirmed.videoId;
        ({ response, payload } = await fetchHealth(hostVideoId));
        if (payload.health?.ok !== true) {
          const liveUrl = packBuildLiveUrl(origin, hostVideoId);
          if (liveUrl) {
            return {
              ok: true,
              liveUrl,
              reasonCode: payload.factory_deliver?.reason_code ?? 'FACTORY_DELIVER_READY',
            };
          }
        }
      }
    }
  }

  if (!response.ok || payload.health?.ok !== true) {
    return { ok: false, message: healthFailureMessage(payload, response.status) };
  }

  const liveUrl = packBuildLiveUrl(origin, hostVideoId);
  if (!liveUrl) {
    return { ok: false, message: 'Could not resolve a hosted live URL for this video.' };
  }
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
