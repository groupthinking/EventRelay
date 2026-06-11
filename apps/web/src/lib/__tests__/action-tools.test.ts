import { describe, it, expect, vi } from 'vitest';
import {
  ACTION_TOOLS,
  getTool,
  toGeminiFunctionDeclarations,
  toOpenAITools,
  type ToolContext,
} from '@/lib/action-tools';

const NO_BACKEND: ToolContext = { backendBaseUrl: null };

describe('action tool registry', () => {
  it('exposes the exact declared set of named tools with object schemas', () => {
    const names = ACTION_TOOLS.map((t) => t.name);
    // Assert the full set so adding/removing/renaming a tool fails fast.
    expect([...names].sort()).toEqual(
      [
        'add_to_knowledge_base',
        'create_workflow_task',
        'dispatch_agent',
        'save_resource',
        'schedule_followup',
      ].sort(),
    );
    for (const t of ACTION_TOOLS) {
      expect(t.parameters.type).toBe('object');
      expect(t.parameters.additionalProperties).toBe(false);
      expect(Array.isArray(t.parameters.required)).toBe(true);
    }
  });

  it('getTool resolves by name and returns undefined for unknown tools', () => {
    expect(getTool('save_resource')?.name).toBe('save_resource');
    expect(getTool('nope')).toBeUndefined();
  });

  it('create_workflow_task produces real structured output (no fabrication)', async () => {
    const tool = getTool('create_workflow_task')!;
    const res = await tool.execute(
      { title: 'Install pnpm', description: 'Set up the toolchain', category: 'setup', priority: 'high' },
      NO_BACKEND,
    );
    expect(res.isError).toBeFalsy();
    expect(res.summary).toContain('Install pnpm');
    expect(res.data).toMatchObject({ title: 'Install pnpm', category: 'setup', priority: 'high' });
  });

  it('dispatch_agent reports honestly when no backend is configured', async () => {
    const tool = getTool('dispatch_agent')!;
    const res = await tool.execute(
      { agentType: 'code_generator', instruction: 'scaffold the app' },
      NO_BACKEND,
    );
    expect(res.isError).toBe(true);
    expect(res.summary).toMatch(/no backend configured/i);
  });

  it('dispatch_agent calls the backend when configured', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ agent_id: 'a1', status: 'queued' }),
    } as unknown as Response);

    const tool = getTool('dispatch_agent')!;
    const res = await tool.execute(
      { agentType: 'researcher', instruction: 'find benchmarks' },
      { backendBaseUrl: 'http://backend', fetchImpl, jobId: 'job1' },
    );

    expect(fetchImpl).toHaveBeenCalledOnce();
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('http://backend/api/v1/agents/dispatch');
    expect(JSON.parse((init as RequestInit).body as string)).toMatchObject({
      job_id: 'job1',
      agent_types: ['researcher'],
    });
    expect(res.isError).toBeFalsy();
    expect(res.data).toMatchObject({ agent_id: 'a1' });
  });

  it('add_to_knowledge_base surfaces a non-ok backend response as an error', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      text: async () => 'unavailable',
    } as unknown as Response);

    const tool = getTool('add_to_knowledge_base')!;
    const res = await tool.execute(
      { insight: 'RAG improves recall', tags: ['rag'] },
      { backendBaseUrl: 'http://backend', fetchImpl },
    );
    expect(res.isError).toBe(true);
    expect(res.summary).toContain('503');
  });

  it('adapts tools to OpenAI function-tool format', () => {
    const openai = toOpenAITools();
    expect(openai).toHaveLength(ACTION_TOOLS.length);
    expect(openai[0]).toMatchObject({ type: 'function', strict: true });
    expect(openai[0]).toHaveProperty('parameters');
  });

  it('adapts tools to Gemini functionDeclarations format', () => {
    const gemini = toGeminiFunctionDeclarations();
    expect(gemini).toHaveLength(ACTION_TOOLS.length);
    expect(gemini[0]).toHaveProperty('name');
    expect(gemini[0]).toHaveProperty('parameters');
    expect(gemini[0]).not.toHaveProperty('strict');
  });
});
