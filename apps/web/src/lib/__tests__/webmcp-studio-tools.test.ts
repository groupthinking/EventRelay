// @vitest-environment jsdom
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it, vi } from 'vitest';
import {
  auditDocumentAeoAndWebMcp,
  getDocumentModelContext,
  registerStudioWebMcpTools,
  WEBFLOW_MCP_CURRICULUM_VIDEOS,
  type StudioWebMcpHandlers,
  type WebMcpToolDefinition,
} from '@/lib/webmcp-studio-tools';

describe('webmcp-studio-tools', () => {
  const handlers: StudioWebMcpHandlers = {
    getSnapshot: vi.fn(),
    onLoadUrl: vi.fn(),
  };

  it.each(['permissionsPolicy', 'featurePolicy'])(
    'skips modelContext access and registration when %s denies tools',
    async (policyProperty) => {
      const allowsFeature = vi.fn(() => false);
      const getModelContext = vi.fn(() => {
        throw new DOMException('Tools are blocked by permissions policy.', 'NotAllowedError');
      });
      const doc = document.implementation.createHTMLDocument();
      Object.defineProperty(doc, policyProperty, { value: { allowsFeature } });
      Object.defineProperty(doc, 'modelContext', { get: getModelContext });

      expect(getDocumentModelContext(doc)).toBeNull();
      expect(auditDocumentAeoAndWebMcp(doc).imperativeApiAvailable).toBe(false);
      await expect(registerStudioWebMcpTools(handlers, { doc })).resolves.toEqual({
        registered: [],
        supported: false,
      });
      expect(allowsFeature).toHaveBeenCalledWith('tools');
      expect(getModelContext).not.toHaveBeenCalled();
    },
  );

  it('prefers permissionsPolicy over the legacy featurePolicy API', () => {
    const registerTool = vi.fn();
    const doc = {
      permissionsPolicy: { allowsFeature: vi.fn(() => true) },
      featurePolicy: { allowsFeature: vi.fn(() => false) },
      modelContext: { registerTool },
    } as unknown as Document;

    expect(getDocumentModelContext(doc)).toEqual({ registerTool });
  });

  it.each(['NotAllowedError', 'SecurityError'])(
    'treats a %s from the modelContext getter as unsupported',
    async (name) => {
      const doc = document.implementation.createHTMLDocument();
      Object.defineProperty(doc, 'modelContext', {
        get: () => {
          throw new DOMException('Tools access denied.', name);
        },
      });

      expect(getDocumentModelContext(doc)).toBeNull();
      expect(auditDocumentAeoAndWebMcp(doc).imperativeApiAvailable).toBe(false);
      await expect(registerStudioWebMcpTools(handlers, { doc })).resolves.toEqual({
        registered: [],
        supported: false,
      });
    },
  );

  it('returns unsupported without probing unknown policies when WebMCP is unavailable', async () => {
    const doc = document.implementation.createHTMLDocument();
    const allowsFeature = vi.fn();
    Object.defineProperty(doc, 'featurePolicy', { value: { allowsFeature } });

    await expect(registerStudioWebMcpTools(handlers, { doc })).resolves.toEqual({
      registered: [],
      supported: false,
    });
    expect(allowsFeature).not.toHaveBeenCalled();
  });

  it.each(['throw', 'reject'])(
    'handles registration permission failures when registerTool uses %s',
    async (failureMode) => {
      const error = new DOMException('Tools access denied.', 'NotAllowedError');
      const registerTool = vi.fn(() => {
        if (failureMode === 'throw') throw error;
        return Promise.reject(error);
      });
      const doc = { modelContext: { registerTool } } as unknown as Document;

      await expect(registerStudioWebMcpTools(handlers, { doc })).resolves.toEqual({
        registered: [],
        supported: false,
      });
      expect(registerTool).toHaveBeenCalledTimes(1);
    },
  );

  it('stops registration if permission is denied after a tool has registered', async () => {
    const registerTool = vi.fn()
      .mockResolvedValueOnce(undefined)
      .mockRejectedValue(new DOMException('Tools access denied.', 'SecurityError'));
    const doc = { modelContext: { registerTool } } as unknown as Document;

    await expect(registerStudioWebMcpTools(handlers, { doc })).resolves.toEqual({
      registered: ['get_active_video_pack'],
      supported: false,
    });
    expect(registerTool).toHaveBeenCalledTimes(2);
  });

  it('handles an in-flight registration aborted by effect cleanup', async () => {
    const controller = new AbortController();
    const registerTool = vi.fn(() => {
      controller.abort();
      return Promise.reject(controller.signal.reason);
    });
    const doc = { modelContext: { registerTool } } as unknown as Document;

    await expect(registerStudioWebMcpTools(handlers, { doc, signal: controller.signal }))
      .resolves.toEqual({ registered: [], supported: true });
    expect(registerTool).toHaveBeenCalledTimes(1);
  });

  it('does not register tools when the signal is already aborted', async () => {
    const controller = new AbortController();
    controller.abort();
    const registerTool = vi.fn();
    const doc = { modelContext: { registerTool } } as unknown as Document;

    await expect(registerStudioWebMcpTools(handlers, { doc, signal: controller.signal }))
      .resolves.toEqual({ registered: [], supported: true });
    expect(registerTool).not.toHaveBeenCalled();
  });

  it('does not hide unexpected registration errors', async () => {
    const error = new TypeError('Invalid tool definition');
    const doc = {
      modelContext: { registerTool: vi.fn().mockRejectedValue(error) },
    } as unknown as Document;

    await expect(registerStudioWebMcpTools(handlers, { doc })).rejects.toBe(error);
  });

  it('includes the Webflow MCP curriculum video entry for 6TrjBFW6EKg', () => {
    const webflow = WEBFLOW_MCP_CURRICULUM_VIDEOS.find((v) => v.videoId === '6TrjBFW6EKg');
    expect(webflow).toBeDefined();
    expect(webflow?.title).toContain('MCP');
    expect(webflow?.url).toBe('https://www.youtube.com/watch?v=6TrjBFW6EKg');
  });

  it('registers atomic tools with AbortSignal cleanup and readOnly annotations', async () => {
    const registered: Array<{ tool: WebMcpToolDefinition; signal?: AbortSignal }> = [];
    const fakeDoc = {
      modelContext: {
        registerTool: vi.fn((tool: WebMcpToolDefinition, opts?: { signal?: AbortSignal }) => {
          registered.push({ tool, signal: opts?.signal });
        }),
      },
      querySelectorAll: () => [],
      querySelector: () => null,
    } as unknown as Document;

    const controller = new AbortController();
    const onLoadUrl = vi.fn();
    const result = await registerStudioWebMcpTools(
      {
        getSnapshot: () => ({
          videoId: '6TrjBFW6EKg',
          packId: 'vp:v0:6TrjBFW6EKg',
          sourceUrl: 'https://www.youtube.com/watch?v=6TrjBFW6EKg',
          sourceHash: 'abc123',
          busy: true,
          transcriptWordCount: 0,
          chapterCount: 0,
          actionCount: 0,
          toolCount: 0,
          artifactCount: 0,
        }),
        onLoadUrl,
      },
      { doc: fakeDoc, signal: controller.signal },
    );

    expect(result.supported).toBe(true);
    expect(result.registered).toEqual([
      'get_active_video_pack',
      'audit_aeo_webmcp_readiness',
      'load_studio_youtube_url',
    ]);
    expect(registered).toHaveLength(3);
    expect(registered[0]?.signal).toBe(controller.signal);
    expect(registered[0]?.tool.annotations).toEqual({
      readOnlyHint: true,
      untrustedContentHint: true,
    });
    expect(registered[1]?.tool.annotations).toEqual({
      readOnlyHint: true,
    });

    const loadRes = (await registered[2]?.tool.execute({
      preset: 'webflow-mcp-marketers',
      runImmediately: true,
    })) as { ok: boolean; videoId: string; started: boolean };
    expect(loadRes).toEqual({
      ok: true,
      videoId: '6TrjBFW6EKg',
      youtubeUrl: 'https://www.youtube.com/watch?v=6TrjBFW6EKg',
      started: true,
    });
    expect(onLoadUrl).toHaveBeenCalledWith('https://www.youtube.com/watch?v=6TrjBFW6EKg', true);

    await expect(
      registered[2]?.tool.execute({ youtubeUrl: 'https://example.com/not-youtube' }),
    ).rejects.toThrow(/valid YouTube URL/i);
  });

  it('audits JSON-LD, canonical, OpenGraph, h1, and declarative form tools for AEO readiness', () => {
    document.head.innerHTML = `
      <link rel="canonical" href="https://uvai.io/studio" />
      <meta property="og:title" content="UVAI Studio" />
    `;
    document.body.innerHTML = `
      <h1>UVAI Studio</h1>
      <script type="application/ld+json">{"@type":"SoftwareApplication"}</script>
      <form toolname="run_studio_video_analysis" tooldescription="Extract Video Pack"></form>
    `;

    const audit = auditDocumentAeoAndWebMcp(document, 3);
    expect(audit.hasJsonLd).toBe(true);
    expect(audit.hasCanonical).toBe(true);
    expect(audit.hasOpenGraphTitle).toBe(true);
    expect(audit.h1Count).toBe(1);
    expect(audit.declarativeFormTools).toEqual([
      { name: 'run_studio_video_analysis', description: 'Extract Video Pack' },
    ]);
    expect(audit.totalRegisteredToolCount).toBe(4);
    expect(audit.lighthouseOver40ToolsWarning).toBe(false);
    expect(audit.score).toBe(100);
  });

  it('gives declarative WebMCP forms named youtubeUrl inputs for browser schema generation', () => {
    const srcRoot = join(dirname(fileURLToPath(import.meta.url)), '../..');
    const homePaste = readFileSync(join(srcRoot, 'components/home/HomePasteForm.tsx'), 'utf8');
    const studio = readFileSync(join(srcRoot, 'components/OneLoopStudio.tsx'), 'utf8');
    expect(homePaste).toContain('toolname="extract_youtube_video_pack"');
    expect(homePaste).toContain('name="youtubeUrl"');
    expect(studio).toContain('toolname="run_studio_video_analysis"');
    expect(studio).toContain('name="youtubeUrl"');
  });
});
