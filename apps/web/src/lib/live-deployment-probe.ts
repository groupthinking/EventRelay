/**
 * Reachability of the exact claimed deployment URL, not a redirect target.
 * Public DNS validation is a first line of defense, not DNS-rebinding protection.
 * Runtime egress containment is still required; this helper grants no authority.
 */
import { assertPublicHttpUrl } from '@/lib/ssrf-guard';

export type LiveDeploymentProbeResult =
  | { ok: true; statusCode: number; finalUrl: string }
  | { ok: false; statusCode?: number; error: string };

const PROBE_TIMEOUT_MS = 8_000;

export async function probeLiveDeploymentUrl(
  liveUrl: string,
): Promise<LiveDeploymentProbeResult> {
  const trimmed = liveUrl.trim();
  if (!trimmed) return { ok: false, error: 'empty_url' };
  let target: URL;
  try {
    target = new URL(trimmed);
    if (trimmed.length > 2048 || target.protocol !== 'https:' ||
        target.username || target.password || target.hash) {
      return { ok: false, error: 'invalid_target' };
    }
    await assertPublicHttpUrl(target.href);
  } catch {
    return { ok: false, error: 'invalid_target' };
  }
  try {
    const response = await fetch(target.href, {
      method: 'GET',
      // A failed target must not expand the destination or substitute evidence.
      redirect: 'error',
      signal: AbortSignal.timeout(PROBE_TIMEOUT_MS),
      headers: { Accept: 'text/html,application/json;q=0.9,*/*;q=0.8' },
    });
    if (response.status >= 300 && response.status < 400) {
      return { ok: false, statusCode: response.status, error: 'redirect_rejected' };
    }
    if (response.status >= 200 && response.status < 300) {
      if (response.redirected || response.url !== target.href) {
        return { ok: false, error: 'target_mismatch' };
      }
      return { ok: true, statusCode: response.status, finalUrl: response.url };
    }
    return { ok: false, statusCode: response.status, error: `http_${response.status}` };
  } catch {
    // Avoid returning DNS, credential or transport details to callers.
    return { ok: false, error: 'probe_failed' };
  }
}
