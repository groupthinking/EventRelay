import { describe, expect, it } from 'vitest';
import { parsePackActionItems, parsePackChapters } from '@/lib/video-pack-types';

describe('parsePackChapters', () => {
  it('accepts start/end/topic/key_points and rejects prose-only rows', () => {
    const chapters = parsePackChapters([
      {
        start: 0,
        end: 42,
        topic: 'Intro',
        key_points: ['Define the problem', 'Show the stack'],
      },
      { start: 10, end: 5, topic: 'Bad range', key_points: ['nope'] },
      { topic: 'Missing times', key_points: ['nope'] },
      'prose only chapter blob',
    ]);

    expect(chapters).toEqual([
      {
        start: 0,
        end: 42,
        topic: 'Intro',
        key_points: ['Define the problem', 'Show the stack'],
      },
    ]);
  });

  it('maps start_s/end_s aliases from legacy model output', () => {
    expect(
      parsePackChapters([
        { start_s: 12, end_s: 90, topic: 'Build', key_points: ['Wire MCP gateway'] },
      ]),
    ).toEqual([{ start: 12, end: 90, topic: 'Build', key_points: ['Wire MCP gateway'] }]);
  });
});

describe('parsePackActionItems', () => {
  it('requires structured objects with title and description', () => {
    const items = parsePackActionItems([
      {
        id: 'a1',
        type: 'implementation',
        title: 'Ship the worker',
        description: 'Deploy the Cloudflare Worker that fronts x402.',
        difficulty: 'medium',
      },
      { title: 'Missing description' },
      'Do the thing in one prose blob',
    ]);

    expect(items).toEqual([
      {
        id: 'a1',
        type: 'implementation',
        title: 'Ship the worker',
        description: 'Deploy the Cloudflare Worker that fronts x402.',
        difficulty: 'medium',
        priority: null,
      },
    ]);
  });
});
