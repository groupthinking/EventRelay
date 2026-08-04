import { describe, expect, it } from 'vitest';
import {
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
});
