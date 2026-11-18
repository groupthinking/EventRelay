// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest';
import {
  auditDocumentAeoAndWebMcp,
  registerStudioWebMcpTools,
  WEBFLOW_MCP_CURRICULUM_VIDEOS,
  type WebMcpToolDefinition,
} from '@/lib/webmcp-studio-tools';

describe('webmcp-studio-tools', () => {
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
});
