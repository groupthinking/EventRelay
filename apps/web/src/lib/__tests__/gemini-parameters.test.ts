import { describe, expect, it } from 'vitest';
import { geminiSampling } from '../gemini-parameters';

describe('Gemini sampling compatibility', () => {
  it.each(['gemini-3.5-flash', 'gemini-3.8-flash', 'google/gemini-3.8-flash', 'models/gemini-3-pro-preview', 'gemini-4-flash'])('omits sampling for %s', (model) => {
    expect(geminiSampling(model, 0.3)).toEqual({});
  });
  it.each(['gemini-2.5-flash', 'gemini-2.0-flash', 'gemma-3-27b-it', 'openai/gpt-4o', 'gemini-pro'])('preserves sampling for %s', (model) => {
    expect(geminiSampling(model, 0.3)).toEqual({ temperature: 0.3 });
  });
});
