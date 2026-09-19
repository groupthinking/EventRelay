import { reasonEnvelope, reasonEnvelopeJson } from '@/lib/api-reason-envelope';
import { studioVerifiedLiveUrl } from '@/lib/studio-pipeline-status';

export { hostedSpecLivePath } from '@/lib/hosted-spec-paths';

export type HostedSpecHealthReasonCode =
  | 'HOSTED_SPEC_READY'
  | 'HOSTED_SPEC_INCOMPLETE'
  | 'HOSTED_PACK_NOT_FOUND'
  | 'HOSTED_PACK_PROCESSING'
  | 'HOSTED_PACK_EXTRACT_FAILED'
  | 'HOSTED_PACK_STORE_ERROR'
  | 'HOSTED_PACK_IDENTITY_ONLY';

export interface HostedSpecHealthCheck {
  ok: boolean;
  status: number;
  checked_at: string;
  detail?: string;
  reason_code?: HostedSpecHealthReasonCode;
}

export type HostedPackResolution =
  | { kind: 'ready'; files: Record<string, string> }
  | { kind: 'missing' }
  | { kind: 'processing' }
  | { kind: 'extract_error'; message: string }
  | { kind: 'store_error'; message: string }
  | { kind: 'identity_only' };

const HEALTH_HISTORY_LIMIT = 20;
const hostedSpecHealthChecks = new Map<string, HostedSpecHealthCheck[]>();

function normalizedVideoId(videoId: string): string {
  return videoId.trim();
}

export function evaluateHostedSpecHealth(files: Record<string, string>): HostedSpecHealthCheck {
  const checked_at = new Date().toISOString();
  const required = ['index.html', 'src/main.ts', 'src/pack.ts', 'package.json'];
  const missing = required.filter((path) => !(files[path] ?? '').trim());
  if (missing.length > 0) {
    return {
      ok: false,
      status: 200,
      checked_at,
      reason_code: 'HOSTED_SPEC_INCOMPLETE',
      detail: `Missing hosted spec files: ${missing.join(', ')}`,
    };
  }
  return {
    ok: true,
    status: 200,
    checked_at,
    reason_code: 'HOSTED_SPEC_READY',
  };
}

export function hostedSpecHealthFromPackResolution(
  resolution: HostedPackResolution,
): HostedSpecHealthCheck {
  const checked_at = new Date().toISOString();
  switch (resolution.kind) {
    case 'ready':
      return evaluateHostedSpecHealth(resolution.files);
    case 'missing':
      return {
        ok: false,
        status: 200,
        checked_at,
        reason_code: 'HOSTED_PACK_NOT_FOUND',
        detail: 'Video pack not found. Generate /api/video/pack first.',
      };
    case 'processing':
      return {
        ok: false,
        status: 200,
        checked_at,
        reason_code: 'HOSTED_PACK_PROCESSING',
        detail: 'Video pack is still processing.',
      };
    case 'extract_error':
      return {
        ok: false,
        status: 200,
        checked_at,
        reason_code: 'HOSTED_PACK_EXTRACT_FAILED',
        detail: resolution.message,
      };
    case 'store_error':
      return {
        ok: false,
        status: 200,
        checked_at,
        reason_code: 'HOSTED_PACK_STORE_ERROR',
        detail: resolution.message,
      };
    case 'identity_only':
      return {
        ok: false,
        status: 200,
        checked_at,
        reason_code: 'HOSTED_PACK_IDENTITY_ONLY',
        detail: 'Compiled spec is unavailable for identity-only packs.',
      };
    default: {
      const unexpected: never = resolution;
      return {
        ok: false,
        status: 200,
        checked_at,
        reason_code: 'HOSTED_PACK_EXTRACT_FAILED',
        detail: `Unhandled pack resolution: ${JSON.stringify(unexpected)}`,
      };
    }
  }
}

export function recordHostedSpecHealthCheck(
  videoId: string,
  health: HostedSpecHealthCheck,
): HostedSpecHealthCheck {
  const key = normalizedVideoId(videoId);
  const history = hostedSpecHealthChecks.get(key) ?? [];
  history.push(health);
  if (history.length > HEALTH_HISTORY_LIMIT) {
    history.splice(0, history.length - HEALTH_HISTORY_LIMIT);
  }
  hostedSpecHealthChecks.set(key, history);
  return health;
}

export function hostedSpecHealthHistory(videoId: string): HostedSpecHealthCheck[] {
  return [...(hostedSpecHealthChecks.get(normalizedVideoId(videoId)) ?? [])];
}

