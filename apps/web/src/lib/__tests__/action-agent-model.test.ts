import { describe, it, expect, afterEach } from 'vitest';
import { resolveOpenAIActionModel, AVAILABLE_TOOL_NAMES } from '@/lib/action-agent';

const ORIGINAL = process.env.OPENAI_ACTION_MODEL;

afterEach(() => {
  if (ORIGINAL === undefined) delete process.env.OPENAI_ACTION_MODEL;
  else process.env.OPENAI_ACTION_MODEL = ORIGINAL;
});

describe('resolveOpenAIActionModel', () => {
  it('defaults to gpt-4o-mini when OPENAI_ACTION_MODEL is unset', () => {
    delete process.env.OPENAI_ACTION_MODEL;
    expect(resolveOpenAIActionModel()).toBe('gpt-4o-mini');
  });

  it('uses a configured Codex model on the Responses API', () => {
    process.env.OPENAI_ACTION_MODEL = 'codex-mini-latest';
    expect(resolveOpenAIActionModel()).toBe('codex-mini-latest');
  });

  it('trims whitespace and falls back to the default for blank values', () => {
    process.env.OPENAI_ACTION_MODEL = '  gpt-5-codex  ';
    expect(resolveOpenAIActionModel()).toBe('gpt-5-codex');

    process.env.OPENAI_ACTION_MODEL = '   ';
    expect(resolveOpenAIActionModel()).toBe('gpt-4o-mini');
  });

  it('resolves per call so runtime env changes take effect', () => {
    process.env.OPENAI_ACTION_MODEL = 'codex-mini-latest';
    expect(resolveOpenAIActionModel()).toBe('codex-mini-latest');
    process.env.OPENAI_ACTION_MODEL = 'gpt-4o-mini';
    expect(resolveOpenAIActionModel()).toBe('gpt-4o-mini');
  });
});

describe('action agent surface', () => {
  it('still exposes the executable tool registry', () => {
    expect(AVAILABLE_TOOL_NAMES).toContain('dispatch_agent');
    expect(AVAILABLE_TOOL_NAMES.length).toBeGreaterThan(0);
  });
});
