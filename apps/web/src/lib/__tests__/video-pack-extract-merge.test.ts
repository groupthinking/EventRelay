import { describe, expect, it } from 'vitest';
import { mergeSectionVideoPackSpecs } from '@/lib/video-pack-extract-merge';

const baseSection = (overrides: Record<string, unknown> = {}) => ({
  transcript: {
    language: 'en',
    full_text: 'line one',
    segments: [{ idx: 0, start_s: 0, end_s: 4, text: 'line one' }],
  },
  keyframes: [],
  concepts: ['alpha'],
  requirements: [{ id: 'sec1-req-1', title: 'First', detail: 'd', priority: 'normal', tags: [] }],
  code_snippets: [],
  architecture: null,
  artifacts: [],
  stack: { tools: [{ name: 'MCP', evidence: 'spoken', kind: 'protocol' }] },
  visual_context: null,
  chapters: [],
  action_items: [],
  ...overrides,
});

describe('mergeSectionVideoPackSpecs', () => {
  it('dedupes stack tools and concatenates transcript segments in order', () => {
    const merged = mergeSectionVideoPackSpecs([
      baseSection(),
      baseSection({
        transcript: {
          language: 'en',
          full_text: 'line two',
          segments: [{ idx: 0, start_s: 10, end_s: 14, text: 'line two' }],
        },
        concepts: ['alpha', 'beta'],
        requirements: [{ id: 'sec2-req-1', title: 'Second', detail: 'd2', priority: 'normal', tags: [] }],
        stack: {
          tools: [
            { name: 'MCP', evidence: 'repeat', kind: 'protocol' },
            { name: 'Cloudflare', evidence: 'slide', kind: 'platform' },
          ],
        },
      }),
    ]);

    expect(merged.transcript.segments).toHaveLength(2);
    expect(merged.transcript.full_text).toContain('line one');
    expect(merged.transcript.full_text).toContain('line two');
    expect(merged.concepts).toEqual(['alpha', 'beta']);
    expect(merged.stack.tools.map((tool) => tool.name)).toEqual(['MCP', 'Cloudflare']);
    expect(merged.requirements).toHaveLength(2);
  });
});
