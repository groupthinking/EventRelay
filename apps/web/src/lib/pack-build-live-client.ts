/**
 * Client-safe Build live helpers (fetch + URL resolution only).
 * Do not import video-pack, extractors, or other server-only modules here.
 */
import { hostedSpecLivePath } from '@/lib/hosted-spec-paths';
import { extractYouTubeId } from '@/lib/timestamp';

export const PACK_BUILD_LIVE_CUT = 'pack→App Builder build→hosted live URL' as const;

export function packBuildLivePath(videoId: string): string {
  return hostedSpecLivePath(videoId);
}

function verifiedHttpsLiveUrl(liveUrl?: string | null): string | null {
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

/** Absolute https URL for the compiled pack viewer on this deployment. */
export function packBuildLiveUrl(origin: string, videoId: string): string | null {
  const id = videoId.trim();
  if (!id) return null;
  try {
    const absolute = new URL(packBuildLivePath(id), origin.endsWith('/') ? origin : `${origin}/`);
    return verifiedHttpsLiveUrl(absolute.href);
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
  | { ok: false; message: string; reasonCode?: string };

export type StudioRecoveryAction =
  | { id: 'rerun_analysis'; label: string }
  | { id: 'scroll_pack'; label: string }
  | { id: 'open_hosted'; label: string; href: string };

export type PackBuildLiveFailureDetails = {
  title: string;
  message: string;
  reasonCode?: string;
  actions: StudioRecoveryAction[];
};

/** YouTube id for `/d/{videoId}` — must come from the pack citation, not the dashboard row UUID. */
export function resolvePackBuildLiveVideoId(input: {
  packVideoId?: string | null;
  watchUrl?: string | null;
}): string | null {
  const fromPack = input.packVideoId?.trim() ?? '';
  if (fromPack && extractYouTubeId(fromPack)) {
    return fromPack;
  }
  const fromUrl = input.watchUrl?.trim() ? extractYouTubeId(input.watchUrl) : null;
  if (fromUrl) return fromUrl;
  return fromPack || null;
}

type StoredPackConfirmation = { ok: true; videoId: string } | { ok: false };

function sanitizeHostedDetail(detail: string | undefined): string | undefined {
  const raw = detail?.trim();
  if (!raw) return undefined;
  if (/\/api\//i.test(raw) || /generate\s+\/api/i.test(raw)) {
    return undefined;
  }
  return raw;
}

function healthFailureMessage(
  payload: PackBuildLiveHealthPayload,
  status: number,
): { message: string; reasonCode?: string } {
  const reason = payload.health?.reason_code;
  const detail = sanitizeHostedDetail(payload.health?.detail);
  const error = sanitizeHostedDetail(payload.error);
  if (reason === 'HOSTED_PACK_NOT_FOUND' || status === 404) {
    return {
      reasonCode: 'HOSTED_PACK_NOT_FOUND',
      message: 'No stored Video Pack for this video. Run analysis on this URL, then try Build live again.',
    };
  }
  if (reason === 'HOSTED_PACK_PROCESSING' || status === 202) {
    return {
      reasonCode: 'HOSTED_PACK_PROCESSING',
      message: 'Video Pack is still processing. Wait for analysis to finish, then try again.',
    };
  }
  if (reason === 'HOSTED_PACK_EXTRACT_FAILED') {
    return {
      reasonCode: reason,
      message:
        detail ??
        'Pack extraction failed. You can still open the hosted page for details, or re-run analysis in Studio.',
    };
  }
  if (detail) {
    return { reasonCode: reason, message: detail };
  }
  if (error) {
    return { reasonCode: reason, message: error };
  }
  return {
    reasonCode: reason,
    message: `Hosted build health check failed (HTTP ${status}).`,
  };
}

export function packBuildLiveFailureDetails(input: {
  reasonCode?: string | null;
  message?: string;
  videoId?: string | null;
  origin?: string;
  storedPackMissing?: boolean;
}): PackBuildLiveFailureDetails {
  const videoId = input.videoId?.trim() ?? '';
  const origin =
    input.origin?.trim() ||
    (typeof window !== 'undefined' ? window.location.origin : 'https://uvai.io');
  const hostedHref = videoId ? packBuildLiveUrl(origin, videoId) : null;
  const reason =
    input.reasonCode?.trim() ||
    (input.storedPackMissing ? 'HOSTED_PACK_NOT_FOUND' : undefined);

  const rerun: StudioRecoveryAction = { id: 'rerun_analysis', label: 'Re-run analysis' };
  const scrollPack: StudioRecoveryAction = { id: 'scroll_pack', label: 'Open Video pack section' };
  const openHosted: StudioRecoveryAction | null = hostedHref
    ? { id: 'open_hosted', label: 'Open hosted page', href: hostedHref }
    : null;

  switch (reason) {
    case 'HOSTED_PACK_NOT_FOUND':
      return {
        title: 'No stored Video Pack',
        message:
          input.message?.trim() ||
          'Run analysis on this URL so UVAI can store a Video Pack, then try Build live again.',
        reasonCode: reason,
        actions: [rerun, scrollPack],
      };
    case 'HOSTED_PACK_PROCESSING':
      return {
        title: 'Video Pack still processing',
        message:
          input.message?.trim() ||
          'Analysis is still storing the pack. Wait for the run to finish, then try Build live again.',
        reasonCode: reason,
        actions: [rerun],
      };
    case 'HOSTED_PACK_EXTRACT_FAILED':
      return {
        title: 'Hosted pack extraction failed',
        message:
          input.message?.trim() ||
          'Extraction did not produce a full hosted spec. Open the hosted page for the recorded reason, or re-run analysis if you intend to retry.',
        reasonCode: reason,
        actions: openHosted ? [openHosted, rerun] : [rerun],
      };
    default:
      return {
        title: 'Build live did not open',
        message:
          input.message?.trim() ||
          'Could not verify a hosted app for this video. Re-run analysis or open the hosted page when a pack exists.',
        reasonCode: reason,
        actions: openHosted ? [openHosted, rerun, scrollPack] : [rerun, scrollPack],
      };
  }
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
    return {
      ok: false,
      message: 'Analyze a video before Build live.',
      reasonCode: 'HOSTED_PACK_NOT_FOUND',
    };
  }

  const origin =
    input.origin?.trim() ||
    (typeof window !== 'undefined' ? window.location.origin : 'https://uvai.io');
  if (!packBuildLiveUrl(origin, videoId)) {
    return {
      ok: false,
      message: 'Could not resolve a hosted live URL for this video.',
      reasonCode: 'HOSTED_SPEC_INCOMPLETE',
    };
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
    const failure = healthFailureMessage(payload, response.status);
    return {
      ok: false,
      message: failure.message,
      reasonCode: failure.reasonCode,
    };
  }

  const liveUrl = packBuildLiveUrl(origin, hostVideoId);
  if (!liveUrl) {
    return {
      ok: false,
      message: 'Could not resolve a hosted live URL for this video.',
      reasonCode: 'HOSTED_SPEC_INCOMPLETE',
    };
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
  return verifiedHttpsLiveUrl(input.liveUrl);
}
