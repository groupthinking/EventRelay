import { afterEach, describe, expect, it } from 'vitest';
import {
  TEMP_PAYWALL_OFF,
  isChatPaywallBypassed,
  isTempPaywallOff,
} from '../paywall-bypass';

const original = process.env.TEMP_PAYWALL_OFF;

afterEach(() => {
  if (original === undefined) {
    delete process.env.TEMP_PAYWALL_OFF;
  } else {
    process.env.TEMP_PAYWALL_OFF = original;
  }
});

describe('TEMP_PAYWALL_OFF', () => {
  it('defaults on so signed-in dogfood skips the Pro chat gate', () => {
    delete process.env.TEMP_PAYWALL_OFF;
    expect(TEMP_PAYWALL_OFF).toBe(true);
    expect(isTempPaywallOff()).toBe(true);
    expect(isChatPaywallBypassed('signed-in@example.com')).toBe(true);
    expect(isChatPaywallBypassed('')).toBe(false);
    expect(isChatPaywallBypassed(null)).toBe(false);
  });

  it('TEMP_PAYWALL_OFF=0 re-enables the paywall without a code change', () => {
    process.env.TEMP_PAYWALL_OFF = '0';
    expect(isTempPaywallOff()).toBe(false);
    expect(isChatPaywallBypassed('signed-in@example.com')).toBe(false);
  });
});
