import { describe, expect, it } from 'vitest';
import { formatApiError } from '@/lib/error-handling';

/**
 * Security regression coverage for #945 / PR #942.
 *
 * `formatApiError` must never surface stack-derived implementation details in
 * the client-visible error payload. These tests pin that boundary so the
 * general web suite cannot pass while a regression re-exposes `Error.stack`.
 */
describe('formatApiError stack-trace safety', () => {
  const STACK_MARKER = 'SECRET_STACK_FRAME at /srv/app/internal/secret.ts:42:13';

  it('returns only the public message for an Error and never leaks the stack', () => {
    const error = new Error('Something failed publicly');
    error.stack = `Error: Something failed publicly\n    ${STACK_MARKER}`;

    const result = formatApiError(error);

    expect(result).toEqual({ message: 'Something failed publicly' });
    // The serialized payload is what reaches the client — assert the whole
    // shape is free of any stack-derived detail, not just the known keys.
    expect(JSON.stringify(result)).not.toContain(STACK_MARKER);
    expect(JSON.stringify(result)).not.toContain('secret.ts');
    expect(result).not.toHaveProperty('stack');
    expect(result.details).toBeUndefined();
  });

  it('falls back to the default message when an Error has an empty message', () => {
    const error = new Error('');
    error.stack = `Error\n    ${STACK_MARKER}`;

    const result = formatApiError(error, 'An error occurred');

    expect(result).toEqual({ message: 'An error occurred' });
    expect(JSON.stringify(result)).not.toContain(STACK_MARKER);
  });

  it('formats the non-Error object shape without exposing extra internals', () => {
    const result = formatApiError({
      message: 'Upstream rejected',
      code: 'E_UPSTREAM',
      stack: STACK_MARKER,
    });

    expect(result).toEqual({ message: 'Upstream rejected', code: 'E_UPSTREAM' });
    expect(JSON.stringify(result)).not.toContain(STACK_MARKER);
    expect(result).not.toHaveProperty('stack');
    expect(result.details).toBeUndefined();
  });

  it('handles primitive errors with only the public string or default', () => {
    expect(formatApiError('plain failure')).toEqual({ message: 'plain failure' });
    expect(formatApiError('', 'fallback message')).toEqual({ message: 'fallback message' });
  });
});
