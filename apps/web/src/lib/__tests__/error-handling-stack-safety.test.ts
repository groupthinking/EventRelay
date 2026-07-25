import { describe, test, expect } from 'vitest';
import { formatApiError } from '../error-handling';

describe('formatApiError stack safety', () => {
  test('should not leak stack trace in formatApiError details', () => {
    const error = new Error('Database connection failed');
    const formatted = formatApiError(error);

    expect(formatted.message).toBe('Database connection failed');
    expect(formatted.details).toBeUndefined();
    if (error.stack) {
      expect(JSON.stringify(formatted)).not.toContain('error-handling-stack-safety.test.ts');
    }
  });
});
