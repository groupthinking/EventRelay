import { describe, expect, it } from 'vitest';
import { hasRichDashboardInsights, isThinDashboardAnalysis } from '../dashboard-analysis';

describe('dashboard-analysis', () => {
  it('detects thin complete analysis', () => {
    expect(
      isThinDashboardAnalysis({
        insights: { summary: 'Analysis complete', actions: [], sentiment: 'Neutral', topics: [] },
        transcript: '',
        events: [],
      }),
    ).toBe(true);
  });

  it('treats actionable insights as rich', () => {
    const video = {
      insights: {
        summary: 'Analysis complete',
        actions: [{ title: 'Ship', description: 'd', category: 'build' }],
        sentiment: 'Neutral',
        topics: [],
      },
      transcript: '',
      events: [],
    };
    expect(isThinDashboardAnalysis(video)).toBe(false);
    expect(hasRichDashboardInsights(video)).toBe(true);
  });
});