/**
 * Hayden lock 2026-09-26 — temporary production dogfood bypass.
 *
 * Signed-in sessions (NextAuth email or HMAC billing cookie) use the Pro
 * chat path, including xAI, without a Stripe subscription. Checkout,
 * webhooks, and stored entitlements stay in place. Agent dispatch, video
 * generation, workspace export, and refinery dataset access stay gated.
 *
 * Re-enable the paywall in this one file:
 *   set `TEMP_PAYWALL_OFF` to `false`.
 * Runtime override without editing the constant:
 *   `TEMP_PAYWALL_OFF=0` (or `false` / `off`) turns the paywall back on.
 *   `TEMP_PAYWALL_OFF=1` (or `true` / `on`) forces the bypass on.
 */

/** Flip to `false` to restore the Pro chat paywall. */
export const TEMP_PAYWALL_OFF = true;

export function isTempPaywallOff(): boolean {
  const raw = process.env.TEMP_PAYWALL_OFF?.trim().toLowerCase();
  if (raw === '0' || raw === 'false' || raw === 'off') return false;
  if (raw === '1' || raw === 'true' || raw === 'on') return true;
  return TEMP_PAYWALL_OFF;
}

/** True when a trusted signed-in identity should skip the Pro chat gate. */
export function isChatPaywallBypassed(email: string | null | undefined): boolean {
  return Boolean(email?.trim()) && isTempPaywallOff();
}
