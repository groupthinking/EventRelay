import { describe, it, expect } from 'vitest';
import { firstNonNull } from '@/lib/transcription-service';

// Regression guard for the transcript-fallback race: when every provider
// resolves to null (or rejects), the resolver must SETTLE to null rather than
// hang. The previous Promise.race()-over-PENDING_FOREVER implementation hung
// forever in exactly this case, wedging the request.

const defer = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

describe('firstNonNull', () => {
  it('resolves null when there are no candidates', async () => {
    await expect(firstNonNull<string>([])).resolves.toBeNull();
  });

  it('settles to null (does not hang) when every candidate resolves null', async () => {
    const result = await firstNonNull<string>([
      Promise.resolve(null),
      Promise.resolve(null),
      Promise.resolve(null),
    ]);
    expect(result).toBeNull();
  });

  it('settles to null when every candidate rejects', async () => {
    const result = await firstNonNull<string>([
      Promise.reject(new Error('a')),
      Promise.reject(new Error('b')),
    ]);
    expect(result).toBeNull();
  });

  it('returns the first non-null result without waiting for slow candidates', async () => {
    const slow = defer<string | null>();
    const result = await firstNonNull<string>([
      Promise.resolve(null),
      Promise.resolve('winner'),
      slow.promise,
    ]);
    expect(result).toBe('winner');
    // Slow candidate never settles; the resolver must not have awaited it.
  });

  it('treats a falsy-but-non-null value as a real result', async () => {
    const result = await firstNonNull<string>([
      Promise.resolve(null),
      Promise.resolve(''),
    ]);
    expect(result).toBe('');
  });

  it('skips a rejecting candidate and returns a later non-null result', async () => {
    const result = await firstNonNull<string>([
      Promise.reject(new Error('boom')),
      Promise.resolve(null),
      Promise.resolve('ok'),
    ]);
    expect(result).toBe('ok');
  });
});
