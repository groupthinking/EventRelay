import { describe, expect, it } from 'vitest';
import { buildIdentityPack } from '@/lib/video-pack';
import { resolveVideoPackPlanResponse } from '@/lib/video-pack-plan';

describe('Video Pack planner', () => {
  const pack = buildIdentityPack('auJzb1D-fag');
  pack.transcript.full_text = 'A video about a workflow.';

  it('keeps every user-supplied tool and separates them from pack evidence', () => {
    const tools = Array.from({ length: 9 }, (_, index) => `Tool-${index + 1}`);
    const response = resolveVideoPackPlanResponse({
      query: 'Plan a build from this Video Pack',
      pack,
      planInterview: {
        useCase: 'Focus workflow',
        trigger: 'Weekdays',
        tools,
        constraints: 'No notifications at night',
        successSignal: 'Five sessions each week',
      },
    });

    expect(response?.requiresInterview).toBe(false);
    if (response?.requiresInterview === false) {
      expect(response.interview.tools).toEqual(tools);
      expect(response.answer).toContain('Tool-9');
      expect(response.answer).toContain('LSP: No explicit evidence');
      expect(response.answer).toContain('MCP: No explicit evidence');
      expect(response.answer).toContain('Pack-extracted cues');
    }
  });

  it('continues interview without repeating the planning phrase', () => {
    const response = resolveVideoPackPlanResponse({
      query: 'useCase: Focus workflow',
      planIntent: true,
      planInterview: { useCase: 'Focus workflow' },
      pack,
    });
    expect(response?.requiresInterview).toBe(true);
  });

  it('uses full transcript when there are no segments and retains all extracted tools', () => {
    const sourcePack = buildIdentityPack('auJzb1D-fag');
    sourcePack.transcript.full_text = 'The video calls for a React frontend and a test runner.';
    sourcePack.stack.tools = Array.from({ length: 9 }, (_, index) => ({ name: `PackTool-${index + 1}` }));
    const response = resolveVideoPackPlanResponse({
      query: 'Plan a build from this Video Pack',
      pack: sourcePack,
      planInterview: {
        useCase: 'A source-bound app',
        trigger: 'Manual action',
        tools: ['Git'],
        constraints: 'Cite the source',
        successSignal: 'Passing test',
      },
    });
    expect(response?.requiresInterview).toBe(false);
    if (response?.requiresInterview === false) {
      expect(response.answer).toContain('[transcript] The video calls for a React frontend');
      expect(response.answer).toContain('Frontend: [transcript]');
      expect(response.answer).toContain('[pack tool PackTool-9] PackTool-9');
    }
  });
});
