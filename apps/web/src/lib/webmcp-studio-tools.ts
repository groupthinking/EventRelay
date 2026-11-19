import { extractYouTubeId } from '@/lib/timestamp';

export type WebMcpJsonSchemaProperty = {
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  description?: string;
  enum?: readonly string[];
};

export type WebMcpToolAnnotations = {
  readOnlyHint?: boolean;
  untrustedContentHint?: boolean;
};

export type WebMcpToolDefinition<TInput = Record<string, unknown>> = {
  name: string;
  description: string;
  inputSchema: {
    type: 'object';
    properties: Record<string, WebMcpJsonSchemaProperty>;
    required?: readonly string[];
  };
  execute: (input: TInput) => Promise<unknown> | unknown;
  annotations?: WebMcpToolAnnotations;
};

export type WebMcpRegisterOptions = {
  signal?: AbortSignal;
  exposedTo?: readonly string[];
};

export type WebMcpModelContext = {
  registerTool: <TInput = Record<string, unknown>>(
    tool: WebMcpToolDefinition<TInput>,
    options?: WebMcpRegisterOptions,
  ) => Promise<void> | void;
};

export type StudioWebMcpPackSnapshot = {
  videoId: string | null;
  packId: string | null;
  sourceUrl: string | null;
  sourceHash: string | null;
  busy: boolean;
  transcriptWordCount: number;
  chapterCount: number;
  actionCount: number;
  toolCount: number;
  artifactCount: number;
};

export type WebflowCurriculumVideo = {
  id: string;
  videoId: string;
  title: string;
  topic: 'AI' | 'CMS' | 'Components';
  duration: string;
  url: string;
};

export const WEBFLOW_MCP_CURRICULUM_VIDEOS: readonly WebflowCurriculumVideo[] = [
  {
    id: 'webflow-mcp-marketers',
    videoId: '6TrjBFW6EKg',
    title: 'MCP for marketers in Webflow',
    topic: 'AI',
    duration: '7:29',
    url: 'https://www.youtube.com/watch?v=6TrjBFW6EKg',
  },
  {
    id: 'uvai-default-fixture',
    videoId: 'auJzb1D-fag',
    title: 'UVAI Default Reference Video Pack',
    topic: 'AI',
    duration: 'fixture',
    url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
  },
] as const;

export type AeoWebMcpAuditResult = {
  hasJsonLd: boolean;
  jsonLdCount: number;
  hasCanonical: boolean;
  hasOpenGraphTitle: boolean;
  h1Count: number;
  declarativeFormTools: Array<{ name: string; description: string }>;
  imperativeApiAvailable: boolean;
  totalRegisteredToolCount: number;
  lighthouseOver40ToolsWarning: boolean;
  score: number;
};

type DocumentWithModelContext = Document & {
  modelContext?: WebMcpModelContext;
};

export function getDocumentModelContext(doc?: Document | null): WebMcpModelContext | null {
  const target = doc ?? (typeof document !== 'undefined' ? document : null);
  if (!target) return null;
  const candidate = (target as DocumentWithModelContext).modelContext;
  if (!candidate || typeof candidate.registerTool !== 'function') {
    return null;
  }
  return candidate;
}

/**
 * Native client-side Answer Engine Optimization (AEO) and WebMCP readiness audit.
 * Evaluates structured JSON-LD metadata, semantic headings, declarative `<form toolname>`,
 * imperative `document.modelContext` support, and Lighthouse's 40-tool ceiling.
 */
export function auditDocumentAeoAndWebMcp(
  doc?: Document | null,
  imperativeToolCount = 0,
): AeoWebMcpAuditResult {
  const target = doc ?? (typeof document !== 'undefined' ? document : null);
  if (!target) {
    return {
      hasJsonLd: false,
      jsonLdCount: 0,
      hasCanonical: false,
      hasOpenGraphTitle: false,
      h1Count: 0,
      declarativeFormTools: [],
      imperativeApiAvailable: false,
      totalRegisteredToolCount: imperativeToolCount,
      lighthouseOver40ToolsWarning: imperativeToolCount > 40,
      score: 0,
    };
  }

  const jsonLdNodes = target.querySelectorAll('script[type="application/ld+json"]');
  const jsonLdCount = jsonLdNodes.length;
  const hasJsonLd = jsonLdCount > 0;
  const hasCanonical = Boolean(target.querySelector('link[rel="canonical"]')?.getAttribute('href'));
  const hasOpenGraphTitle = Boolean(
    target.querySelector('meta[property="og:title"]')?.getAttribute('content'),
  );
  const h1Count = target.querySelectorAll('h1').length;

  const formNodes = Array.from(target.querySelectorAll('form[toolname]'));
  const declarativeFormTools = formNodes
    .map((form) => ({
      name: (form.getAttribute('toolname') ?? '').trim(),
      description: (form.getAttribute('tooldescription') ?? '').trim(),
    }))
    .filter((tool) => tool.name.length > 0);

  const imperativeApiAvailable = Boolean(getDocumentModelContext(target));
  const totalRegisteredToolCount = declarativeFormTools.length + Math.max(0, imperativeToolCount);
  const lighthouseOver40ToolsWarning = totalRegisteredToolCount > 40;

  let score = 0;
  if (hasJsonLd) score += 25;
  if (hasCanonical) score += 20;
  if (hasOpenGraphTitle) score += 15;
  if (h1Count === 1) score += 20;
  if (declarativeFormTools.length > 0 || imperativeApiAvailable) score += 20;
  if (lighthouseOver40ToolsWarning) score = Math.max(0, score - 20);

  return {
    hasJsonLd,
    jsonLdCount,
    hasCanonical,
    hasOpenGraphTitle,
    h1Count,
    declarativeFormTools,
    imperativeApiAvailable,
    totalRegisteredToolCount,
    lighthouseOver40ToolsWarning,
    score,
  };
}

