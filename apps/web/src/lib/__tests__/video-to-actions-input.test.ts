import { describe, expect, it } from 'vitest';
import {
  buildActionAgentSource,
  buildSameRunActInput,
  sanitizeActEvents,
  usableProvidedTranscript,
} from '@/lib/video-to-actions-input';

describe('same-run Act payload', () => {
  it('keeps a usable Analyze transcript and drops a short one', () => {
    expect(usableProvidedTranscript('x'.repeat(39))).toBeUndefined();
    expect(usableProvidedTranscript(`  ${'x'.repeat(40)}  `)).toHaveLength(40);
  });

  it('buildSameRunActInput sends this run’s transcript and events', () => {
    const payload = buildSameRunActInput({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      videoTitle: 'Fixture',
      transcript: 'x'.repeat(50),
      events: [{ type: 'action', title: 'Ship', description: 'now' }, { title: '   ' }],
    });
    expect(payload.url).toContain('auJzb1D-fag');
    expect(payload.transcript).toHaveLength(50);
    expect(payload.events).toEqual([{ type: 'action', title: 'Ship', description: 'now' }]);
  });

  it('sanitizeActEvents ignores non-objects and empty titles', () => {
    expect(sanitizeActEvents(['nope', { title: '' }, null])).toBeUndefined();
    expect(sanitizeActEvents([{ title: 'Keep' }])).toEqual([{ title: 'Keep' }]);
  });

  it('buildActionAgentSource appends Analyze events without dropping them', () => {
    const source = buildActionAgentSource('spoken words from the video', [
      { type: 'action', title: 'Export', description: 'scaffold' },
    ]);
    expect(source).toContain('spoken words from the video');
    expect(source).toContain('EVENTS FROM ANALYZE');
    expect(source).toContain('Export');
  });
});
