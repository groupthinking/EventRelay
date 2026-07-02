import { describe, it, expect } from 'vitest';
import {
  parseTimestampToSeconds,
  formatSeconds,
  extractYouTubeId,
  parseTranscriptSegments,
} from '@/lib/timestamp';

describe('parseTimestampToSeconds', () => {
  it('parses bare seconds', () => {
    expect(parseTimestampToSeconds('83')).toBe(83);
    expect(parseTimestampToSeconds('0')).toBe(0);
  });
  it('parses M:SS and MM:SS', () => {
    expect(parseTimestampToSeconds('1:23')).toBe(83);
    expect(parseTimestampToSeconds('01:23')).toBe(83);
  });
  it('parses H:MM:SS', () => {
    expect(parseTimestampToSeconds('1:02:03')).toBe(3723);
  });
  it('strips brackets and parens', () => {
    expect(parseTimestampToSeconds('[1:23]')).toBe(83);
    expect(parseTimestampToSeconds('(0:05)')).toBe(5);
  });
  it('returns null for garbage', () => {
    expect(parseTimestampToSeconds('abc')).toBeNull();
    expect(parseTimestampToSeconds('')).toBeNull();
    expect(parseTimestampToSeconds(null)).toBeNull();
    expect(parseTimestampToSeconds('1:2:3:4')).toBeNull();
  });
});

describe('formatSeconds', () => {
  it('formats under an hour as M:SS', () => {
    expect(formatSeconds(83)).toBe('1:23');
    expect(formatSeconds(5)).toBe('0:05');
  });
  it('formats over an hour as H:MM:SS', () => {
    expect(formatSeconds(3723)).toBe('1:02:03');
  });
  it('clamps invalid input to 0:00', () => {
    expect(formatSeconds(-4)).toBe('0:00');
    expect(formatSeconds(NaN)).toBe('0:00');
  });
});

describe('extractYouTubeId', () => {
  it('handles watch URLs', () => {
    expect(extractYouTubeId('https://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    expect(extractYouTubeId('https://youtube.com/watch?list=x&v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });
  it('handles short, embed, shorts and live URLs', () => {
    expect(extractYouTubeId('https://youtu.be/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    expect(extractYouTubeId('https://www.youtube.com/embed/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    expect(extractYouTubeId('https://www.youtube.com/shorts/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    expect(extractYouTubeId('https://www.youtube.com/live/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });
  it('accepts a raw id and rejects junk', () => {
    expect(extractYouTubeId('dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    expect(extractYouTubeId('not a url')).toBeNull();
    expect(extractYouTubeId('')).toBeNull();
  });
});

describe('parseTranscriptSegments', () => {
  it('returns no timings for plain prose', () => {
    const { segments, hasTimings } = parseTranscriptSegments(
      'Welcome to the video.\nToday we build an app.\nThanks for watching.',
    );
    expect(hasTimings).toBe(false);
    expect(segments).toHaveLength(3);
    expect(segments[0].text).toBe('Welcome to the video.');
  });

  it('detects leading timestamps and enables timings', () => {
    const { segments, hasTimings } = parseTranscriptSegments(
      '[0:00] Intro to the topic\n[0:12] Main point one\n[1:05] Wrap up',
    );
    expect(hasTimings).toBe(true);
    expect(segments[0].startTime).toBe(0);
    expect(segments[1].startTime).toBe(12);
    expect(segments[2].startTime).toBe(65);
    // end time flows to the next start
    expect(segments[0].endTime).toBe(12);
    expect(segments[2].endTime).toBe(70);
  });

  it('extracts speaker labels', () => {
    const { segments } = parseTranscriptSegments('0:00 Alice: Hello there\n0:04 Bob: Hi Alice');
    expect(segments[0].speaker).toBe('Alice');
    expect(segments[0].text).toBe('Hello there');
    expect(segments[1].speaker).toBe('Bob');
  });

  it('handles empty input', () => {
    expect(parseTranscriptSegments('')).toEqual({ segments: [], hasTimings: false });
    expect(parseTranscriptSegments(null)).toEqual({ segments: [], hasTimings: false });
  });
});
