import { describe, expect, it } from 'vitest';
import {
  studioRunQuality,
  studioStatusLabel,
  studioStatusMessage,
} from '../studio-pipeline-status';

describe('studio-pipeline-status', () => {
  it('marks async backend kickoff as live', () => {
    expect(
      studioRunQuality(
        { ok: true, status: 200, pipeline: 'backend-async', jobId: 'job_1' },
        false,
        true,
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

  it('uses draft-only label when ready without live backend', () => {
    expect(studioStatusLabel('draft', 'ready')).toBe('Draft only');
    expect(studioStatusLabel('live', 'ready')).toBe('Backend connected');
  });

  it('explains dashboard handoff in ready draft message', () => {
    const msg = studioStatusMessage('draft', 'ready', 'App', false);
    expect(msg).toContain('Dashboard');
    expect(msg).toContain('planning draft');
  });
});