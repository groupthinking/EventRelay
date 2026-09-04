import { afterEach, describe, expect, it, vi } from 'vitest';
import { GOLDEN_IDENTITY_HASHES, applyExtractedSpec, buildIdentityPack } from '@/lib/video-pack';
import { parseArchitecture, parseArtifacts } from '@/lib/video-pack-types';
import {
  VIDEO_PACK_EXTRACTOR_MODEL,
  VideoPackExtractError,
  extractVideoPackSpec,
  type VideoPackGenerateText,
} from '@/lib/video-pack-extractor';

const CANON = 'auJzb1D-fag';
const SOURCE_URL = `https://www.youtube.com/watch?v=${CANON}`;

const SPEC_JSON = {
  transcript: {
    language: 'en',
    full_text: 'Me at the zoo. The elephants have really long trunks.',
    segments: [{ idx: 0, start_s: 0, end_s: 5.2, text: 'Me at the zoo.' }],
  },
  keyframes: [{ t_s: 1.2, desc: 'Elephants at the enclosure' }],
  concepts: ['zoo', 'elephants'],
  requirements: [
    {
      id: 'req-1',
      title: 'Show the enclosure',
      detail: 'The speaker points at the elephants.',
      priority: 'normal',
      tags: ['visual'],
    },
  ],
  code_snippets: [],
  artifacts: [],
  stack: { tools: [] },
  visual_context: {
    visual_elements: [
      {
        timestamp: 1.2,
        element_type: 'scene',
        content: 'Elephants behind a fence',
        confidence: 0.9,
      },
    ],
    summary: 'Short zoo clip with elephants',
    frame_analysis_count: 1,
  },
};

const MNNFAT_ID = 'MNNfat_QP0E';
const MNNFAT_URL = `https://www.youtube.com/watch?v=${MNNFAT_ID}`;

/** Cloudflare / x402 evidence — must not invent Shopify. */
const MNNFAT_SPEC_JSON = {
  transcript: {
    language: 'en',
    full_text:
      'Decode frames, run multimodal temporal Q and A, then an agentic build that verifies against Cloudflare Workers and an x402 MCP gateway.',
    segments: [
      {
        idx: 0,
        start_s: 12,
        end_s: 28,
        text: 'Cloudflare Workers front the x402 payment rail and the MCP gateway.',
      },
    ],
  },
  keyframes: [{ t_s: 14, desc: 'Architecture slide: decode to x402 gateway' }],
  concepts: ['Cloudflare', 'x402', 'MCP', 'multimodal Q/A'],
  requirements: [
    {
      id: 'req-1',
      title: 'Stand up the x402 MCP gateway',
      detail: 'Workers terminate paid tool calls.',
      priority: 'high',
      tags: ['cloudflare', 'x402'],
    },
  ],
  code_snippets: [
    {
      path_hint: 'src/mcp_x402_gateway.ts',
      lang: 'ts',
      content: 'export function createGateway(config: GatewayConfig): Gateway',
    },
  ],
  architecture: {
    summary: 'Decode, multimodal temporal Q/A, agentic build/verify, monetization rails.',
    stages: [
      { id: 'decode', name: 'decode', description: 'Frame and audio decode' },
      { id: 'qa', name: 'multimodal temporal Q/A', description: 'Video question answering' },
      { id: 'build', name: 'agentic build/verify', description: 'Build engine checks artifacts' },
      { id: 'rails', name: 'monetization rails', description: 'Cloudflare Workers + x402' },
    ],
    mermaid:
      'flowchart LR\ndecode-->qa-->build-->rails',
  },
  artifacts: [
    {
      path_hint: 'src/spdl_decoder.py',
      purpose: 'Decode video/audio frames for the QA agent',
      interface: 'decode(uri: str) -> FrameBatch',
      signatures: ['def decode(uri: str) -> FrameBatch'],
    },
    {
      path_hint: 'src/video_qa_agent.py',
      purpose: 'Multimodal temporal question answering',
      interface: 'ask(batch: FrameBatch, question: str) -> Answer',
    },
    {
      path_hint: 'src/build_engine.ts',
      purpose: 'Verify generated artifacts against the pack',
      interface: 'verify(artifacts: Artifact[]) -> VerifyReport',
    },
    {
      path_hint: 'src/mcp_x402_gateway.ts',
      purpose: 'Paid MCP tool gateway on Cloudflare Workers',
      interface: 'createGateway(config: GatewayConfig): Gateway',
    },
  ],
  stack: {
    tools: [
      { name: 'Cloudflare', evidence: 'Workers front the paid rail', kind: 'platform' },
      { name: 'x402', evidence: 'payment rail named on slide', kind: 'protocol' },
      { name: 'MCP', evidence: 'MCP gateway in the architecture', kind: 'protocol' },
      { name: 'Cloudflare Workers', evidence: 'spoken + on-screen', kind: 'product' },
    ],
  },
  visual_context: {
    visual_elements: [
      {
        timestamp: 14,
        element_type: 'diagram',
        content: 'Pipeline: decode → QA → build → x402 gateway',
        confidence: 0.88,
      },
    ],
    summary: 'Cloudflare and x402 architecture slide',
    frame_analysis_count: 1,
  },
};

