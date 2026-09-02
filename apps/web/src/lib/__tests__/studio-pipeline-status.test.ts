import { describe, expect, it } from 'vitest';
import {
  studioPackCitation,
  studioPasteOutcomeMessage,
  studioRunQuality,
  studioStatusLabel,
  studioStatusMessage,
} from '../studio-pipeline-status';

describe('studio-pipeline-status', () => {
  it('marks a job_id kickoff as draft until transcript or events exist', () => {
    expect(
      studioRunQuality(
        { ok: true, status: 200, pipeline: 'backend-async', jobId: 'job_1' },
        false,
        true,
      ),
    ).toBe('draft');
  });

  it('marks live when transcript or events are present', () => {
    expect(
      studioRunQuality(
        { ok: true, status: 200, pipeline: 'backend-async', jobId: 'job_1' },
        false,
        true,
        { transcript: 'x'.repeat(50), eventCount: 0 },
      ),
    ).toBe('live');
  });

  it('marks local fallback as draft', () => {
    expect(
      studioRunQuality(
        { ok: true, status: 200, pipeline: 'local-fallback' },
        false,
        true,
      ),
    ).toBe('draft');
  });

  it('uses no-transcript label when ready without payload', () => {
    expect(studioStatusLabel('draft', 'ready')).toBe('No transcript yet');
    expect(studioStatusLabel('live', 'ready')).toBe('Analysis ready');
  });

  it('shows the identity pack cite when transcript evidence is missing', () => {
    const citation = studioPackCitation({
      version: 'v0',
      videoId: 'jNQXAC9IVRw',
      packId: 'vp:v0:jNQXAC9IVRw',
      sourceHash: '97150a5c21eef3d12a4543ce2108ca28fd6f829db1da120d7e75655ab471f97d',
    });
    expect(citation).toBe(
      'cite:youtube:jNQXAC9IVRw · v0 · 97150a5c21eef3d12a4543ce2108ca28fd6f829db1da120d7e75655ab471f97d',
    );
    expect(
      studioPasteOutcomeMessage({
        hasUsableTranscript: false,
        packCitation: citation,
      }),
    ).toContain('cite:youtube:jNQXAC9IVRw');
    expect(
      studioPasteOutcomeMessage({
        hasUsableTranscript: false,
        packCitation: citation,
      }),
    ).toContain('97150a5c21eef3d12a4543ce2108ca28fd6f829db1da120d7e75655ab471f97d');
  });

  it('does not send the user to a second product when ready', () => {
    const draft = studioStatusMessage('draft', 'ready', 'App', false);
    const live = studioStatusMessage('live', 'ready', 'App', false);
    expect(draft.toLowerCase()).not.toContain('planning draft');
    expect(live.toLowerCase()).not.toContain('dashboard');
  });
});