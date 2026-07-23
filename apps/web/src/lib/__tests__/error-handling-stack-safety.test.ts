import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { formatApiError } from '../error-handling';

const webSrc = join(dirname(fileURLToPath(import.meta.url)), '../..');

function readSource(relativePath: string) {
  return readFileSync(join(webSrc, relativePath), 'utf8');
}

describe('formatApiError stack safety', () => {
  it('does not expose Error.stack in the formatted response', () => {
    const err = new Error('public message only');
    err.stack =
      'Error: public message only\n    at Object.<anonymous> (/src/secret/internal-path.ts:42:7)';

    const result = formatApiError(err);

    expect(result.message).toBe('public message only');
    // stack-derived details must not appear anywhere in the result
    expect(JSON.stringify(result)).not.toContain('internal-path.ts');
    expect(JSON.stringify(result)).not.toContain('secret');
    expect(result).not.toHaveProperty('stack');
    expect(result).not.toHaveProperty('details');
  });

  it('uses the defaultMessage when Error.message is empty', () => {
    const err = new Error('');
    err.stack = 'Error\n    at Object.<anonymous> (/src/secret/another-path.ts:1:1)';

    const result = formatApiError(err, 'fallback message');

    expect(result.message).toBe('fallback message');
    expect(JSON.stringify(result)).not.toContain('another-path.ts');
    expect(result).not.toHaveProperty('stack');
  });

  it('handles a non-Error object shape with message and code', () => {
    const result = formatApiError({ message: 'bad request', code: 'ERR_400' });

    expect(result.message).toBe('bad request');
    expect(result.code).toBe('ERR_400');
    expect(result).not.toHaveProperty('stack');
  });

  it('handles a primitive input without throwing', () => {
    const result = formatApiError('something went wrong');

    expect(result.message).toBe('something went wrong');
    expect(result).not.toHaveProperty('stack');
  });

  it('source file does not contain stack in the Error branch', () => {
    const source = readSource('lib/error-handling.ts');
    // The Error instanceof branch must not reference .stack
    const errorBranchMatch = source.match(
      /if\s*\(\s*error\s+instanceof\s+Error\s*\)([\s\S]*?)(?=if\s*\(typeof|return\s*\{[^}]*message:\s*String)/,
    )?.[1];

    if (errorBranchMatch) {
      expect(errorBranchMatch).not.toContain('.stack');
    } else {
      // Fallback: verify .stack is absent from the entire formatApiError body
      const fnMatch = source.match(/function formatApiError[\s\S]*?^}/m)?.[0] ?? '';
      expect(fnMatch).not.toContain('error.stack');
    }
  });
});
