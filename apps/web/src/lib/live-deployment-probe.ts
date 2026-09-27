/**
 * HTTP reachability probe for claimed live deployment URLs.
 * Used by G.A.T.E. before treating a hostname-valid https URL as verified evidence.
 */

export type LiveDeploymentProbeResult =
  | { ok: true; statusCode: number; finalUrl: string }
  | { ok: false; statusCode?: number; error: string };

const PROBE_TIMEOUT_MS = 8_000;

export async function probeLiveDeploymentUrl(
  liveUrl: string,
): Promise<LiveDeploymentProbeResult> {
  const trimmed = liveUrl.trim();
  if (!trimmed) {
    return { ok: false, error: 'empty_url' };
  }
  try {
    const response = await fetch(trimmed, {
      method: 'GET',
      redirect: 'follow',
      signal: AbortSignal.timeout(PROBE_TIMEOUT_MS),
      headers: { Accept: 'text/html,application/json;q=0.9,*/*;q=0.8' },
    });
    if (response.status >= 200 && response.status < 400) {
      return { ok: true, statusCode: response.status, finalUrl: response.url };
    }
    return {
      ok: false,
      statusCode: response.status,
      error: `http_${response.status}`,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { ok: false, error: message.slice(0, 200) };
  }
}
