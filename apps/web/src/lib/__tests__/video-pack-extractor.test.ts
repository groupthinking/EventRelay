import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  GOLDEN_IDENTITY_HASHES,
  KEYFRAME_IMAGES_OK,
  KEYFRAME_IMAGES_OK_NOTE,
  KEYFRAME_IMAGES_OK_STILLS_NOTE,
  KEYFRAME_IMAGES_PARTIAL,
  KEYFRAME_IMAGES_PARTIAL_NOTE,
  applyExtractedSpec,
  applyKeyframeImageHonesty,
  buildIdentityPack,
} from '@/lib/video-pack';
import {
  KEYFRAME_JPEG_CONTENT_TYPE,
  hydrateKeyframeImages,
  isDurableCapturedImagePath,
  resetKeyframeFrameCaptureForTests,
  setKeyframeFrameCaptureForTests,
} from '@/lib/keyframe-frame-capture';
import { parseArchitecture, parseArtifacts } from '@/lib/video-pack-types';
import {
  VIDEO_PACK_EXTRACTOR_MODEL,
  VideoPackExtractError,
  extractVideoPackSpec,
  type VideoPackGenerateText,
} from '@/lib/video-pack-extractor';

const CANON = 'auJzb1D-fag';
const SOURCE_URL = `https://www.youtube.com/watch?v=${CANON}`;

/** Live Eggs GET/pack failure class — Gemini cut mid-string around position 8050. */
const EGGS_ID = 'vuLPccrooHU';
const EGGS_URL = `https://www.youtube.com/watch?v=${EGGS_ID}`;
const EGGS_SPOKEN =
  'Eggs tutorial: function bake() { return omelette; } crack the shell then whisk. ';

function jsonParseError(raw: string): string {
  try {
    JSON.parse(raw);
    throw new Error('expected JSON.parse to fail');
  } catch (error) {
    if (error instanceof Error && error.message === 'expected JSON.parse to fail') {
      throw error;
    }
    return error instanceof Error ? error.message : String(error);
  }
}

function jsonParsePosition(message: string): number | null {
  const match = /position\s+(\d+)/i.exec(message);
  return match ? Number(match[1]) : null;
}

/**
 * Build the production failure class: unterminated string at ~8050 where the
 * last `}` lives inside the cut string, so first-{ to last-} salvage also fails.
 */