export type StudioWebMcpHandlers = {
  getSnapshot: () => StudioWebMcpPackSnapshot;
  onLoadUrl: (watchUrl: string, runImmediately: boolean) => void;
};

/**
 * Registers UVAI Studio's imperative WebMCP tools on `document.modelContext`
 * using an `AbortSignal` for leak-free unregistration when Studio unmounts.
 */
export async function registerStudioWebMcpTools(
  handlers: StudioWebMcpHandlers,
  options?: {
    doc?: Document | null;
    signal?: AbortSignal;
    exposedTo?: readonly string[];
  },
): Promise<{ registered: string[]; supported: boolean }> {
  const doc = options?.doc ?? (typeof document !== 'undefined' ? document : null);
  const modelContext = getDocumentModelContext(doc);
  if (!modelContext) {
    return { registered: [], supported: false };
  }

  const tools: WebMcpToolDefinition[] = [
    {
      name: 'get_active_video_pack',
      description:
        'Return the active UVAI Studio Video Pack identifier, extraction state, transcript word count, chapters, actions, tools, and artifacts.',
      inputSchema: {
        type: 'object',
        properties: {},
      },
      execute: async () => handlers.getSnapshot(),
      annotations: {
        readOnlyHint: true,
        untrustedContentHint: true,
      },
    },
    {
      name: 'audit_aeo_webmcp_readiness',
      description:
        'Run UVAI native Answer Engine Optimization (AEO) and WebMCP audit on the current document (JSON-LD, canonical, OpenGraph, h1 count, registered tools).',
      inputSchema: {
        type: 'object',
        properties: {},
      },
      execute: async () => auditDocumentAeoAndWebMcp(doc, 3),
      annotations: {
        readOnlyHint: true,
      },
    },
    {
      name: 'load_studio_youtube_url',
      description:
        'Populate UVAI Studio with a validated YouTube watch URL (or built-in Webflow curriculum preset) and optionally start Video Pack extraction.',
      inputSchema: {
        type: 'object',
        properties: {
          youtubeUrl: {
            type: 'string',
            description: 'Full YouTube watch or youtu.be URL to inspect in Studio.',
          },
          preset: {
            type: 'string',
            enum: WEBFLOW_MCP_CURRICULUM_VIDEOS.map((item) => item.id),
            description: 'Optional built-in Webflow MCP curriculum video preset ID.',
          },
          runImmediately: {
            type: 'boolean',
            description: 'Set true to trigger extraction right after loading the URL.',
          },
        },
      },
      execute: async (rawInput: Record<string, unknown>) => {
        const presetId = typeof rawInput.preset === 'string' ? rawInput.preset.trim() : '';
        const presetEntry = WEBFLOW_MCP_CURRICULUM_VIDEOS.find((entry) => entry.id === presetId);
        const candidateUrl =
          presetEntry?.url ?? (typeof rawInput.youtubeUrl === 'string' ? rawInput.youtubeUrl.trim() : '');
        const resolvedId = extractYouTubeId(candidateUrl);
        if (!resolvedId) {
          throw new Error('Provide a valid YouTube URL or preset identifier.');
        }
        const canonicalWatchUrl = `https://www.youtube.com/watch?v=${resolvedId}`;
        const runImmediately = Boolean(rawInput.runImmediately);
        handlers.onLoadUrl(canonicalWatchUrl, runImmediately);
        await Promise.resolve();
        return {
          ok: true,
          videoId: resolvedId,
          youtubeUrl: canonicalWatchUrl,
          started: runImmediately,
        };
      },
    },
  ];

  const registerOptions: WebMcpRegisterOptions = {
    ...(options?.signal ? { signal: options.signal } : {}),
    ...(options?.exposedTo ? { exposedTo: options.exposedTo } : {}),
  };

  const registered: string[] = [];
  for (const tool of tools) {
    if (options?.signal?.aborted) break;
    await modelContext.registerTool(tool, registerOptions);
    registered.push(tool.name);
  }

  return { registered, supported: true };
}
