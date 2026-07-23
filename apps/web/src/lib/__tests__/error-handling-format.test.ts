import { describe, it, expect } from 'vitest';
import { formatApiError } from '@/lib/error-handling';

/**
 * Security regression coverage for `formatApiError` (see PR #942 / issue #945).
 *
 * The formatter must never surface stack-derived implementation details in the
 * response payload. These tests assign a distinctive `Error.stack` and assert
 * the formatted result carries only the public message, plus coverage for the
 * non-`Error` object and primitive shapes so the security boundary cannot
 * regress undetected via a general refactor.
 */
describe('formatApiError', () => {
  it('returns only the public message for Error instances and never leaks the stack', () => {
    const error = new Error('Database connection failed');
    error.stack =
      'Error: Database connection failed\n' +
      '    at queryUsers (/srv/app/secret/path/db.ts:42:13)\n' +
      '    at internalHandler (/srv/app/lib/pg.ts:88:7)';

    const result = formatApiError(error);

    expect(result).toEqual({ message: 'Database connection failed' });
    // No stack-derived field should exist on the formatted payload.
    expect(result).not.toHaveProperty('details');
    expect(result).not.toHaveProperty('stack');

    // Belt-and-braces: distinctive stack tokens must not appear anywhere in the
    // serialized response, even if a future change adds new fields.
    const serialized = JSON.stringify(result);
    expect(serialized).not.toContain('/srv/app');
    expect(serialized).not.toContain('db.ts');
    expect(serialized).not.toContain('internalHandler');
  });

  it('falls back to the default message when an Error has an empty message, still hiding the stack', () => {
    const error = new Error('');
    error.stack = 'Error\n    at leak (/srv/secret.ts:1:1)';

    const result = formatApiError(error, 'A fallback message');

    expect(result).toEqual({ message: 'A fallback message' });
    expect(JSON.stringify(result)).not.toContain('/srv/secret.ts');
  });

  it('extracts message and code from plain object errors without adding details', () => {
    const result = formatApiError({ message: 'Rate limited', code: 'RATE_LIMIT' });

    expect(result).toEqual({ message: 'Rate limited', code: 'RATE_LIMIT' });
    expect(result).not.toHaveProperty('details');
  });

  it('uses the error field and an empty code when message is absent on object errors', () => {
    const result = formatApiError({ error: 'Upstream unavailable' });

    expect(result.message).toBe('Upstream unavailable');
    expect(result.code).toBe('');
  });

  it('stringifies primitive errors and applies the default only when the value is falsy', () => {
    expect(formatApiError('boom').message).toBe('boom');
    // String('') is falsy, so the default takes over.
    expect(formatApiError('', 'Nothing here').message).toBe('Nothing here');
    // A bare number stringifies rather than falling back.
    expect(formatApiError(503).message).toBe('503');
  });
});