function buildMidStringTruncationAt(cutAt = 8050): {
  truncated: string;
  spokenPrefix: string;
  parseError: string;
} {
  const prefix = '{"transcript":{"language":"en","full_text":"';
  let spoken = EGGS_SPOKEN;
  while (prefix.length + spoken.length < cutAt + 400) {
    spoken += EGGS_SPOKEN;
  }
  const truncated = (prefix + spoken).slice(0, cutAt);
  const spokenPrefix = spoken.slice(0, cutAt - prefix.length);
  return { truncated, spokenPrefix, parseError: jsonParseError(truncated) };
}

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

  it('asks Gemini for keyframe t_s + desc only and forbids invented image_path URLs', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const generateText = vi.fn<VideoPackGenerateText>(async (args) => {
      const textPart = args.messages[0]?.content.find((part) => part.type === 'text');
      const prompt = textPart && textPart.type === 'text' ? textPart.text : '';
      expect(prompt).toMatch(/keyframes: \[{ t_s, desc }\]/);
      expect(prompt).toMatch(/Do not (emit|invent) image_path/i);
      expect(prompt).not.toMatch(/keyframes: \[{ t_s, desc, image_path }\]/);
      return { text: JSON.stringify(SPEC_JSON) };
    });

    await extractVideoPackSpec({ sourceUrl: SOURCE_URL, videoId: CANON }, { generateText });
    expect(generateText).toHaveBeenCalledTimes(1);
  });

  it('keeps desc-only keyframes and leaves image_path null (no captured asset)', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const generateText = vi.fn<VideoPackGenerateText>(async () => ({
      text: JSON.stringify(SPEC_JSON),
    }));

    const spec = await extractVideoPackSpec(
      { sourceUrl: SOURCE_URL, videoId: CANON },
      { generateText },
    );

    expect(spec.keyframes).toHaveLength(1);
    expect(spec.keyframes[0]?.t_s).toBe(1.2);
    expect(spec.keyframes[0]?.desc).toBe('Elephants at the enclosure');
    expect(spec.keyframes[0]?.image_path).toBeNull();
  });

  it('strips Gemini-invented image_path instead of persisting a hallucinated URL', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const invented = 'https://i.ytimg.com/vi/QjZ5ohr7sGA/hqdefault.jpg';
    const generateText = vi.fn<VideoPackGenerateText>(async () => ({
      text: JSON.stringify({
        ...SPEC_JSON,
        keyframes: [
          { t_s: 1.2, desc: 'Elephants at the enclosure', image_path: invented },
          { t_s: 4, desc: 'Close-up trunk', image_path: '/tmp/frame-4.png' },
        ],
      }),
    }));

    const spec = await extractVideoPackSpec(
      { sourceUrl: SOURCE_URL, videoId: CANON },
      { generateText },
    );

    expect(spec.keyframes).toHaveLength(2);
    expect(spec.keyframes.every((frame) => frame.image_path === null)).toBe(true);
    expect(JSON.stringify(spec.keyframes)).not.toContain(invented);
    expect(JSON.stringify(spec.keyframes)).not.toContain('/tmp/frame-4.png');
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

  it('salvages Gemini JSON truncated mid-string at position ~8050 (Eggs / vuLPccrooHU class)', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const { truncated, spokenPrefix, parseError } = buildMidStringTruncationAt(8050);

    expect(truncated).toHaveLength(8050);
    expect(parseError).toMatch(/Unterminated string in JSON at position 8050/i);
    expect(jsonParsePosition(parseError)).toBe(8050);
    const lastBrace = truncated.lastIndexOf('}');
    expect(lastBrace).toBeGreaterThan(0);
    expect(jsonParseError(truncated.slice(truncated.indexOf('{'), lastBrace + 1))).toMatch(
      /Unterminated string in JSON/i,
    );

    const generateText = vi.fn<VideoPackGenerateText>(async () => ({ text: truncated }));
    const spec = await extractVideoPackSpec(
      { sourceUrl: EGGS_URL, videoId: EGGS_ID },
      { generateText },
    );

    expect(spec.transcript.language).toBe('en');
    expect(spec.transcript.full_text).toBe(spokenPrefix);
    expect(spec.transcript.full_text.startsWith('Eggs tutorial:')).toBe(true);
    expect(spec.transcript.full_text.endsWith(spokenPrefix.slice(-16))).toBe(true);
    expect(spec.concepts).toEqual([]);
    expect(spec.requirements).toEqual([]);
    expect(spec.stack.tools).toEqual([]);
    expect(JSON.stringify(spec)).not.toMatch(/shopify/i);
  });

  it('keeps complete fields before a mid-string cut and does not invent later pack content', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const completePrefix = [
      '{"transcript":{"language":"en","full_text":"Eggs spoken line about cracking a shell.",',
      '"segments":[{"idx":0,"start_s":0,"end_s":4,"text":"Eggs spoken line about cracking a shell."}]},',
      '"keyframes":[{"t_s":2,"desc":"Eggs on a counter"}],',
      '"concepts":["eggs"],',
      '"requirements":[],',
      '"code_snippets":[{"path_hint":"src/bake.ts","lang":"ts","content":"',
    ].join('');
    const snippet = `${EGGS_SPOKEN.repeat(80)}later-invented-should-not-appear`;
    const truncated = `${completePrefix}${snippet}`.slice(0, completePrefix.length + 1200);

    expect(jsonParseError(truncated)).toMatch(/Unterminated string in JSON/i);

    const generateText = vi.fn<VideoPackGenerateText>(async () => ({
      text: `\`\`\`json\n${truncated}`,
    }));
    const spec = await extractVideoPackSpec(
      { sourceUrl: EGGS_URL, videoId: EGGS_ID },
      { generateText },
    );

    expect(spec.transcript.full_text).toBe('Eggs spoken line about cracking a shell.');
    expect(spec.concepts).toEqual(['eggs']);
    expect(spec.keyframes[0]?.desc).toBe('Eggs on a counter');
    expect(spec.code_snippets[0]?.content.startsWith('Eggs tutorial:')).toBe(true);
    expect(spec.code_snippets[0]?.content).not.toContain('later-invented-should-not-appear');
    expect(spec.stack.tools).toEqual([]);
    expect(spec.artifacts).toEqual([]);
  });

  it('fails closed with a position-bearing error when truncated JSON is not a spec object', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const garbage = `"not-a-spec-object ${'Eggs tutorial without braces. '.repeat(20)}`.slice(0, 200);
    const parseError = jsonParseError(garbage);
    expect(parseError).toMatch(/Unterminated string in JSON at position/i);

    const generateText = vi.fn<VideoPackGenerateText>(async () => ({ text: garbage }));
    await expect(
      extractVideoPackSpec({ sourceUrl: EGGS_URL, videoId: EGGS_ID }, { generateText }),
    ).rejects.toThrow(/unparseable spec JSON at position \d+/i);
    await expect(
      extractVideoPackSpec({ sourceUrl: EGGS_URL, videoId: EGGS_ID }, { generateText }),
    ).rejects.toThrow(/truncated mid-string/i);
  });

  it('fails closed when a repaired payload is still identity-only cite text', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const truncated = `{"transcript":{"language":null,"full_text":"cite:youtube:${EGGS_ID}","segments":[]},"concepts":[`;
    const generateText = vi.fn<VideoPackGenerateText>(async () => ({ text: truncated }));

    await expect(
      extractVideoPackSpec({ sourceUrl: EGGS_URL, videoId: EGGS_ID }, { generateText }),
    ).rejects.toThrow(/no extracted spec content/i);
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

  it('marks desc-only keyframes as PARTIAL and does not invent image_path', () => {
    const identity = buildIdentityPack(CANON, SOURCE_URL, '2026-09-03T00:00:00.000Z');
    const merged = applyExtractedSpec(identity, SPEC_JSON);

    expect(merged.keyframes[0]?.image_path).toBeNull();
    expect(merged.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_PARTIAL);
    expect(merged.provenance.notes).toContain(KEYFRAME_IMAGES_PARTIAL_NOTE);
    expect(merged.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON]);
    expect(JSON.stringify(merged.keyframes)).not.toMatch(/https?:\/\//);
  });

  it('strips an invented Gemini image_path and still records PARTIAL provenance', () => {
    const identity = buildIdentityPack(CANON, SOURCE_URL, '2026-09-03T00:00:00.000Z');
    const invented = 'https://example.com/not-a-captured-frame.jpg';
    const merged = applyExtractedSpec(identity, {
      ...SPEC_JSON,
      keyframes: [{ t_s: 1.2, desc: 'Elephants at the enclosure', image_path: invented }],
    });

    expect(merged.keyframes[0]?.image_path).toBeNull();
    expect(merged.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_PARTIAL);
    expect(merged.provenance.notes).toContain(KEYFRAME_IMAGES_PARTIAL_NOTE);
    expect(JSON.stringify(merged)).not.toContain(invented);
  });
});

