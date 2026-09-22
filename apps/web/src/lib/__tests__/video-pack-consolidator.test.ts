import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { JevEvaluatePayload } from '@/lib/billing/jev-lead-score';
import type { JevExtractAction, JevExtractDecision } from '@/lib/video-pack-extract-jev';
import type { TranscriptChunkEvidence } from '@/lib/transcript-team';
import {
  SANDBOX_BUILD_DEFAULT,
  consolidateShardExtract,
} from '@/lib/video-pack-consolidator';

const { experimental_evaluate, evaluationModel } = vi.hoisted(() => ({
  experimental_evaluate: vi.fn(),
  evaluationModel: vi.fn((modelId: string) => `evaluation:${modelId}`),
}));

vi.mock('ai', () => ({
  experimental_evaluate,
}));

vi.mock('@/lib/ai-gateway', () => ({
  aiGateway: { evaluationModel },
  GATEWAY_CHAT_MODEL: 'openai/gpt-4o',
}));

const { hasAiGatewayKey } = vi.hoisted(() => ({
  hasAiGatewayKey: vi.fn(),
}));

vi.mock('@/lib/vercel-ai-gateway', () => ({
  hasAiGatewayKey,
}));

const VIDEO_ID = 'auJzb1D-fag';

const POST_CHECK: readonly JevExtractAction[] = [
  'retry',
  'consolidate',
  'request-more-evidence',
  'stop',
];

beforeEach(() => {
  hasAiGatewayKey.mockReset();
  experimental_evaluate.mockReset();
  evaluationModel.mockClear();
  hasAiGatewayKey.mockReturnValue(false);
});

function section(overrides: Record<string, unknown> = {}) {
  return {
    transcript: {
      language: 'en',
      full_text: 'line one',
      segments: [{ idx: 0, start_s: 0, end_s: 4, text: 'line one' }],
    },
    keyframes: [],
    concepts: ['alpha'],
    requirements: [{ id: 'sec1-req-1', title: 'First', detail: 'd', priority: 'normal', tags: [] }],
    code_snippets: [] as Array<{ path_hint?: string | null; lang?: string | null; content: string }>,
    architecture: null,
    artifacts: [],
    stack: { tools: [{ name: 'MCP', evidence: 'spoken', kind: 'protocol' }] },
    visual_context: null,
    chapters: [],
    action_items: [],
    ...overrides,
  };
}

function evidence(
  index: number,
  bullets: string[],
  analyzed = true,
): TranscriptChunkEvidence {
  return {
    index,
    start_s: index * 10,
    end_s: index * 10 + 5,
    bullets,
    entities: bullets.length > 0 ? ['zoo'] : [],
    analyzed,
  };
}

function decision(action: JevExtractAction): JevExtractDecision {
  return {
    action,
    confidence: 0.81,
    probabilities: {
      chunk: 0,
      model: 0,
      retry: 0,
      consolidate: 0,
      'request-more-evidence': 0,
      stop: 0,
      [action]: 0.81,
    },
    rationale: '',
    model: 'typesafe-ai/jev',
  };
}

function choicePayload(choice: string): JevEvaluatePayload {
  return {
    answers: {
      extract_next: {
        type: 'choice',
        choice,
        probabilities: { [choice]: 0.81 },
      },
    },
    providerMetadata: { typesafe: { confidence: 0.81 } },
    response: { modelId: 'typesafe-ai/jev' },
  };
}