afterEach(() => {
  delete process.env.AI_GATEWAY_API_KEY;
  delete process.env.VERCEL_AI_GATEWAY_API_KEY;
  vi.restoreAllMocks();
});

describe('VIDEO_PACK_EXTRACTOR_MODEL', () => {
  it('pins google/gemini-3.8-flash and does not default to 2.5-flash', () => {
    expect(VIDEO_PACK_EXTRACTOR_MODEL).toBe('google/gemini-3.8-flash');
    expect(VIDEO_PACK_EXTRACTOR_MODEL).not.toContain('2.5-flash');
  });
});

describe('extractVideoPackSpec', () => {
  it('fails closed when AI Gateway is not configured', async () => {
    delete process.env.AI_GATEWAY_API_KEY;
    delete process.env.VERCEL_AI_GATEWAY_API_KEY;
    const generateText = vi.fn();

    await expect(
      extractVideoPackSpec({ sourceUrl: SOURCE_URL, videoId: CANON }, { generateText }),
    ).rejects.toThrow(/AI Gateway/i);
    expect(generateText).not.toHaveBeenCalled();
  });

  it('calls generateText with google/gemini-3.8-flash and the YouTube video file', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const generateText = vi.fn<VideoPackGenerateText>(async () => ({
      text: JSON.stringify(SPEC_JSON),
    }));

    const spec = await extractVideoPackSpec(
      { sourceUrl: SOURCE_URL, videoId: CANON },
      { generateText },
    );

    expect(spec.transcript.full_text).toContain('elephants');
    expect(spec.concepts).toEqual(['zoo', 'elephants']);
    expect(generateText).toHaveBeenCalledTimes(1);
    const args = generateText.mock.calls[0]?.[0];
    expect(args).toBeDefined();
    if (!args) {
      throw new Error('generateText was not called');
    }
    expect(args.model).toBe('google/gemini-3.8-flash');
    const parts = args.messages[0]?.content ?? [];
    const filePart = parts.find((part) => part.type === 'file');
    expect(filePart && filePart.type === 'file' ? filePart.mediaType : undefined).toMatch(/^video\//);
    expect(filePart && filePart.type === 'file' ? String(filePart.data) : undefined).toBe(SOURCE_URL);
  });

  it('fails closed when Gateway returns empty or identity-only cite text', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const generateText = vi.fn(async () => ({
      text: JSON.stringify({
        transcript: { language: null, full_text: `cite:youtube:${CANON}`, segments: [] },
        keyframes: [],
        concepts: [],
        requirements: [],
        code_snippets: [],
        visual_context: null,
      }),
    }));

    await expect(
      extractVideoPackSpec({ sourceUrl: SOURCE_URL, videoId: CANON }, { generateText }),
    ).rejects.toBeInstanceOf(VideoPackExtractError);
  });

  it('asks Gemini for architecture, artifacts, and grounded stack.tools — not a Shopify dump', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const generateText = vi.fn<VideoPackGenerateText>(async (args) => {
      const textPart = args.messages[0]?.content.find((part) => part.type === 'text');
      const prompt = textPart && textPart.type === 'text' ? textPart.text : '';
      expect(prompt).toMatch(/architecture/i);
      expect(prompt).toMatch(/artifacts/i);
      expect(prompt).toMatch(/stack\.tools/i);
      expect(prompt).toMatch(/grounded/i);
      expect(prompt).not.toMatch(/shopify cli/i);
      return { text: JSON.stringify(MNNFAT_SPEC_JSON) };
    });

    const spec = await extractVideoPackSpec(
      { sourceUrl: MNNFAT_URL, videoId: MNNFAT_ID },
      { generateText },
    );

    expect(spec.architecture?.stages.map((stage) => stage.id)).toEqual([
      'decode',
      'qa',
      'build',
      'rails',
    ]);
    expect(spec.architecture?.mermaid).toMatch(/decode-->qa-->build-->rails/);
    expect(spec.artifacts.map((item) => item.path_hint)).toEqual([
      'src/spdl_decoder.py',
      'src/video_qa_agent.py',
      'src/build_engine.ts',
      'src/mcp_x402_gateway.ts',
    ]);
    expect(spec.artifacts.every((item) => item.purpose && item.interface)).toBe(true);
    expect(spec.stack.tools.map((tool) => tool.name)).toEqual([
      'Cloudflare',
      'x402',
      'MCP',
      'Cloudflare Workers',
    ]);
    expect(JSON.stringify(spec.stack.tools)).not.toMatch(/shopify/i);
    expect(spec.artifacts.some((item) => /decode\(|ask\(|verify\(|createGateway\(/.test(item.interface))).toBe(true);
    expect(spec.artifacts.every((item) => (item.stubs?.join('\n').length ?? 0) < 800)).toBe(true);
  });

  it('truncates wall-of-code snippet dumps instead of persisting a chat paste', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const wall = Array.from({ length: 80 }, (_, i) => `console.log(${i});`).join('\n');
    const generateText = vi.fn<VideoPackGenerateText>(async () => ({
      text: JSON.stringify({
        ...MNNFAT_SPEC_JSON,
        code_snippets: [{ path_hint: 'src/dump.ts', lang: 'ts', content: wall }],
        artifacts: [
          {
            path_hint: 'src/dump.ts',
            purpose: 'Should stay a signature',
            interface: 'run(): void',
            stubs: [wall],
          },
        ],
      }),
    }));

    const spec = await extractVideoPackSpec(
      { sourceUrl: MNNFAT_URL, videoId: MNNFAT_ID },
      { generateText },
    );
    expect(spec.code_snippets[0]?.content.length).toBeLessThanOrEqual(800);
    expect(spec.artifacts[0]?.stubs?.join('\n').length ?? 0).toBeLessThanOrEqual(800);
  });

  it('keeps a mermaid-only architecture as real spec content, not identity-only cite', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const generateText = vi.fn<VideoPackGenerateText>(async () => ({
      text: JSON.stringify({
        transcript: { language: null, full_text: `cite:youtube:${MNNFAT_ID}`, segments: [] },
        keyframes: [],
        concepts: [],
        requirements: [],
        code_snippets: [],
        architecture: {
          summary: 'On-screen pipeline',
          mermaid: 'flowchart LR\ndecode-->rails',
        },
        artifacts: [],
        stack: { tools: [] },
        visual_context: null,
      }),
    }));

    const spec = await extractVideoPackSpec(
      { sourceUrl: MNNFAT_URL, videoId: MNNFAT_ID },
      { generateText },
    );
    expect(spec.architecture?.mermaid).toMatch(/decode-->rails/);
    expect(spec.architecture?.summary).toBe('On-screen pipeline');
    expect(spec.artifacts).toEqual([]);
    expect(spec.stack.tools).toEqual([]);
  });
});

