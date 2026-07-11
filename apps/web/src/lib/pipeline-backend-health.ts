import 'server-only';

import { backendHeaders } from '@/lib/pipeline-backend';

export const PIPELINE_HEALTH_TIMEOUT_MS = 5_000;

export interface BackendHealth {
  configured: boolean;
  available: boolean;
  host: string | null;
  reason?: string;
}

export function getBackendConfig(): { configured: boolean; url: string } {
  const raw = (process.env.BACKEND_URL || '').trim();
  const configured = raw.startsWith('http');
  return {
    configured,
    url: configured ? raw.replace(/\/$/, '') : '',
  };
}

function backendHost(url: string): string | null {
  try {
    return new URL(url).host;
  } catch {
    return null;
  }
}

function timeoutSignal(ms: number): AbortSignal {
  return AbortSignal.timeout(ms);
}

/** Probe FastAPI /api/v1/health — use before routing to backend strategies. */
export async function checkBackendHealth(
  timeoutMs = PIPELINE_HEALTH_TIMEOUT_MS,
): Promise<BackendHealth> {
  const { configured, url } = getBackendConfig();
  if (!configured) {
    return {
      configured: false,
      available: false,
      host: null,
      reason: 'BACKEND_URL is not configured',
    };
  }

  try {
    const response = await fetch(`${url}/api/v1/health`, {
      cache: 'no-store',
      headers: backendHeaders(),
      signal: timeoutSignal(timeoutMs),
    });
    return {
      configured: true,
      available: response.ok,
      host: backendHost(url),
      reason: response.ok ? undefined : `Backend health returned ${response.status}`,
    };
  } catch (error) {
    return {
      configured: true,
      available: false,
      host: backendHost(url),
      reason: error instanceof Error ? error.message : String(error),
    };
  }
}

/** Parse backend JSON safely; returns null when body is HTML or malformed. */
export async function parseBackendJson<T>(response: Response): Promise<T | null> {
  const text = await response.text();
  const trimmed = text.trim();
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
    return null;
  }
  try {
    return JSON.parse(trimmed) as T;
  } catch {
    return null;
  }
}