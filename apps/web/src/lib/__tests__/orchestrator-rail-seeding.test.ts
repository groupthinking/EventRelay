import { describe, expect, it } from 'vitest';
import { seededPromptDispatchKey } from '@/lib/orchestrator-rail-seeding';

describe('seededPromptDispatchKey', () => {
  it('returns null for empty prompts', () => {
    expect(seededPromptDispatchKey('', 'n1')).toBeNull();
    expect(seededPromptDispatchKey('   ', 'n1')).toBeNull();
  });

  it('includes nonce so repeated seeded prompts can be retriggered', () => {
    const prompt = 'Ask about this source';
    expect(seededPromptDispatchKey(prompt, 'n1')).toBe('n1::Ask about this source');
    expect(seededPromptDispatchKey(prompt, 'n2')).toBe('n2::Ask about this source');
  });

  it('normalizes whitespace before keying', () => {
    expect(seededPromptDispatchKey('  Ask about this source  ', 'n1')).toBe(
      'n1::Ask about this source',
    );
  });
});