describe('formation parsers', () => {
  it('rejects whitespace-only artifact cards', () => {
    expect(
      parseArtifacts([
        { path_hint: '   ', purpose: 'real', interface: 'run(): void' },
        { path_hint: 'src/ok.ts', purpose: '  ', interface: 'run(): void' },
        { path_hint: 'src/ok.ts', purpose: 'decode', interface: '   ' },
        { path_hint: 'src/ok.ts', purpose: 'decode', interface: 'run(): void' },
      ]),
    ).toEqual([
      { path_hint: 'src/ok.ts', purpose: 'decode', interface: 'run(): void' },
    ]);
  });

  it('caps signatures to one shared 800-character budget', () => {
    const lines = Array.from({ length: 40 }, (_, i) => `sig_${String(i).padStart(2, '0')} ${'x'.repeat(40)}`);
    const [artifact] = parseArtifacts([
      {
        path_hint: 'src/ok.ts',
        purpose: 'decode',
        interface: 'run(): void',
        signatures: lines,
      },
    ]);
    const total = artifact?.signatures?.join('').length ?? 0;
    expect(total).toBeLessThanOrEqual(800);
    expect(parseArchitecture({ summary: '  pipeline  ', mermaid: 'flowchart LR\na-->b' })?.summary).toBe(
      'pipeline',
    );
  });
});

describe('applyExtractedSpec', () => {
  it('keeps the identity hash contract and fills spec fields', () => {
    const identity = buildIdentityPack(CANON, SOURCE_URL, '2026-09-03T00:00:00.000Z');
    const merged = applyExtractedSpec(identity, SPEC_JSON);

    expect(merged.version).toBe('v0');
    expect(merged.video_id).toBe(CANON);
    expect(merged.source_url).toBe(SOURCE_URL);
    expect(merged.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON]);
    expect(merged.provenance.source_hash).toBe(identity.provenance.source_hash);
    expect(merged.transcript.full_text).not.toBe(`cite:youtube:${CANON}`);
    expect(merged.concepts).toEqual(['zoo', 'elephants']);
    expect(merged.requirements[0]?.title).toBe('Show the enclosure');
    expect(merged.keyframes[0]?.desc).toBe('Elephants at the enclosure');
    expect(merged.provenance.tool_versions.extractor).toBe('google/gemini-3.8-flash');
  });

  it('copies architecture, artifacts, and stack.tools without changing source_hash', () => {
    const identity = buildIdentityPack(MNNFAT_ID, MNNFAT_URL, '2026-09-03T00:00:00.000Z');
    const beforeHash = identity.provenance.source_hash;
    const merged = applyExtractedSpec(identity, MNNFAT_SPEC_JSON);

    expect(merged.provenance.source_hash).toBe(beforeHash);
    expect(merged.provenance.source_hash).not.toBe(GOLDEN_IDENTITY_HASHES[CANON]);
    expect(merged.architecture?.stages).toHaveLength(4);
    expect(merged.artifacts).toHaveLength(4);
    expect(merged.stack.tools.map((tool) => tool.name)).toEqual(
      expect.arrayContaining(['Cloudflare', 'x402', 'MCP']),
    );
    expect(JSON.stringify(merged.stack)).not.toMatch(/shopify/i);
  });
});
