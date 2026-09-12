import { describe, expect, it } from 'vitest';
import { parseVerifiedBackendTranscript } from '@/lib/transcription-service';

const transcript = 'This is verified source speech with enough words and characters to pass the transcript evidence threshold.';

describe('parseVerifiedBackendTranscript', () => {
  it('preserves caption provenance and timestamps from the backend envelope', () => {
    const result = parseVerifiedBackendTranscript(
      {
        success: true,
        transcript: {
          text: transcript,
          source: 'youtube_transcript_api',
          segments: [{ start: 1, duration: 2, text: transcript }],
        },
      },
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );

    expect(result).toEqual(
      expect.objectContaining({
        success: true,
        verified: true,
        source: 'youtube_transcript_api',
        acquisitionMethod: 'backend-caption-api',
      }),
    );
    expect(result?.segments).toHaveLength(1);
  });

  it('rejects model-derived backend text instead of relabelling it captions', () => {
    const result = parseVerifiedBackendTranscript(
      {
        success: true,
        transcript: { text: transcript, source: 'gemini_video', segments: [] },
      },
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );

    expect(result).toBeNull();
  });

  it('rejects an unknown source even when the transcript is non-empty', () => {
    const result = parseVerifiedBackendTranscript(
      { success: true, transcript: { text: transcript, segments: [] } },
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );

    expect(result).toBeNull();
  });
});