describe('applyKeyframeImageHonesty', () => {
  it('overlays PARTIAL on a stored prod-shaped pack without inventing URLs', () => {
    const identity = buildIdentityPack('QjZ5ohr7sGA', 'https://www.youtube.com/watch?v=QjZ5ohr7sGA', '2026-09-12T16:39:08.716Z');
    const stored = applyExtractedSpec(identity, SPEC_JSON);
    const prodShaped = {
      ...stored,
      keyframes: [
        { t_s: 1, image_path: null, desc: 'Host Matt Schmitz introducing tire change guide' },
        { t_s: 8, image_path: null, desc: 'Jack point under the car' },
      ],
      metrics: {},
      provenance: {
        ...stored.provenance,
        notes: 'Identity pack plus Gemini 3.8 Flash spec extract via AI Gateway.',
      },
    };

    const honest = applyKeyframeImageHonesty(prodShaped);

    expect(honest.keyframes.every((frame) => frame.image_path === null)).toBe(true);
    expect(honest.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_PARTIAL);
    expect(honest.provenance.notes).toContain(KEYFRAME_IMAGES_PARTIAL_NOTE);
    expect(honest.provenance.notes).toContain('Identity pack plus Gemini 3.8 Flash spec extract via AI Gateway.');
    expect(honest.provenance.source_hash).toBe(prodShaped.provenance.source_hash);
    expect(JSON.stringify(honest.keyframes)).not.toMatch(/https?:\/\//);
  });

  it('does not duplicate the PARTIAL note on a second seal', () => {
    const identity = buildIdentityPack(CANON, SOURCE_URL, '2026-09-03T00:00:00.000Z');
    const once = applyKeyframeImageHonesty(applyExtractedSpec(identity, SPEC_JSON));
    const twice = applyKeyframeImageHonesty(once);
    const occurrences = twice.provenance.notes.split(KEYFRAME_IMAGES_PARTIAL_NOTE).length - 1;
    expect(occurrences).toBe(1);
  });

  it('keeps a durable Blob capture URL and marks keyframes_images ok', () => {
    const identity = buildIdentityPack(CANON, SOURCE_URL, '2026-09-03T00:00:00.000Z');
    const captured =
      'https://abc123.public.blob.vercel-storage.com/videopack/auJzb1D-fag/keyframes/1.2.jpg';
    const honest = applyKeyframeImageHonesty({
      ...applyExtractedSpec(identity, SPEC_JSON),
      keyframes: [{ t_s: 1.2, desc: 'Elephants at the enclosure', image_path: captured }],
    });

    expect(isDurableCapturedImagePath(captured)).toBe(true);
    expect(honest.keyframes[0]?.image_path).toBe(captured);
    expect(honest.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_OK);
    expect(honest.provenance.notes).toContain(KEYFRAME_IMAGES_OK_NOTE);
    expect(honest.provenance.notes).not.toContain(KEYFRAME_IMAGES_PARTIAL_NOTE);
    expect(honest.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON]);
  });

  it('keeps an app-served captured frame path and still strips thumbs', () => {
    const identity = buildIdentityPack('QjZ5ohr7sGA', 'https://www.youtube.com/watch?v=QjZ5ohr7sGA', '2026-09-12T16:39:08.716Z');
    const served = '/api/video/pack/frames/QjZ5ohr7sGA/8';
    const thumb = 'https://i.ytimg.com/vi/QjZ5ohr7sGA/hqdefault.jpg';
    const honest = applyKeyframeImageHonesty({
      ...applyExtractedSpec(identity, SPEC_JSON),
      keyframes: [
        { t_s: 8, desc: 'Jack point under the car', image_path: served },
        { t_s: 1, desc: 'Host intro', image_path: thumb },
      ],
    });

    expect(honest.keyframes[0]?.image_path).toBe(served);
    expect(honest.keyframes[1]?.image_path).toBeNull();
    expect(honest.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_PARTIAL);
    expect(JSON.stringify(honest.keyframes)).not.toContain(thumb);
  });

  it('strips img.youtube.com still URLs instead of treating them as captured paths', () => {
    const identity = buildIdentityPack('QjZ5ohr7sGA', 'https://www.youtube.com/watch?v=QjZ5ohr7sGA', '2026-09-12T16:39:08.716Z');
    const still = 'https://img.youtube.com/vi/QjZ5ohr7sGA/hq2.jpg';
    const honest = applyKeyframeImageHonesty({
      ...applyExtractedSpec(identity, SPEC_JSON),
      keyframes: [{ t_s: 8, desc: 'Jack point under the car', image_path: still }],
    });
    expect(isDurableCapturedImagePath(still)).toBe(false);
    expect(honest.keyframes[0]?.image_path).toBeNull();
    expect(honest.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_PARTIAL);
    expect(JSON.stringify(honest.keyframes)).not.toContain(still);
  });
});