export function latestHostedSpecHealthCheck(videoId: string): HostedSpecHealthCheck | null {
  const history = hostedSpecHealthChecks.get(normalizedVideoId(videoId));
  if (!history || history.length === 0) return null;
  return history[history.length - 1] ?? null;
}

export type FactoryDeliverStatus = {
  videoId: string;
  live_url: string | null;
  health: HostedSpecHealthCheck | null;
  ready: boolean;
  reason_code:
    | 'FACTORY_DELIVER_READY'
    | 'FACTORY_DELIVER_MISSING_LIVE_URL'
    | 'FACTORY_DELIVER_MISSING_HEALTH'
    | 'FACTORY_DELIVER_HEALTH_FAILED';
};

export function factoryDeliverFromHostedSpec(input: {
  videoId: string;
  liveUrl?: string | null;
  health?: HostedSpecHealthCheck | null;
}): FactoryDeliverStatus {
  const verifiedLiveUrl = studioVerifiedLiveUrl(input.liveUrl);
  if (!verifiedLiveUrl) {
    return {
      videoId: normalizedVideoId(input.videoId),
      live_url: null,
      health: input.health ?? null,
      ready: false,
      reason_code: 'FACTORY_DELIVER_MISSING_LIVE_URL',
    };
  }
  const health = input.health ?? null;
  if (!health) {
    return {
      videoId: normalizedVideoId(input.videoId),
      live_url: verifiedLiveUrl,
      health: null,
      ready: false,
      reason_code: 'FACTORY_DELIVER_MISSING_HEALTH',
    };
  }
  if (!health.ok || health.status < 200 || health.status >= 400) {
    return {
      videoId: normalizedVideoId(input.videoId),
      live_url: verifiedLiveUrl,
      health,
      ready: false,
      reason_code: 'FACTORY_DELIVER_HEALTH_FAILED',
    };
  }
  return {
    videoId: normalizedVideoId(input.videoId),
    live_url: verifiedLiveUrl,
    health,
    ready: true,
    reason_code: 'FACTORY_DELIVER_READY',
  };
}

export function resetHostedSpecHealthChecksForTests(): void {
  hostedSpecHealthChecks.clear();
}

export function isHostedExtractOrGatewayMessage(message: string): boolean {
  const normalized = message.trim().toLowerCase();
  if (!normalized) return false;
  if (normalized.includes('vercel ai gateway')) return true;
  if (normalized.includes('returned empty content')) return true;
  if (normalized.includes('returned no extracted spec')) return true;
  if (normalized.includes('videopackextracterror')) return true;
  return false;
}

export function hostedPackResolutionFromThrownError(error: unknown): HostedPackResolution {
  if (error instanceof Error) {
    const message = error.message.trim() || 'Hosted pack resolution failed.';
    if (isHostedExtractOrGatewayMessage(message) || error.name === 'VideoPackExtractError') {
      return { kind: 'extract_error', message };
    }
    return { kind: 'extract_error', message };
  }
  return {
    kind: 'extract_error',
    message: typeof error === 'string' && error.trim() ? error.trim() : 'Hosted pack resolution failed.',
  };
}

export function isHostedHealthPath(pathname: string, videoId: string): boolean {
  const id = normalizedVideoId(videoId);
  if (!id) return false;
  const base = `/d/${encodeURIComponent(id)}`;
  return pathname === `${base}/health` || pathname === `${base}/health/`;
}

export function isHostedIndexRequest(assetParts: string[]): boolean {
  if (assetParts.length === 0) return true;
  if (assetParts.length === 1 && assetParts[0] === 'index.html') return true;
  return false;
}

/** Canonical hosted app page: `/d/{videoId}` or `/d/{videoId}/` (not `/health` or asset paths). */
export function isHostedLivePagePath(pathname: string, videoId: string): boolean {
  const id = normalizedVideoId(videoId);
  if (!id) return false;
  if (isHostedHealthPath(pathname, id)) return false;
  const base = `/d/${encodeURIComponent(id)}`;
  return pathname === base || pathname === `${base}/`;
}

export function isHostedLivePageRequest(
  request: Request,
  videoId: string,
  assetParts: string[],
): boolean {
  if (isHostedIndexRequest(assetParts)) {
    return true;
  }
  try {
    return isHostedLivePagePath(new URL(request.url).pathname, videoId);
  } catch {
    return false;
  }
}

export function hostedPackAssetUnavailableJson(
  videoId: string,
  health: HostedSpecHealthCheck,
): Record<string, unknown> {
  return reasonEnvelopeJson(
    reasonEnvelope(
      false,
      health.reason_code ?? 'HOSTED_PACK_EXTRACT_FAILED',
      health.detail,
    ),
    {
      videoId: normalizedVideoId(videoId),
      health,
    },
  );
}
