import { describe, it, expect, afterEach } from 'vitest';
import { backendHeaders, resolveBackendStatusUrl } from '@/lib/pipeline-backend';

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

describe('resolveBackendStatusUrl', () => {
  const backend = 'https://api.uvai.io';

  it('accepts relative paths on the configured backend', () => {
    expect(resolveBackendStatusUrl('/api/v1/jobs/abc', backend)).toBe(
      'https://api.uvai.io/api/v1/jobs/abc',
    );
  });

  it('accepts absolute URLs on the configured backend origin', () => {
    expect(resolveBackendStatusUrl('https://api.uvai.io/api/v1/jobs/abc', backend)).toBe(
      'https://api.uvai.io/api/v1/jobs/abc',
    );
  });

  it('rejects untrusted origins', () => {
    expect(() =>
      resolveBackendStatusUrl('https://evil.example/jobs/abc', backend),
    ).toThrow(/untrusted origin/);
  });
});