const TINY_JPEG = Uint8Array.from([
  0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
  0x00, 0x01, 0x00, 0x00, 0xff, 0xdb, 0x00, 0x43, 0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
  0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0a, 0x0c, 0x14, 0x0d, 0x0c, 0x0b, 0x0b, 0x0c, 0x19, 0x12,
  0x13, 0x0f, 0x14, 0x1d, 0x1a, 0x1f, 0x1e, 0x1d, 0x1a, 0x1c, 0x1c, 0x20, 0x24, 0x2e, 0x27, 0x20,
  0x22, 0x2c, 0x23, 0x1c, 0x1c, 0x28, 0x37, 0x29, 0x2c, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1f, 0x27,
  0x39, 0x3d, 0x38, 0x32, 0x3c, 0x2e, 0x33, 0x34, 0x32, 0xff, 0xc0, 0x00, 0x0b, 0x08, 0x00, 0x01,
  0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xff, 0xc4, 0x00, 0x14, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0xff, 0xc4, 0x00, 0x14,
  0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0xff, 0xda, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3f, 0x00, 0x7f, 0x3f, 0xff, 0xd9,
]);

describe('hydrateKeyframeImages', () => {
  afterEach(() => {
    resetKeyframeFrameCaptureForTests();
  });

  it('writes app-served image_path after a real JPEG capture and seals ok', async () => {
    setKeyframeFrameCaptureForTests(async ({ videoId, t_s }) => ({
      bytes: TINY_JPEG,
      contentType: KEYFRAME_JPEG_CONTENT_TYPE,
      imagePath: `/api/video/pack/frames/${videoId}/${t_s}`,
    }));
    const identity = buildIdentityPack('QjZ5ohr7sGA', 'https://www.youtube.com/watch?v=QjZ5ohr7sGA', '2026-09-12T16:39:08.716Z');
    const stored = applyKeyframeImageHonesty({
      ...applyExtractedSpec(identity, SPEC_JSON),
      keyframes: [
        { t_s: 1, image_path: null, desc: 'Host Matt Schmitz introducing tire change guide' },
        { t_s: 8, image_path: null, desc: 'Jack point under the car' },
      ],
    });
    expect(stored.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_PARTIAL);

    const hydrated = await hydrateKeyframeImages(stored);

    expect(hydrated.keyframes.map((frame) => frame.image_path)).toEqual([
      '/api/video/pack/frames/QjZ5ohr7sGA/1',
      '/api/video/pack/frames/QjZ5ohr7sGA/8',
    ]);
    expect(hydrated.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_OK);
    expect(hydrated.provenance.notes).toContain(KEYFRAME_IMAGES_OK_NOTE);
    expect(hydrated.provenance.notes).not.toContain(KEYFRAME_IMAGES_PARTIAL_NOTE);
    expect(hydrated.provenance.source_hash).toBe(stored.provenance.source_hash);
  });

  it('stays PARTIAL when capture cannot obtain a frame', async () => {
    setKeyframeFrameCaptureForTests(async () => null);
    const identity = buildIdentityPack(CANON, SOURCE_URL, '2026-09-03T00:00:00.000Z');
    const stored = applyExtractedSpec(identity, SPEC_JSON);
    const hydrated = await hydrateKeyframeImages(stored);
    expect(hydrated.keyframes[0]?.image_path).toBeNull();
    expect(hydrated.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_PARTIAL);
    expect(hydrated.provenance.notes).toContain(KEYFRAME_IMAGES_PARTIAL_NOTE);
    expect(hydrated.provenance.notes).toMatch(/storyboard and stills/i);
  });

  it('seals ok with stills provenance when every frame came from stills bytes', async () => {
    setKeyframeFrameCaptureForTests(async ({ videoId, t_s }) => ({
      bytes: TINY_JPEG,
      contentType: KEYFRAME_JPEG_CONTENT_TYPE,
      imagePath: `/api/video/pack/frames/${videoId}/${t_s}`,
      source: 'stills',
    }));
    const identity = buildIdentityPack('QjZ5ohr7sGA', 'https://www.youtube.com/watch?v=QjZ5ohr7sGA', '2026-09-12T16:39:08.716Z');
    const stored = applyKeyframeImageHonesty({
      ...applyExtractedSpec(identity, SPEC_JSON),
      keyframes: [
        { t_s: 1, image_path: null, desc: 'Host Matt Schmitz introducing tire change guide' },
        { t_s: 8, image_path: null, desc: 'Jack point under the car' },
      ],
    });

    const hydrated = await hydrateKeyframeImages(stored);

    expect(hydrated.keyframes.map((frame) => frame.image_path)).toEqual([
      '/api/video/pack/frames/QjZ5ohr7sGA/1',
      '/api/video/pack/frames/QjZ5ohr7sGA/8',
    ]);
    expect(hydrated.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_OK);
    expect(hydrated.metrics.keyframes_images_source).toBe('stills');
    expect(hydrated.provenance.notes).toContain(KEYFRAME_IMAGES_OK_STILLS_NOTE);
    expect(hydrated.provenance.notes).not.toContain(KEYFRAME_IMAGES_PARTIAL_NOTE);
    expect(JSON.stringify(hydrated.keyframes)).not.toMatch(/i\.ytimg\.com|img\.youtube\.com|hqdefault/);
    expect(hydrated.provenance.source_hash).toBe(stored.provenance.source_hash);
  });
});
