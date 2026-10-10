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
const MAX_PENDING_VALIDATIONS = 4;
let pendingValidations = 0;

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
  } catch {
    return { ok: false, error: 'invalid_target' };
  }
  // Node DNS lookup cannot be cancelled. Retain its slot until it settles,
  // even after the caller times out, to bound outstanding resolver work.
  if (pendingValidations >= MAX_PENDING_VALIDATIONS) {
    return { ok: false, error: 'probe_busy' };
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  timer.unref();
  let onAbort: (() => void) | undefined;
  const deadline = new Promise<never>((_, reject) => {
    onAbort = () => reject(new Error('Probe deadline exceeded'));
    controller.signal.addEventListener('abort', onAbort, { once: true });
  });
  let validating = true;
  try {
    pendingValidations += 1;
    const validation = assertPublicHttpUrl(target.href).finally(() => {
      pendingValidations -= 1;
    });
    // Race attaches rejection handlers even if DNS settles after timeout.
    await Promise.race([validation, deadline]);
    validating = false;
    const response = await Promise.race([fetch(target.href, {
      method: 'GET',
      // A failed target must not expand the destination or substitute evidence.
      redirect: 'manual',
      signal: controller.signal,
      headers: { Accept: 'text/html,application/json;q=0.9,*/*;q=0.8' },
    }), deadline]);
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
    return { ok: false, error: controller.signal.aborted ? 'probe_timeout' : validating ? 'invalid_target' : 'probe_failed' };
  } finally {
    clearTimeout(timer);
    if (onAbort) controller.signal.removeEventListener('abort', onAbort);
  }
}
