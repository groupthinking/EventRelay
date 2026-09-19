import { studioVerifiedLiveUrl } from '@/lib/studio-pipeline-status';

export type HostedSpecHealthReasonCode =
  | 'HOSTED_SPEC_READY'
  | 'HOSTED_SPEC_INCOMPLETE'
  | 'HOSTED_PACK_NOT_FOUND'
  | 'HOSTED_PACK_PROCESSING'
  | 'HOSTED_PACK_EXTRACT_FAILED'
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
  | { kind: 'identity_only' };

const HEALTH_HISTORY_LIMIT = 20;
const hostedSpecHealthChecks = new Map<string, HostedSpecHealthCheck[]>();

function normalizedVideoId(videoId: string): string {
  return videoId.trim();
}

export function hostedSpecLivePath(videoId: string): string {
  return `/d/${encodeURIComponent(normalizedVideoId(videoId))}`;
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
