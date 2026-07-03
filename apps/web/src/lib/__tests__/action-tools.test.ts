import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  ACTION_TOOLS,
  getTool,
  resolveBackendBaseUrl,
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
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ agent_id: 'a1', status: 'queued' })));

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
    const fetchImpl = vi.fn().mockResolvedValue(new Response('unavailable', { status: 503 }));

    const tool = getTool('add_to_knowledge_base')!;
    const res = await tool.execute(
      { insight: 'RAG improves recall', tags: ['rag'] },
      { backendBaseUrl: 'http://backend', fetchImpl },
    );
    expect(res.isError).toBe(true);
    expect(res.summary).toContain('503');
  });

  it('add_to_knowledge_base coerces non-array/invalid tags to a string array', async () => {
    // Fresh Response per call: this test invokes the tool twice, and a
    // Response body is single-use.
    const fetchImpl = vi
      .fn()
      .mockImplementation(async () => new Response(JSON.stringify({ stored: true })));

    const tool = getTool('add_to_knowledge_base')!;
    // tags arrives as a non-array (e.g. a stringified value from a provider).
    await tool.execute(
      { insight: 'x', tags: 'not-an-array' },
      { backendBaseUrl: 'http://backend', fetchImpl },
    );
    const body = JSON.parse((fetchImpl.mock.calls[0][1] as RequestInit).body as string);
    expect(body.tags).toEqual([]);

    // Mixed array drops non-string entries.
    fetchImpl.mockClear();
    await tool.execute(
      { insight: 'x', tags: ['a', 2, null, 'b'] },
      { backendBaseUrl: 'http://backend', fetchImpl },
    );
    const body2 = JSON.parse((fetchImpl.mock.calls[0][1] as RequestInit).body as string);
    expect(body2.tags).toEqual(['a', 'b']);
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
    expect(gemini[0]).toHaveProperty('parametersJsonSchema');
    expect(gemini[0]).not.toHaveProperty('strict');
  });
});

describe('resolveBackendBaseUrl', () => {
  const original = process.env.BACKEND_URL;
  afterEach(() => {
    if (original === undefined) delete process.env.BACKEND_URL;
    else process.env.BACKEND_URL = original;
  });

  it('returns null when unset or empty', () => {
    delete process.env.BACKEND_URL;
    expect(resolveBackendBaseUrl()).toBeNull();
    process.env.BACKEND_URL = '   ';
    expect(resolveBackendBaseUrl()).toBeNull();
  });

  it('returns null for non-http(s) or malformed values', () => {
    process.env.BACKEND_URL = 'ftp://example.com';
    expect(resolveBackendBaseUrl()).toBeNull();
    process.env.BACKEND_URL = 'not a url';
    expect(resolveBackendBaseUrl()).toBeNull();
    process.env.BACKEND_URL = 'localhost:8000'; // no scheme
    expect(resolveBackendBaseUrl()).toBeNull();
  });

  it('accepts http(s) URLs and trims trailing slashes', () => {
    process.env.BACKEND_URL = 'https://api.example.com';
    expect(resolveBackendBaseUrl()).toBe('https://api.example.com');
    process.env.BACKEND_URL = 'http://localhost:8000///';
    expect(resolveBackendBaseUrl()).toBe('http://localhost:8000');
  });
});

describe('backend auth headers on tool calls', () => {
  // Regression coverage for the #470 401 gap: the transcript action agent's
  // dispatch/ingest tools call non-public FastAPI endpoints, so they must send
  // X-API-Key (via backendHeaders) once EVENTRELAY_API_KEY is configured.
  const original = process.env.EVENTRELAY_API_KEY;
  afterEach(() => {
    if (original === undefined) delete process.env.EVENTRELAY_API_KEY;
    else process.env.EVENTRELAY_API_KEY = original;
  });

  it('dispatch_agent sends a trimmed X-API-Key when EVENTRELAY_API_KEY is set', async () => {
    process.env.EVENTRELAY_API_KEY = '  secret-key  '; // padded to prove trimming
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ agent_id: 'a1' })));
    await getTool('dispatch_agent')!.execute(
      { agentType: 'researcher', instruction: 'x' },
      { backendBaseUrl: 'http://backend', fetchImpl, jobId: 'job1' },
    );
    const headers = (fetchImpl.mock.calls[0][1] as RequestInit).headers as Record<string, string>;
    expect(headers['X-API-Key']).toBe('secret-key');
    expect(headers['Content-Type']).toBe('application/json');
  });

  it('add_to_knowledge_base sends X-API-Key when EVENTRELAY_API_KEY is set', async () => {
    process.env.EVENTRELAY_API_KEY = 'secret-key';
    const fetchImpl = vi.fn().mockResolvedValue(new Response(JSON.stringify({ stored: true })));
    await getTool('add_to_knowledge_base')!.execute(
      { insight: 'x', tags: ['a'] },
      { backendBaseUrl: 'http://backend', fetchImpl },
    );
    const headers = (fetchImpl.mock.calls[0][1] as RequestInit).headers as Record<string, string>;
    expect(headers['X-API-Key']).toBe('secret-key');
  });

  it('omits X-API-Key when EVENTRELAY_API_KEY is unset', async () => {
    delete process.env.EVENTRELAY_API_KEY;
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ agent_id: 'a1' })));
    await getTool('dispatch_agent')!.execute(
      { agentType: 'researcher', instruction: 'x' },
      { backendBaseUrl: 'http://backend', fetchImpl, jobId: 'job1' },
    );
    const headers = (fetchImpl.mock.calls[0][1] as RequestInit).headers as Record<string, string>;
    expect(headers['X-API-Key']).toBeUndefined();
    expect(headers['Content-Type']).toBe('application/json');
  });
});
