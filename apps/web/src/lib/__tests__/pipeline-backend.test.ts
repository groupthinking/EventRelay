import { describe, it, expect, afterEach } from 'vitest';
import { backendHeaders } from '@/lib/pipeline-backend';

describe('backendHeaders', () => {
  const original = process.env.EVENTRELAY_API_KEY;

  afterEach(() => {
    if (original === undefined) {
      delete process.env.EVENTRELAY_API_KEY;
    } else {
      process.env.EVENTRELAY_API_KEY = original;
    }
  });

  it('includes trimmed X-API-Key when configured', () => {
    process.env.EVENTRELAY_API_KEY = '  test-key\n';
    expect(backendHeaders()).toEqual({
      'Content-Type': 'application/json',
      'X-API-Key': 'test-key',
    });
  });

  it('omits X-API-Key when unset', () => {
    delete process.env.EVENTRELAY_API_KEY;
    expect(backendHeaders()).toEqual({ 'Content-Type': 'application/json' });
  });
});