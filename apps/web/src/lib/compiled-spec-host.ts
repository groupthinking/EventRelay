import { studioVerifiedLiveUrl } from '@/lib/studio-pipeline-status';

export interface HostedSpecHealthCheck {
  ok: boolean;
  status: number;
  checked_at: string;
  detail?: string;
}

const HEALTH_HISTORY_LIMIT = 20;
const hostedSpecHealthChecks = new Map<string, HostedSpecHealthCheck[]>();

function normalizedVideoId(videoId: string): string {
  return videoId.trim();
}

export function hostedSpecLivePath(videoId: string): string {
  return `/d/${encodeURIComponent(normalizedVideoId(videoId))}`;
}

export function evaluateHostedSpecHealth(files: Record<string, string>): HostedSpecHealthCheck {
  const required = ['index.html', 'src/main.ts', 'src/pack.ts', 'package.json'];
  const missing = required.filter((path) => !(files[path] ?? '').trim());
  if (missing.length > 0) {
    return {
      ok: false,
      status: 503,
      checked_at: new Date().toISOString(),
      detail: `Missing hosted spec files: ${missing.join(', ')}`,
    };
  }
  return {
    ok: true,
    status: 200,
    checked_at: new Date().toISOString(),
  };
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
