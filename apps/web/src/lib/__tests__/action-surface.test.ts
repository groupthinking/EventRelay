import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  actionsFromStudioRun,
  buildScaffoldPackage,
  downloadScaffoldPackage,
  summarizeProjectScaffold,
} from '@/lib/action-surface';
import { zipEntryNames, zipUtf8Files } from '@/lib/zip-store';

describe('action-surface (F3)', () => {
  const fetchMock = vi.fn();
  const clickMock = vi.fn();
  const appendChildMock = vi.fn();
  const removeMock = vi.fn();
  const createObjectURLMock = vi.fn(() => 'blob:zip');
  const revokeObjectURLMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('URL', {
      createObjectURL: createObjectURLMock,
      revokeObjectURL: revokeObjectURLMock,
    });
    vi.stubGlobal('document', {
      body: { appendChild: appendChildMock },
      createElement: vi.fn(() => ({
        click: clickMock,
        remove: removeMock,
        href: '',
        download: '',
        rel: '',
      })),
    });
  });

  afterEach(() => {
    fetchMock.mockReset();
    clickMock.mockReset();
    appendChildMock.mockReset();
    removeMock.mockReset();
    createObjectURLMock.mockClear();
    revokeObjectURLMock.mockClear();
    vi.unstubAllGlobals();
  });

  it('buildScaffoldPackage emits README, tasks.json, and stub index', () => {
    const pkg = buildScaffoldPackage({
      projectName: 'My Cool App!',
      actions: [
        { title: 'Wire auth', description: 'Add OAuth', category: 'setup', estimatedMinutes: 30 },
        { title: 'Deploy', category: 'deploy', start: 10, end: 45, confidence: 0.9 },
      ],
    });

    expect(pkg.projectName).toBe('my-cool-app');
    expect(pkg.files['README.md']).toContain('# my-cool-app');
    expect(pkg.files['README.md']).toContain('TASK-001: Wire auth');
    expect(pkg.files['tasks.json']).toContain('Wire auth');
    expect(pkg.files['src/index.ts']).toContain('Generated project scaffold');
    expect(pkg.files['project_scaffold.json']).toBeUndefined();
    expect(pkg.files['DEPLOY.md']).toBeUndefined();
  });

  it('exports SOP checklist and DEPLOY.md from linked SOP', () => {
    const pkg = buildScaffoldPackage({
      projectName: 'groke-run',
      actions: [{ title: 'ignored when sop exists' }],
      linkedSop: {
        entities: [{
          name: 'Vercel',
          kind: 'platform',
          officialUrl: 'https://vercel.com',
          docsUrl: 'https://vercel.com/docs/deployments',
          timestamps: [12],
        }],
        steps: [{
          id: 'sop_1',
          order: 1,
          title: 'Ship the preview',
          description: 'From the video.',
          timestamp: 12,
          entityNames: ['Vercel'],
        }],
        checklist: [{
          id: 'chk_vercel_1',
          source: 'stack',
          stack: 'vercel',
          title: 'Hold production until Deployment Checks pass',
          href: 'https://vercel.com/docs/deployment-checks',
        }],
      },
    });
    expect(pkg.files['tasks.json']).toContain('Deployment Checks');
    expect(pkg.files['DEPLOY.md']).toContain('https://vercel.com/docs/deployment-checks');
    expect(pkg.files['README.md']).toContain('https://vercel.com');
    expect(pkg.files['linked-sop.json']).toContain('Ship the preview');
    expect(pkg.files['src/index.ts']).toBeUndefined();
    expect(pkg.files['app/page.tsx']).toContain('export default function Page');
    expect(pkg.files['README.md']).toContain('create-next-app');
    expect(zipEntryNames(zipUtf8Files(pkg.files))).toEqual(
      expect.arrayContaining(['README.md', 'DEPLOY.md', 'app/page.tsx', 'package.json']),
    );
  });

  it('exports architecture and artifacts when events[] is empty', () => {
    const pkg = buildScaffoldPackage({
      projectName: 'empty-events-pack',
      actions: [],
      packFormation: {
        architecture: {
          summary: 'decode to rails',
          stages: [{ id: 'decode', name: 'decode', description: 'frames' }],
          mermaid: 'flowchart LR\ndecode-->rails',
        },
        artifacts: [
          {
            path_hint: 'src/mcp_x402_gateway.ts',
            purpose: 'Paid MCP gateway',
            interface: 'createGateway(config: GatewayConfig): Gateway',
          },
          {
            path_hint: 'src/agent_loop.ts',
            purpose: 'Agent verify loop',
            interface: 'runLoop(input: LoopInput): Promise<LoopResult>',
          },
        ],
        tools: [{ name: 'Cloudflare' }, { name: 'x402' }],
      },
    });
    expect(pkg.files['ARCHITECTURE.md']).toContain('decode to rails');
    expect(pkg.files['ARCHITECTURE.md']).toContain('decode');
    expect(pkg.files['artifacts.json']).toContain('src/mcp_x402_gateway.ts');
    expect(pkg.files['artifacts.json']).toContain('src/agent_loop.ts');
    expect(pkg.files['README.md']).toContain('Cloudflare');
    expect(pkg.files['README.md']).toContain('x402');
  });

  it('includes project_scaffold.json when Gemini scaffold is present', () => {
    const scaffold = {
      repository_structure: [{ path: 'src/app.ts', purpose: 'entry' }],
      core_modules: [{ name: 'api', responsibility: 'HTTP' }],
    };
    const pkg = buildScaffoldPackage({
      projectName: 'demo',
      actions: [{ title: 'Ship it' }],
      projectScaffold: scaffold,
    });
    expect(pkg.files['project_scaffold.json']).toContain('src/app.ts');
  });

  it('summarizeProjectScaffold extracts structure and modules', () => {
    const lines = summarizeProjectScaffold({
      repository_structure: [{ path: 'lib/x.ts', purpose: 'core' }],
      core_modules: [{ name: 'worker', responsibility: 'jobs' }],
    });
    expect(lines.some((l) => l.includes('lib/x.ts'))).toBe(true);
    expect(lines.some((l) => l.includes('worker'))).toBe(true);
  });

  it('summarizeProjectScaffold handles raw string fallback', () => {
    expect(summarizeProjectScaffold({ raw: 'plain scaffold text' })).toEqual([
      'plain scaffold text',
    ]);
  });

  it('actionsFromStudioRun prefers Analyze actions, then events, then Act tools', () => {
    expect(
      actionsFromStudioRun({
        insightActions: [{ title: 'Ship scaffold', description: 'from insights', category: 'build' }],
        events: [{ type: 'action', title: 'Duplicate-ish', description: 'event' }],
        workflowActions: [{ tool: 'save_resource', status: 'ok', result: 'saved' }],
      }),
    ).toEqual([
      { title: 'Ship scaffold', description: 'from insights', category: 'build' },
      { title: 'Duplicate-ish', description: 'event', category: 'action' },
    ]);

    expect(
      actionsFromStudioRun({
        insightActions: [],
        events: [{ type: 'topic', title: 'Paste URL', description: 'start here' }],
        workflowActions: [{ tool: 'create_workflow_task', status: 'ok' }],
      }),
    ).toEqual([{ title: 'Paste URL', description: 'start here', category: 'topic' }]);

    expect(
      actionsFromStudioRun({
        events: [],
        workflowActions: [{ tool: 'save_resource', status: 'ok', result: 'wrote file' }],
      }),
    ).toEqual([{ title: 'save_resource', description: 'wrote file', category: 'act' }]);

    expect(actionsFromStudioRun({ insightActions: [{ title: '  ' }], events: [] })).toEqual([]);
  });

  it('surfaces payment-required export responses without triggering a download', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          error: 'Workspace ZIP exports require Pro. Upgrade to continue.',
          code: 'payment_required',
          upgradeRequired: true,
          checkoutUrl: 'https://checkout.stripe.com/c/pay/cs_test_export',
          retryable: true,
        }),
        {
          status: 402,
          headers: { 'content-type': 'application/json' },
        },
      ),
    );

    const result = await downloadScaffoldPackage({
      projectName: 'paid-pack',
      files: { 'README.md': '# paid-pack\n' },
    });

    expect(result).toEqual({
      ok: false,
      status: 402,
      error: 'Workspace ZIP exports require Pro. Upgrade to continue.',
      code: 'payment_required',
      upgradeRequired: true,
      checkoutUrl: 'https://checkout.stripe.com/c/pay/cs_test_export',
      retryable: true,
    });
    expect(clickMock).not.toHaveBeenCalled();
    expect(createObjectURLMock).not.toHaveBeenCalled();
  });

  it('downloads ZIP bytes returned by the workspace export API', async () => {
    fetchMock.mockResolvedValue(
      new Response(new Uint8Array([0x50, 0x4b, 0x03, 0x04]), {
        status: 200,
        headers: {
          'content-type': 'application/zip',
          'content-disposition': 'attachment; filename="studio-pack.zip"',
        },
      }),
    );

    const result = await downloadScaffoldPackage({
      projectName: 'studio-pack',
      files: { 'README.md': '# studio-pack\n' },
    });

    expect(result).toEqual({ ok: true, status: 200, filename: 'studio-pack.zip' });
    expect(clickMock).toHaveBeenCalledTimes(1);
    expect(createObjectURLMock).toHaveBeenCalledTimes(1);
    expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:zip');
  });

  it('retries transient workspace export failures before downloading', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'temporary' }), {
          status: 503,
          headers: { 'content-type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(new Uint8Array([0x50, 0x4b, 0x03, 0x04]), {
          status: 200,
          headers: {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="retry-pack.zip"',
          },
        }),
      );

    const result = await downloadScaffoldPackage({
      projectName: 'retry-pack',
      files: { 'README.md': '# retry-pack\n' },
    });

    expect(result).toEqual({ ok: true, status: 200, filename: 'retry-pack.zip' });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(clickMock).toHaveBeenCalledTimes(1);
  });
});
