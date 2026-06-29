/** Default Grok/Composer model for paid-tier agent features. */
export const GROK_BILLING_LEAD_MODEL =
  process.env.GROK_BILLING_LEAD_MODEL || 'grok-4-1-fast';

export function billingLeadMetadata(): Record<string, string> {
  return {
    lead_model: GROK_BILLING_LEAD_MODEL,
    lead_runtime: 'grok-composer',
  };
}