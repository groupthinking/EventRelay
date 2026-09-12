import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const openAiState = vi.hoisted(() => ({
  constructorOptions: [] as Array<Record<string, unknown> | undefined>,
  create: vi.fn(),
}));

vi.mock('openai', () => ({
  default: class OpenAIMock {
    responses = { create: openAiState.create };

    constructor(options?: Record<string, unknown>) {
      openAiState.constructorOptions.push(options);
    }
  },
}));

import { runActionAgent } from '@/lib/action-agent';

const TRANSCRIPT = 'A sufficiently long transcript describing a concrete task for the viewer to review.';

describe('action-agent provider routing', () => {
  beforeEach(() => {
    openAiState.constructorOptions.length = 0;
    openAiState.create.mockReset();
    openAiState.create.mockResolvedValue({ id: 'resp_test', output: [] });
    delete process.env.AI_GATEWAY_API_KEY;
    delete process.env.VERCEL_AI_GATEWAY_API_KEY;
    delete process.env.VERCEL_AI_GATEWAY_API;
    delete process.env.VERCEL_API_KEY;
    delete process.env.OPENAI_API_KEY;
    delete process.env.GEMINI_API_KEY;
    delete process.env.GOOGLE_API_KEY;
    delete process.env.Vertex_AI_API_KEY;
  });

  it('routes action planning through Vercel AI Gateway before a direct OpenAI key', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_gateway_test';
    process.env.OPENAI_API_KEY = 'sk_stale_direct_key';

    const result = await runActionAgent({ transcript: TRANSCRIPT, executeTools: false });

    expect(result.provider).toBe('gateway:google/gemini-2.5-flash');
    expect(openAiState.constructorOptions.at(-1)).toEqual({
      apiKey: 'vck_gateway_test',
      baseURL: 'https://ai-gateway.vercel.sh/v1',
    });
    expect(openAiState.create).toHaveBeenCalledWith(
      expect.objectContaining({ model: 'google/gemini-2.5-flash' }),
    );
  });

  it('reports Gateway as an accepted provider in the missing-key guard', async () => {
    await expect(runActionAgent({ transcript: TRANSCRIPT, executeTools: false })).rejects.toThrow(
      'Set AI_GATEWAY_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY',
    );
  });

  it('returns the first Gateway tool plan without executing or requesting another round', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_gateway_test';
    openAiState.create.mockResolvedValue({
      id: 'resp_plan',
      output: [
        {
          type: 'function_call',
          name: 'create_workflow_task',
          call_id: 'call_plan',
          arguments: JSON.stringify({ title: 'Review the multimodal prototype' }),
        },
      ],
    });

    const result = await runActionAgent({ transcript: TRANSCRIPT, executeTools: false });

    expect(openAiState.create).toHaveBeenCalledTimes(1);
    expect(result.actions).toEqual([
      expect.objectContaining({
        tool: 'create_workflow_task',
        input: { title: 'Review the multimodal prototype' },
        status: 'pending',
        isError: undefined,
      }),
    ]);
  });
});
