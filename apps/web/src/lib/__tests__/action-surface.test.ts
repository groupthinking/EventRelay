import { describe, expect, it } from 'vitest';
import {
  actionsFromStudioRun,
  buildScaffoldPackage,
  summarizeProjectScaffold,
} from '@/lib/action-surface';

describe('action-surface (F3)', () => {
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
});
