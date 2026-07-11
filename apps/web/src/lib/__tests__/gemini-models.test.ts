import { describe, expect, it } from 'vitest';

import {
  GEMINI_FAST_MODEL,
  GEMINI_SEARCH_MODEL,
  GEMINI_STRUCTURED_MODEL,
} from '@/lib/gemini-models';

describe('gemini-models defaults', () => {
  it('defaults to gemini-2.5-flash for pipeline workloads', () => {
    expect(GEMINI_FAST_MODEL).toBe('gemini-2.5-flash');
    expect(GEMINI_SEARCH_MODEL).toBe('gemini-2.5-flash');
    expect(GEMINI_STRUCTURED_MODEL).toBe('gemini-2.5-flash');
  });
});