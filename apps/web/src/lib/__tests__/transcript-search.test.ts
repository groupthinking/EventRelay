import { describe, it, expect } from 'vitest';
import {
  buildSearchConfig,
  filterSegments,
  type TranscriptSegment,
} from '@/lib/transcript-search';

/**
 * Regression tests for the transcript search path optimized in PR #972
 * (merge `ded0eccf3`, tracked by issue #908).
 *
 * That change hoisted `.toLowerCase()` out of the per-segment filter loop and
 * added null-safety guards. Issue #908 marks "null and empty search behavior is
 * preserved" as satisfied, but nothing enforced it: both components had zero
 * test coverage. These tests lock the behavior in so the guards cannot be
 * silently dropped by a future refactor.
 */

const seg = (over: Partial<TranscriptSegment> = {}): TranscriptSegment => ({
  id: 'seg-1',
  speaker: 'Speaker 1',
  speakerColor: '#6af2de',
  startTime: 0,
  endTime: 1,
  text: 'Hello World',
  ...over,
});

describe('filterSegments — empty/null query behavior (#908)', () => {
  const segments = [
    seg({ id: 'a', text: 'Alpha' }),
    seg({ id: 'b', text: 'Beta' }),
  ];

  it('returns every segment when the query is empty', () => {
    expect(filterSegments(segments, { search: '' }).map((s) => s.id)).toEqual([
      'a',
      'b',
    ]);
  });

  it.each([
    ['undefined', undefined],
    ['null', null],
  ])('returns every segment when the query is %s', (_label, query) => {
    const out = filterSegments(segments, {
      search: query as unknown as string,
    });
    expect(out.map((s) => s.id)).toEqual(['a', 'b']);
  });

  it('does not treat an empty query as "matches nothing"', () => {
    expect(filterSegments(segments, { search: '' })).toHaveLength(
      segments.length,
    );
  });
});

describe('filterSegments — null-safe segment text (#908)', () => {
  it('excludes segments whose text is null/undefined instead of throwing', () => {
    const segments = [
      seg({ id: 'ok', text: 'findme' }),
      seg({ id: 'nullish', text: undefined as unknown as string }),
      seg({ id: 'explicit-null', text: null as unknown as string }),
    ];

    // The guard's contract: a missing body is a non-match, never a crash.
    expect(() => filterSegments(segments, { search: 'findme' })).not.toThrow();
    expect(filterSegments(segments, { search: 'findme' }).map((s) => s.id)).toEqual(
      ['ok'],
    );
  });

  it('still returns text-less segments when there is no query', () => {
    const segments = [seg({ id: 'nullish', text: undefined as unknown as string })];
    expect(filterSegments(segments, { search: '' })).toHaveLength(1);
  });
});

describe('filterSegments — case insensitivity and speaker filter (#908)', () => {
  const segments = [
    seg({ id: 'a', speaker: 'Speaker 1', text: 'Hello World' }),
    seg({ id: 'b', speaker: 'Speaker 2', text: 'goodbye world' }),
  ];

  it('matches case-insensitively in both directions', () => {
    expect(filterSegments(segments, { search: 'WORLD' }).map((s) => s.id)).toEqual([
      'a',
      'b',
    ]);
    expect(filterSegments(segments, { search: 'hello' }).map((s) => s.id)).toEqual([
      'a',
    ]);
  });

  it('applies the speaker filter independently of the query', () => {
    expect(
      filterSegments(segments, { search: '', speaker: 'Speaker 2' }).map((s) => s.id),
    ).toEqual(['b']);
  });

  it('applies speaker and search together (AND, not OR)', () => {
    expect(
      filterSegments(segments, { search: 'hello', speaker: 'Speaker 2' }),
    ).toHaveLength(0);
  });
});

describe('filterSegments — normalization happens once per pass, not per segment (#908)', () => {
  it('lowercases the query exactly once regardless of segment count', () => {
    // This is the actual perf property PR #972 shipped. Asserting it directly
    // means a regression to per-segment normalization fails the suite rather
    // than silently costing N allocations per keystroke.
    let lowerCaseCalls = 0;
    const query = Object.assign(Object.create(String.prototype), {
      toString: () => 'world',
      toLowerCase: () => {
        lowerCaseCalls += 1;
        return 'world';
      },
    }) as unknown as string;

    const segments = Array.from({ length: 50 }, (_, i) =>
      seg({ id: `s${i}`, text: `World ${i}` }),
    );

    const out = filterSegments(segments, { search: query });

    expect(out).toHaveLength(50);
    expect(lowerCaseCalls).toBe(1);
  });
});

describe('buildSearchConfig — highlight regex (#908)', () => {
  it('returns null for empty/nullish queries so highlighting is skipped', () => {
    expect(buildSearchConfig('')).toBeNull();
    expect(buildSearchConfig(undefined as unknown as string)).toBeNull();
    expect(buildSearchConfig(null as unknown as string)).toBeNull();
  });

  it('escapes regex metacharacters instead of interpreting them', () => {
    const config = buildSearchConfig('a.b');
    expect(config).not.toBeNull();
    // Unescaped, `a.b` would match "axb". Escaped, it must not.
    expect(config!.regex.test('axb')).toBe(false);
    expect(config!.regex.test('a.b')).toBe(true);
  });

  it('does not throw on inputs that are invalid raw regexes', () => {
    // A lone `(` or `[` is an invalid pattern; escaping must make it literal.
    expect(() => buildSearchConfig('(')).not.toThrow();
    expect(() => buildSearchConfig('[')).not.toThrow();
    expect(buildSearchConfig('(')!.regex.test('(')).toBe(true);
  });

  it('omits the global flag so .test() cannot desync via lastIndex', () => {
    const config = buildSearchConfig('x')!;
    expect(config.regex.flags).not.toContain('g');
    // With /g, the second call would return false due to lastIndex carry-over.
    expect(config.regex.test('x')).toBe(true);
    expect(config.regex.test('x')).toBe(true);
  });

  it('is a capturing regex so String.split retains the matched text', () => {
    const config = buildSearchConfig('world')!;
    expect('hello world!'.split(config.regex)).toContain('world');
  });

  it('exposes a pre-lowercased query for allocation-free comparison', () => {
    expect(buildSearchConfig('WoRlD')!.lower).toBe('world');
  });
});
