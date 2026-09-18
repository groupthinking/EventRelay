import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  workflowProPriceLabel,
  WORKFLOW_PRO_ANNUAL_CENTS,
  WORKFLOW_PRO_MONTHLY_CENTS,
  WORKFLOW_PRO_PRODUCT_NAME,
} from '@/lib/billing/checkout-config';

const pricingPage = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../page.tsx'),
  'utf8',
);

describe('pricing catalog copy', () => {
  it('renders UVAI Workflow Pro at $39/mo and $390/yr from checkout config', () => {
    expect(WORKFLOW_PRO_PRODUCT_NAME).toBe('UVAI Workflow Pro');
    expect(WORKFLOW_PRO_MONTHLY_CENTS).toBe(3900);
    expect(WORKFLOW_PRO_ANNUAL_CENTS).toBe(39_000);
    expect(workflowProPriceLabel(false)).toBe('$39/mo');
    expect(workflowProPriceLabel(true)).toBe('$390/yr');
    expect(pricingPage).toContain('WORKFLOW_PRO_PRODUCT_NAME');
    expect(pricingPage).toContain('workflowProPriceLabel');
    expect(pricingPage).toContain('ProCheckoutButton');
    expect(pricingPage).toContain('turnstile');
  });

  it('does not advertise EventRelay Pro or the stale $19/$180 catalog', () => {
    expect(pricingPage).not.toContain('EventRelay Pro');
    expect(pricingPage).not.toContain('$19/mo');
    expect(pricingPage).not.toContain('$180/yr');
    expect(pricingPage).not.toContain('1900');
    expect(pricingPage).not.toContain('18000');
  });
});
