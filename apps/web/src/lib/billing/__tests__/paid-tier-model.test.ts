import { describe, it, expect } from 'vitest';
import { resolvePaidTierRouting } from '../paid-tier-model';

describe('resolvePaidTierRouting', () => {
  it('routes Pro users to Grok composer lead model', () => {
    const routing = resolvePaidTierRouting(true);
    expect(routing.plan).toBe('pro');
    expect(routing.runtime).toBe('grok-composer');
    expect(routing.model).toContain('grok');
  });

  it('routes free users to standard cost-controlled model', () => {
    const routing = resolvePaidTierRouting(false);
    expect(routing.plan).toBe('free');
    expect(routing.runtime).toBe('standard');
  });
});