describe('consolidateShardExtract', () => {
  it('merges shard specs and transcript evidence into one tree', async () => {
    const result = await consolidateShardExtract({
      videoId: VIDEO_ID,
      specs: [
        section(),
        section({
          transcript: {
            language: 'en',
            full_text: 'line two',
            segments: [{ idx: 0, start_s: 10, end_s: 14, text: 'line two' }],
          },
          concepts: ['beta'],
          code_snippets: [{ path_hint: 'src/b.ts', lang: 'ts', content: 'export const b = 1;' }],
        }),
      ],
      transcriptEvidence: [
        evidence(1, ['later']),
        evidence(0, ['first']),
        evidence(0, ['dup'], false),
      ],
    });

    expect(result.tree.concepts).toEqual(['alpha', 'beta']);
    expect(result.tree.transcript.segments.map((segment) => segment.text)).toEqual([
      'line one',
      'line two',
    ]);
    expect(result.tree.code_snippets).toHaveLength(1);
    expect(result.tree.transcript_evidence).toEqual([
      expect.objectContaining({ index: 0, bullets: ['first'] }),
      expect.objectContaining({ index: 1, bullets: ['later'] }),
    ]);
    expect(result.app).toEqual({ ok: 1, failures: [] });
    expect(result.decision).toBeNull();
    expect(result.sandboxBuilt).toBe(false);
  });

  it('omits transcript_evidence when none was supplied', async () => {
    const result = await consolidateShardExtract({
      videoId: VIDEO_ID,
      specs: [section()],
    });
    expect(result.tree.transcript_evidence).toBeUndefined();
  });

  it('accepts a bare import listed in package.json', async () => {
    const result = await consolidateShardExtract({
      videoId: VIDEO_ID,
      specs: [
        section({
          code_snippets: [
            {
              path_hint: 'package.json',
              lang: 'json',
              content: JSON.stringify({
                dependencies: { zod: '^3.23.8' },
                devDependencies: { '@scope/pkg': '1.0.0' },
              }),
            },
            {
              path_hint: 'src/app.ts',
              lang: 'ts',
              content: [
                "import { z } from 'zod';",
                "import helper from '@scope/pkg/subpath';",
                "import local from './local';",
                "import fs from 'node:fs';",
                "import path from 'path';",
                'export const schema = z.string();',
              ].join('\n'),
            },
          ],
        }),
      ],
    });
    expect(result.app).toEqual({ ok: 1, failures: [] });
  });

  it('accepts empty code and relative or node imports without package.json', async () => {
    const empty = await consolidateShardExtract({
      videoId: VIDEO_ID,
      specs: [section()],
    });
    const local = await consolidateShardExtract({
      videoId: VIDEO_ID,
      specs: [
        section({
          code_snippets: [
            {
              path_hint: 'src/local.ts',
              lang: 'ts',
              content: "import fs from 'fs';\nimport { readFile } from 'node:fs/promises';\nexport const n = 1;",
            },
          ],
        }),
      ],
    });
    expect(empty.app.ok).toBe(1);
    expect(local.app.ok).toBe(1);
  });

  it.each([
    ['placeholder', 'export const zoo = placeholder;', 'placeholder'],
    ['ascii ellipsis', 'export function rest() { return ... }', 'ellipsis'],
    ['unicode ellipsis', 'export const cut = \u2026', 'ellipsis'],
    ['the word ellipsis', 'export const note = "ellipsis in the signature";', 'ellipsis'],
    ['rest of code here', 'export function run() { /* REST OF CODE HERE */ }', 'rest of code here'],
  ] as const)('fails 0/1 when code contains %s', async (_label, content, needle) => {
    const result = await consolidateShardExtract({
      videoId: VIDEO_ID,
      specs: [
        section({
          code_snippets: [{ path_hint: 'src/zoo.ts', lang: 'ts', content }],
        }),
      ],
    });
    expect(result.app.ok).toBe(0);
    expect(result.app.failures.join('\n').toLowerCase()).toContain(needle);
    expect(result.app.failures.join('\n')).toContain('src/zoo.ts');
  });

  it('fails when a bare import is missing from package.json', async () => {
    const result = await consolidateShardExtract({
      videoId: VIDEO_ID,
      specs: [
        section({
          code_snippets: [
            {
              path_hint: 'package.json',
              lang: 'json',
              content: JSON.stringify({ dependencies: { zod: '^3.23.8' } }),
            },
            {
              path_hint: 'src/app.ts',
              lang: 'ts',
              content: "import leftPad from 'left-pad';\nexport const n = leftPad('1', 2);",
            },
          ],
        }),
      ],
    });
    expect(result.app.ok).toBe(0);
    expect(result.app.failures).toEqual([
      "src/app.ts: import 'left-pad' is missing from package.json",
    ]);
  });

  it('fails when package.json is not valid JSON', async () => {
    const result = await consolidateShardExtract({
      videoId: VIDEO_ID,
      specs: [
        section({
          code_snippets: [{ path_hint: 'package.json', lang: 'json', content: '{ not json' }],
        }),
      ],
    });
    expect(result.app.ok).toBe(0);
    expect(result.app.failures).toEqual(['package.json: package.json is not valid JSON']);
  });

  it('does not let a consolidate decision set or flip ok', async () => {
    const decide = vi.fn(async () => decision('consolidate'));
    const result = await consolidateShardExtract(
      {
        videoId: VIDEO_ID,
        specs: [
          section({
            code_snippets: [
              { path_hint: 'src/zoo.ts', lang: 'ts', content: 'export const zoo = placeholder;' },
            ],
          }),
        ],
      },
      { decide },
    );
    expect(result.app.ok).toBe(0);
    expect(result.decision?.action).toBe('consolidate');
    expect(result.decision).not.toHaveProperty('ok');
    expect(decide).toHaveBeenCalledWith(
      expect.objectContaining({
        videoId: VIDEO_ID,
        stage: 'merged',
        shardCount: 1,
        validationFailures: result.app.failures,
      }),
      expect.objectContaining({ actions: POST_CHECK }),
    );
  });

  it.each(['chunk', 'model'] as const)('drops a %s post-check decision', async (action) => {
    const result = await consolidateShardExtract(
      { videoId: VIDEO_ID, specs: [section()] },
      { decide: async () => decision(action) },
    );
    expect(result.decision).toBeNull();
    expect(result.app.ok).toBe(1);
  });

  it.each(POST_CHECK)('passes through a %s post-check decision', async (action) => {
    const result = await consolidateShardExtract(
      { videoId: VIDEO_ID, specs: [section()] },
      { decide: async () => decision(action) },
    );
    expect(result.decision?.action).toBe(action);
    expect(result.decision).not.toHaveProperty('ok');
  });

  it('asks Jev only for post-check actions on the merged state', async () => {
    hasAiGatewayKey.mockReturnValue(true);
    experimental_evaluate.mockResolvedValue(choicePayload('retry'));
    const result = await consolidateShardExtract({
      videoId: VIDEO_ID,
      specs: [section(), section({ concepts: ['beta'] })],
      durationSeconds: 620,
      attempt: 2,
    });
    expect(experimental_evaluate).toHaveBeenCalledTimes(1);
    const call = experimental_evaluate.mock.calls[0]?.[0] as {
      state: string;
      questions: { extract_next: { criteria: Record<string, string> } };
    };
    expect(Object.keys(call.questions.extract_next.criteria).sort()).toEqual([
      'consolidate',
      'request-more-evidence',
      'retry',
      'stop',
    ]);
    expect(call.state).toContain('merged Video Pack');
    expect(call.state).toContain(VIDEO_ID);
    expect(call.state).toContain('attempt: 2');
    expect(result.decision?.action).toBe('retry');
    expect(result.decision).not.toHaveProperty('ok');
  });

  it('skips Jev without a gateway secret and still returns the tree', async () => {
    hasAiGatewayKey.mockReturnValue(false);
    const result = await consolidateShardExtract({
      videoId: VIDEO_ID,
      specs: [section(), section({ concepts: ['beta'] })],
    });
    expect(experimental_evaluate).not.toHaveBeenCalled();
    expect(result.decision).toBeNull();
    expect(result.tree.concepts).toEqual(['alpha', 'beta']);
  });

  it('leaves the sandbox builder idle unless the flag is on', async () => {
    expect(SANDBOX_BUILD_DEFAULT).toBe(false);
    const buildSandbox = vi.fn();
    const idle = await consolidateShardExtract(
      { videoId: VIDEO_ID, specs: [section()] },
      { buildSandbox },
    );
    const built = await consolidateShardExtract(
      { videoId: VIDEO_ID, specs: [section()], sandboxBuild: true },
      { buildSandbox, decide: async () => null },
    );
    const stopped = await consolidateShardExtract(
      { videoId: VIDEO_ID, specs: [section()], sandboxBuild: true },
      { buildSandbox, decide: async () => decision('stop') },
    );
    const unbuilt = await consolidateShardExtract(
      { videoId: VIDEO_ID, specs: [section()], sandboxBuild: true },
      { decide: async () => null },
    );
    expect(idle.sandboxBuilt).toBe(false);
    expect(built.sandboxBuilt).toBe(true);
    expect(buildSandbox).toHaveBeenCalledTimes(1);
    expect(stopped.sandboxBuilt).toBe(false);
    expect(stopped.decision?.action).toBe('stop');
    expect(unbuilt.sandboxBuilt).toBe(false);
  });
});
