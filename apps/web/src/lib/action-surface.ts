/**
 * Canonical action surface (F3).
 *
 * Single product path for "act on findings" inside EventRelay:
 *
 *   1. Plan  — TranscriptActionAgent (backend) emits summary, task_board,
 *              and project_scaffold via /api/video or /api/pipeline/stream.
 *   2. Act   — Next action-agent (apps/web) runs POST /api/agents/actions;
 *              LLM chooses tools from action-tools.ts and executes them.
 *   3. Package — Deterministic scaffold files (README + tasks.json + stub)
 *              absorbed from video-intelligence-workbench /api/scaffold.
 *
 * Prototypes outside this tree (workbench /api/actions + /api/scaffold,
 * action-genai, youtube-transcript-app ActionExtractor) are non-canonical.
 */

export interface ActionCardLike {
  title: string;
  description?: string;
  category?: string;
  estimatedMinutes?: number | null;
  /** Optional timestamp range in seconds (workbench ActionCard). */
  start?: number;
  end?: number;
  confidence?: number;
  tags?: string[];
  snippet?: string;
}

export interface ScaffoldPackage {
  projectName: string;
  files: Record<string, string>;
}

function safeProjectName(name: string): string {
  return (
    name
      .toLowerCase()
      .replace(/[^a-z0-9-_]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'generated-project'
  );
}

/** Build deterministic scaffold files from planned/fulfilled actions (workbench absorb). */
export type StudioEventLike = {
  type?: string;
  title?: string;
  description?: string;
};

export type StudioWorkflowActionLike = {
  tool?: string;
  status?: string;
  result?: string;
};

/**
 * Export uses this Studio run: Analyze actions, else events, else Act tools.
 * Button is enabled on transcript/events; do not require insights.actions.
 */
export function actionsFromStudioRun(input: {
  insightActions?: ActionCardLike[] | null;
  events?: StudioEventLike[] | null;
  workflowActions?: StudioWorkflowActionLike[] | null;
}): ActionCardLike[] {
  const out: ActionCardLike[] = [];
  const seen = new Set<string>();

  const push = (action: ActionCardLike) => {
    const title = action.title.trim();
    if (!title) return;
    const key = title.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ ...action, title });
  };

  for (const action of input.insightActions || []) {
    if (!action?.title) continue;
    push(action);
  }
  for (const event of input.events || []) {
    if (!event?.title) continue;
    push({
      title: event.title,
      description: event.description,
      category: event.type || 'event',
    });
  }
  if (out.length === 0) {
    for (const action of input.workflowActions || []) {
      const title = (action.tool || '').trim();
      if (!title) continue;
      push({
        title,
        description: action.result || action.status,
        category: 'act',
      });
    }
  }
  return out;
}

export function buildScaffoldPackage(input: {
  projectName?: string;
  actions: ActionCardLike[];
  /** Optional Gemini project_scaffold blob from TranscriptActionAgent. */
  projectScaffold?: unknown;
}): ScaffoldPackage {
  const name = safeProjectName(input.projectName || 'generated-project');
  const tasks = input.actions.map((a, i) => ({
    id: `TASK-${String(i + 1).padStart(3, '0')}`,
    title: a.title,
    description: a.description || '',
    category: a.category || 'build',
    estimatedMinutes: a.estimatedMinutes ?? null,
    source:
      typeof a.start === 'number' && typeof a.end === 'number'
        ? `${Math.round(a.start)}s-${Math.round(a.end)}s`
        : undefined,
    confidence: a.confidence,
    tags: a.tags,
    snippet: a.snippet,
  }));

  const taskLines = tasks
    .map((t) => {
      const meta = [t.source, t.category].filter(Boolean).join(', ');
      return `- [ ] ${t.id}: ${t.title}${meta ? ` (${meta})` : ''}`;
    })
    .join('\n');

  const files: Record<string, string> = {
    'README.md': `# ${name}\n\nGenerated from EventRelay video action surface.\n\n## Tasks\n\n${
      taskLines || '- (no tasks yet — run Act on findings or re-analyze the video)'
    }\n`,
    'tasks.json': JSON.stringify(tasks, null, 2) + '\n',
    'src/index.ts':
      "export function main() {\n  console.log('Generated project scaffold loaded.');\n}\n\nmain();\n",
  };

  if (input.projectScaffold != null) {
    files['project_scaffold.json'] =
      JSON.stringify(input.projectScaffold, null, 2) + '\n';
  }

  return { projectName: name, files };
}

/** Human-readable preview lines for a project_scaffold blob. */
export function summarizeProjectScaffold(scaffold: unknown, maxItems = 6): string[] {
  if (scaffold == null) return [];
  if (typeof scaffold === 'string') {
    const t = scaffold.trim();
    return t ? [t.slice(0, 200)] : [];
  }
  if (typeof scaffold !== 'object') return [String(scaffold)];

  const obj = scaffold as Record<string, unknown>;
  const lines: string[] = [];

  if (typeof obj.raw === 'string' && Object.keys(obj).length === 1) {
    return [obj.raw.slice(0, 200)];
  }

  const structure = obj.repository_structure;
  if (Array.isArray(structure)) {
    for (const item of structure.slice(0, maxItems)) {
      if (typeof item === 'string') lines.push(item);
      else if (item && typeof item === 'object') {
        const row = item as Record<string, unknown>;
        const path = typeof row.path === 'string' ? row.path : typeof row.name === 'string' ? row.name : null;
        const purpose = typeof row.purpose === 'string' ? row.purpose : typeof row.description === 'string' ? row.description : '';
        if (path) lines.push(purpose ? `${path} — ${purpose}` : path);
        else lines.push(JSON.stringify(item).slice(0, 120));
      }
    }
  }

  const modules = obj.core_modules;
  if (Array.isArray(modules) && lines.length < maxItems) {
    for (const m of modules.slice(0, maxItems - lines.length)) {
      if (m && typeof m === 'object') {
        const row = m as Record<string, unknown>;
        const name = typeof row.name === 'string' ? row.name : 'module';
        const resp = typeof row.responsibility === 'string' ? row.responsibility : '';
        lines.push(resp ? `Module ${name}: ${resp}` : `Module ${name}`);
      }
    }
  }

  if (lines.length === 0) {
    lines.push(JSON.stringify(obj).slice(0, 200));
  }
  return lines.slice(0, maxItems);
}

/** Trigger browser downloads for each file in a scaffold package. */
export function downloadScaffoldPackage(pkg: ScaffoldPackage): void {
  if (typeof document === 'undefined') return;
  const entries = Object.entries(pkg.files);
  for (const [path, content] of entries) {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = path.includes('/') ? path.split('/').pop() || path : path;
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }
}
