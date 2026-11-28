import { describe, expect, it } from 'vitest';
import { formatSrt, formatVtt, resolveCaptionSourceLabel } from '@/lib/transcript-export';

describe('transcript-export', () => {
  it('formats segments as SRT with HH:MM:SS,mmm timestamps and 4s default duration', () => {
    const srt = formatSrt([
      { text: 'Intro setup', start: 0 },
      { text: 'Configure pipeline', start: 65.5, duration: 3.25 },
      { text: 'Hour mark', start: 3661.005, duration: 2 },
    ]);

    expect(srt).toBe(
      [
        '1',
        '00:00:00,000 --> 00:00:04,000',
        'Intro setup',
        '',
        '2',
        '00:01:05,500 --> 00:01:08,750',
        'Configure pipeline',
        '',
        '3',
        '01:01:01,005 --> 01:01:03,005',
        'Hour mark',
        '',
      ].join('\n'),
    );
  });

  it('formats segments as WebVTT with WEBVTT header and HH:MM:SS.mmm timestamps', () => {
    const vtt = formatVtt([
      { text: 'First line', start: 12 },
      { text: 'Second line', start: 20, duration: 5.5 },
    ]);

    expect(vtt).toBe(
      [
        'WEBVTT',
        '',
        '00:00:12.000 --> 00:00:16.000',
        'First line',
        '',
        '00:00:20.000 --> 00:00:25.500',
        'Second line',
        '',
      ].join('\n'),
    );
  });

  it('handles empty segments and missing start values cleanly', () => {
    expect(formatSrt([])).toBe('');
    expect(formatVtt([])).toBe('WEBVTT\n\n');
    expect(formatSrt([{ text: '   ' }, { text: 'Kept line' }])).toBe(
      '1\n00:00:00,000 --> 00:00:04,000\nKept line\n',
    );
  });

  it('resolves caption source labels accurately', () => {
    expect(
      resolveCaptionSourceLabel({
        transcriptSource: 'youtube-transcript-api',
        timedSegmentCount: 12,
        hasTranscriptText: true,
      }),
    ).toBe('Timed captions');
    expect(
      resolveCaptionSourceLabel({
        transcriptSource: 'openai-stt',
        timedSegmentCount: 5,
        hasTranscriptText: true,
      }),
    ).toBe('ASR fallback');
    expect(
      resolveCaptionSourceLabel({
        timedSegmentCount: 0,
        hasTranscriptText: false,
      }),
    ).toBe('No captions available');
  });
});
