import type { VideoPackCitation, EmittedVideoPack } from '@/lib/emit-video-pack';
import { MISSION_CANVAS_FILENAME, emitMissionCanvasFile } from '@/lib/emit-json-canvas';
import type {
  VideoPackKeyframe,
  VideoPackRequirement,
  VideoPackV0Json,
  VideoPackVisualElement,
} from '@/lib/video-pack';
import type { VideoPackActionItem, VideoPackChapter, VideoPackStackTool } from '@/lib/video-pack-types';
import { parsePackActionItems } from '@/lib/video-pack-types';

export const APP_BUILDER_CONTRACT = 'app-builder-workspace' as const;
export const APP_BUILDER_CUT = 'ingest→App Builder sandbox emit' as const;
export const APP_BUILDER_PREVIEW_HOST = '0.0.0.0' as const;
export const APP_BUILDER_PREVIEW_PORT = 8080;
export const APP_BUILDER_PROBE_URL = 'http://127.0.0.1:8080/';

/** Exact pins for the assembled workspace — no caret ranges. */
export const APP_BUILDER_PINNED_DEPS = {
  typescript: '5.7.3',
  vite: '6.4.3',
} as const;

const SOURCE_HASH = /^[a-f0-9]{64}$/;
const TRANSCRIPT_EXCERPT = 900;

export type AppBuilderTranscript = {
  full_text: string;
  language?: string | null;
  segments?: Array<{ idx?: number; start_s?: number; end_s?: number; text: string }>;
};

export type AppBuilderVisualEvent = {
  timestamp: number;
  content: string;
  element_type?: string;
  image_path?: string | null;
};

export type AppBuilderSopStep = {
  id: string;
  order: number;
  title: string;
  description: string;
  timestamp?: number;
};

export type AppBuilderActionItem = {
  id: string;
  title: string;
  description: string;
  type?: string | null;
  difficulty?: 'easy' | 'medium' | 'hard' | null;
  priority?: 'low' | 'normal' | 'high' | null;
};

export type AppBuilderStackTool = {
  name: string;
  kind?: string | null;
  evidence?: string | null;
  docs_url?: string | null;
};

export type AppBuilderChapter = {
  start: number;
  end: number;
  topic: string;
  key_points: string[];
};

export type AppBuilderSandboxInput = {
  videoId: string;
  sourceUrl: string;
  sourceHash: string;
  packId?: string;
  transcript?: AppBuilderTranscript | null;
  visualEvents?: AppBuilderVisualEvent[];
  sopSteps?: AppBuilderSopStep[];
  actionItems?: AppBuilderActionItem[];
  stackTools?: AppBuilderStackTool[];
  chapters?: AppBuilderChapter[];
};

export type AppBuilderSandboxPreview = {
  host: typeof APP_BUILDER_PREVIEW_HOST;
  port: typeof APP_BUILDER_PREVIEW_PORT;
  probe: typeof APP_BUILDER_PROBE_URL;
  start: 'npm run dev';
  smoke: 'node scripts/browser-smoke.mjs';
  gates: readonly ['npm run build', 'npm run typecheck'];
};

export type AppBuilderSandboxIngredients = {
  transcript: AppBuilderTranscript;
  visualEvents: AppBuilderVisualEvent[];
  sopSteps: AppBuilderSopStep[];
  actionItems: AppBuilderActionItem[];
  stackTools: AppBuilderStackTool[];
  chapters: AppBuilderChapter[];
};

export type AppBuilderSandbox = {
  contract: typeof APP_BUILDER_CONTRACT;
  cut: typeof APP_BUILDER_CUT;
  videoId: string;
  sourceUrl: string;
  sourceHash: string;
  packId: string;
  preview: AppBuilderSandboxPreview;
  ingredients: AppBuilderSandboxIngredients;
  files: Record<string, string>;
};

const PREVIEW: AppBuilderSandboxPreview = {
  host: APP_BUILDER_PREVIEW_HOST,
  port: APP_BUILDER_PREVIEW_PORT,
  probe: APP_BUILDER_PROBE_URL,
  start: 'npm run dev',
  smoke: 'node scripts/browser-smoke.mjs',
  gates: ['npm run build', 'npm run typecheck'],
};

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function assertIdentity(input: AppBuilderSandboxInput): void {
  const sourceUrl = input.sourceUrl.trim();
  const sourceHash = input.sourceHash.trim();
  if (!sourceUrl.startsWith('http')) {
    throw new Error('App Builder sandbox emit failed: source_url is required.');
  }
  if (!SOURCE_HASH.test(sourceHash)) {
    throw new Error('App Builder sandbox emit failed: source_hash is required.');
  }
  if (!input.videoId.trim()) {
    throw new Error('App Builder sandbox emit failed: video_id is required.');
  }
}

function excerpt(text: string, max = TRANSCRIPT_EXCERPT): string {
  const trimmed = text.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max).trimEnd()}…`;
}

function visualList(events: AppBuilderVisualEvent[]): string {
  if (events.length === 0) {
    return '<p class="empty" data-testid="visual-empty">No visual events on this pack.</p>';
  }
  return `<ol class="events" data-testid="visual-events">${events
    .map((event) => {
      const stamp = Number.isFinite(event.timestamp) ? `${event.timestamp}s` : '';
      const kind = event.element_type ? ` · ${escapeHtml(event.element_type)}` : '';
      return `<li><span class="stamp">${escapeHtml(stamp)}${kind}</span> ${escapeHtml(event.content)}</li>`;
    })
    .join('')}</ol>`;
}

function sopList(steps: AppBuilderSopStep[]): string {
  if (steps.length === 0) {
    return '<p class="empty" data-testid="sop-empty">No SOP steps on this pack.</p>';
  }
  const items = steps
    .map((step) => {
      const stamp =
        step.timestamp != null ? ` <span class="stamp">${escapeHtml(String(step.timestamp))}s</span>` : '';
      return `<li><label><input type="checkbox" data-testid="sop-check" data-sop-id="${escapeHtml(step.id)}" /> <strong>${escapeHtml(step.title)}</strong>${stamp}<p>${escapeHtml(step.description)}</p></label></li>`;
    })
    .join('');
  return `<ol class="sop" data-testid="sop-steps">${items}</ol><p class="honesty" data-testid="sop-checklist-note">Local checklist only — checking a step is not evidence the procedure was performed.</p>`;
}

function transcriptBlock(transcript: AppBuilderTranscript | null | undefined): string {
  const text = transcript?.full_text?.trim() ?? '';
  if (!text) {
    return '<p class="empty" data-testid="transcript-empty">Transcript not extracted from this pack.</p>';
  }
  return `<p class="transcript" data-testid="pack-transcript">${escapeHtml(excerpt(text))}</p>`;
}

function startupSh(): string {
  return `#!/bin/sh
set -eu
cd /workspace
if curl -sf -o /dev/null --max-time 2 http://127.0.0.1:8080/; then
  exit 0
fi
npm run dev >>/tmp/app-startup.log 2>&1 &
`;
}

function packageJson(): string {
  return `${JSON.stringify(
    {
      name: 'uvai-app-builder-sandbox',
      private: true,
      type: 'module',
      scripts: {
        dev: 'vite --host 0.0.0.0 --port 8080',
        build: 'vite build',
        typecheck: 'tsc --noEmit',
        preview: 'vite preview --host 0.0.0.0 --port 8080',
      },
      devDependencies: {
        typescript: APP_BUILDER_PINNED_DEPS.typescript,
        vite: APP_BUILDER_PINNED_DEPS.vite,
      },
    },
    null,
    2,
  )}\n`;
}

function tsconfigJson(): string {
  return `${JSON.stringify(
    {
      compilerOptions: {
        target: 'ES2022',
        module: 'ESNext',
        moduleResolution: 'bundler',
        strict: true,
        noEmit: true,
        skipLibCheck: true,
        lib: ['ES2022', 'DOM', 'DOM.Iterable'],
      },
      include: ['src/**/*.ts', 'vite.config.ts'],
    },
    null,
    2,
  )}\n`;
}

function viteConfigTs(): string {
  return `import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 8080,
    strictPort: true,
  },
  preview: {
    host: '0.0.0.0',
    port: 8080,
    strictPort: true,
  },
});
`;
}

function stylesCss(): string {
  return `:root {
  color-scheme: dark;
  --bg: #071018;
  --ink: #f4f7fb;
  --muted: #9aa8b5;
  --line: rgba(255, 255, 255, 0.12);
  --accent: #5eead4;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  min-height: 100%;
  background: radial-gradient(1200px 600px at 10% -10%, #123 0%, var(--bg) 55%);
  color: var(--ink);
  font-family: ui-sans-serif, system-ui, sans-serif;
}
main {
  max-width: 880px;
  margin: 0 auto;
  padding: 48px 24px 80px;
}
.eyebrow {
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-size: 12px;
  color: var(--accent);
  margin: 0 0 12px;
}
h1 { font-size: 2rem; line-height: 1.2; margin: 0 0 12px; }
.lede, .meta, li, p { color: var(--muted); line-height: 1.55; }
.meta { display: grid; gap: 8px; margin: 24px 0; padding: 16px; border: 1px solid var(--line); border-radius: 12px; }
.meta dt { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }
.meta dd { margin: 0; color: var(--ink); word-break: break-all; }
section { margin-top: 32px; }
h2 { font-size: 1.1rem; margin: 0 0 12px; }
.empty { border: 1px dashed var(--line); padding: 12px 14px; border-radius: 10px; }
.stamp { color: var(--accent); font-size: 12px; }
.transcript { white-space: pre-wrap; }
button, [role="button"] { cursor: pointer; }
.honesty {
  font-size: 0.92rem;
  border-left: 3px solid var(--accent);
  padding: 8px 12px;
  margin: 16px 0 0;
}
.sop label { display: block; cursor: pointer; }
.sop input[type="checkbox"] { margin-right: 8px; accent-color: var(--accent); }
.mini-shell { display: flex; flex-direction: column; gap: 20px; }
.mini-toolbar {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
  padding: 12px 14px; border: 1px solid var(--line); border-radius: 12px;
  background: rgba(0, 0, 0, 0.2);
}
.mini-toolbar button {
  border: 1px solid var(--line); background: transparent; color: var(--ink);
  padding: 8px 14px; border-radius: 999px; font-size: 0.92rem;
}
.mini-toolbar button[aria-selected="true"] {
  border-color: var(--accent); color: var(--accent); background: rgba(94, 234, 212, 0.08);
}
.progress-wrap { flex: 1; min-width: 140px; }
.progress-label { font-size: 12px; color: var(--muted); margin-bottom: 6px; }
.progress-track { height: 8px; border-radius: 999px; background: rgba(255,255,255,0.08); overflow: hidden; }
.progress-fill { height: 100%; width: 0%; background: linear-gradient(90deg, var(--accent), #38bdf8); transition: width 0.2s ease; }
.panel { display: none; }
.panel[data-active="true"] { display: block; }
.action-list, .tool-grid { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.action-card, .tool-card {
  border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px;
  background: rgba(255,255,255,0.02);
}
.action-card label { display: flex; gap: 10px; align-items: flex-start; cursor: pointer; }
.action-card input { margin-top: 4px; accent-color: var(--accent); }
.badge { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--accent); }
.tool-card button {
  width: 100%; text-align: left; border: 1px dashed var(--line); background: transparent;
  color: var(--ink); padding: 10px 12px; border-radius: 10px;
}
.tool-card button[data-pinned="true"] { border-style: solid; border-color: var(--accent); }
.chapter-jump { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.chapter-jump button {
  border: 1px solid var(--line); background: transparent; color: var(--muted);
  padding: 6px 10px; border-radius: 8px; font-size: 12px;
}
.chapter-jump button[data-active="true"] { color: var(--accent); border-color: var(--accent); }
`;
}

function actionItemsList(items: AppBuilderActionItem[]): string {
  if (items.length === 0) {
    return '<p class="empty" data-testid="action-items-empty">No ship actions on this pack yet — use SOP steps in Runbook.</p>';
  }
  const rows = items
    .map((item) => {
      const diff = item.difficulty ? `<span class="badge">${escapeHtml(item.difficulty)}</span> ` : '';
      const kind = item.type ? `<span class="badge">${escapeHtml(item.type)}</span> ` : '';
      return `<li class="action-card" data-testid="action-item"><label><input type="checkbox" data-action-id="${escapeHtml(item.id)}" data-testid="action-check" /><span><strong>${escapeHtml(item.title)}</strong> ${diff}${kind}<p>${escapeHtml(item.description)}</p></span></label></li>`;
    })
    .join('');
  return `<ul class="action-list" data-testid="action-items">${rows}</ul>`;
}

function toolsGrid(tools: AppBuilderStackTool[]): string {
  if (tools.length === 0) {
    return '<p class="empty" data-testid="stack-tools-empty">No stack.tools on this pack.</p>';
  }
  const rows = tools
    .map((tool) => {
      const kind = tool.kind ? ` · ${escapeHtml(tool.kind)}` : '';
      const evidence = tool.evidence ? `<p>${escapeHtml(excerpt(tool.evidence, 160))}</p>` : '';
      const docs =
        tool.docs_url && tool.docs_url.startsWith('http')
          ? `<p><a href="${escapeHtml(tool.docs_url)}" target="_blank" rel="noopener noreferrer">Docs</a></p>`
          : '';
      return `<li class="tool-card" data-testid="stack-tool"><button type="button" data-tool-name="${escapeHtml(tool.name)}" data-testid="tool-pin">${escapeHtml(tool.name)}${kind}</button>${evidence}${docs}</li>`;
    })
    .join('');
  return `<ul class="tool-grid" data-testid="stack-tools">${rows}</ul><p class="honesty">Pin tools you plan to use — local preference only, not a deploy receipt.</p>`;
}

function chapterJumpButtons(chapters: AppBuilderChapter[]): string {
  if (chapters.length === 0) return '';
  const buttons = chapters
    .map((chapter, index) => {
      const label = excerpt(chapter.topic, 48);
      return `<button type="button" data-chapter-index="${index}" data-testid="chapter-jump">${escapeHtml(label)}</button>`;
    })
    .join('');
  return `<div class="chapter-jump" data-testid="chapter-jumps">${buttons}</div>`;
}

function indexHtml(input: AppBuilderSandboxInput): string {
  const actionItems = input.actionItems ?? [];
  const stackTools = input.stackTools ?? [];
  const chapters = input.chapters ?? [];
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>UVAI▶ Video Pack · ${escapeHtml(input.videoId)}</title>
    <link rel="stylesheet" href="/src/styles.css" />
  </head>
  <body>
    <main id="app" class="mini-shell" data-testid="app-builder-sandbox" data-video-id="${escapeHtml(input.videoId)}">
      <p class="eyebrow">UVAI▶ hosted mini-app</p>
      <h1>Video Pack ${escapeHtml(input.videoId)}</h1>
      <p class="lede">Runnable surface from your stored Video Pack — ship actions, runbook steps, stack tools, and reference transcript/visuals.</p>
      <p class="honesty" data-testid="assembly-honesty">Interactive controls are grounded in pack fields (action_items, requirements/SOP, stack.tools). This does not recreate the demonstrated application or claim deploy. Same-origin <code>/d/${escapeHtml(input.videoId)}</code> when the hosted spec is READY. Origin G.A.T.E. <code>studio.deploy</code> stays separate.</p>
      <dl class="meta">
        <div><dt>Source</dt><dd>${escapeHtml(input.sourceUrl)}</dd></div>
        <div><dt>source_hash</dt><dd>${escapeHtml(input.sourceHash)}</dd></div>
        <div><dt>Pack id</dt><dd>${escapeHtml(input.packId || `vp:v0:${input.videoId}`)}</dd></div>
      </dl>
      <div class="mini-toolbar" data-testid="pack-mini-app" role="tablist" aria-label="Pack workbench">
        <button type="button" role="tab" data-mini-tab="actions" data-testid="mini-app-tab" aria-selected="true">Actions</button>
        <button type="button" role="tab" data-mini-tab="runbook" data-testid="mini-app-tab" aria-selected="false">Runbook</button>
        <button type="button" role="tab" data-mini-tab="stack" data-testid="mini-app-tab" aria-selected="false">Stack</button>
        <button type="button" role="tab" data-mini-tab="explore" data-testid="mini-app-tab" aria-selected="false">Explore</button>
        <div class="progress-wrap" data-testid="mini-app-progress">
          <div class="progress-label"><span data-testid="progress-label">0% ship progress</span></div>
          <div class="progress-track" aria-hidden="true"><div class="progress-fill" data-testid="progress-fill"></div></div>
        </div>
      </div>
      ${chapterJumpButtons(chapters)}
      <section class="panel" data-panel="actions" data-active="true" data-testid="panel-actions">
        <h2>Ship actions</h2>
        ${actionItemsList(actionItems)}
      </section>
      <section class="panel" data-panel="runbook" data-testid="pack-sop">
        <h2>SOP steps</h2>
        ${sopList(input.sopSteps ?? [])}
      </section>
      <section class="panel" data-panel="stack" data-testid="panel-stack">
        <h2>Stack tools</h2>
        ${toolsGrid(stackTools)}
      </section>
      <section class="panel" data-panel="explore" data-testid="panel-explore">
        <section data-testid="pack-transcript-section">
          <h2>Transcript</h2>
          ${transcriptBlock(input.transcript)}
        </section>
        <section data-testid="pack-visual">
          <h2>Visual events</h2>
          ${visualList(input.visualEvents ?? [])}
        </section>
      </section>
    </main>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
`;
}

function packTs(input: AppBuilderSandboxInput): string {
  const payload = {
    videoId: input.videoId,
    sourceUrl: input.sourceUrl,
    sourceHash: input.sourceHash,
    packId: input.packId || `vp:v0:${input.videoId}`,
    transcript: input.transcript ?? { full_text: '', segments: [] },
    visualEvents: input.visualEvents ?? [],
    sopSteps: input.sopSteps ?? [],
    actionItems: input.actionItems ?? [],
    stackTools: input.stackTools ?? [],
    chapters: input.chapters ?? [],
  };
  return `export const pack = ${JSON.stringify(payload, null, 2)} as const;
`;
}

function mainTs(): string {
  return `import { pack } from './pack';

const root = document.querySelector<HTMLElement>('[data-testid="app-builder-sandbox"]');
if (root) {
  root.dataset.hydrated = 'true';
  root.dataset.videoId = pack.videoId;
  root.dataset.interactive = 'true';
}

const storagePrefix = \`uvai:mini-app:\${pack.videoId}:\${pack.sourceHash}\`;

type BoolMap = Record<string, boolean>;

function loadMap(key: string): BoolMap {
  try {
    const raw = localStorage.getItem(\`\${storagePrefix}:\${key}\`);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (parsed === null || typeof parsed !== 'object') return {};
    return parsed as BoolMap;
  } catch {
    return {};
  }
}

function saveMap(key: string, state: BoolMap): void {
  try {
    localStorage.setItem(\`\${storagePrefix}:\${key}\`, JSON.stringify(state));
  } catch {
    // quota / private mode
  }
}

function bindChecks(attr: string, storageKey: string): void {
  const state = loadMap(storageKey);
  const boxes = Array.from(document.querySelectorAll<HTMLInputElement>(\`input[\${attr}]\`));
  for (const box of boxes) {
    const id = box.getAttribute(attr);
    if (!id) continue;
    box.checked = state[id] === true;
    box.addEventListener('change', () => {
      const next = loadMap(storageKey);
      next[id] = box.checked;
      saveMap(storageKey, next);
      updateProgress();
    });
  }
}

function bindToolPins(): void {
  const state = loadMap('tools');
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-tool-name]'));
  for (const button of buttons) {
    const name = button.dataset.toolName;
    if (!name) continue;
    const pinned = state[name] === true;
    button.dataset.pinned = pinned ? 'true' : 'false';
    button.addEventListener('click', () => {
      const next = loadMap('tools');
      const now = !(next[name] === true);
      next[name] = now;
      saveMap('tools', next);
      button.dataset.pinned = now ? 'true' : 'false';
      updateProgress();
    });
  }
}

function updateProgress(): void {
  const actionBoxes = Array.from(document.querySelectorAll<HTMLInputElement>('input[data-action-id]'));
  const sopBoxes = Array.from(document.querySelectorAll<HTMLInputElement>('input[data-sop-id]'));
  const toolButtons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-tool-name]'));
  const checks = [...actionBoxes, ...sopBoxes];
  const doneChecks = checks.filter((el) => el.checked).length;
  const pinned = toolButtons.filter((el) => el.dataset.pinned === 'true').length;
  const total = checks.length + toolButtons.length;
  const done = doneChecks + pinned;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const label = document.querySelector('[data-testid="progress-label"]');
  const fill = document.querySelector<HTMLElement>('[data-testid="progress-fill"]');
  if (label) label.textContent = \`\${pct}% ship progress\`;
  if (fill) fill.style.width = \`\${pct}%\`;
}

function activateTab(tabId: string): void {
  const tabs = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-mini-tab]'));
  const panels = Array.from(document.querySelectorAll<HTMLElement>('section[data-panel]'));
  for (const tab of tabs) {
    const active = tab.dataset.miniTab === tabId;
    tab.setAttribute('aria-selected', active ? 'true' : 'false');
  }
  for (const panel of panels) {
    panel.dataset.active = panel.dataset.panel === tabId ? 'true' : 'false';
  }
}

function bindTabs(): void {
  const tabs = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-mini-tab]'));
  for (const tab of tabs) {
    tab.addEventListener('click', () => {
      const id = tab.dataset.miniTab;
      if (id) activateTab(id);
    });
  }
}

function bindChapterJumps(): void {
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-chapter-index]'));
  for (const button of buttons) {
    button.addEventListener('click', () => {
      for (const peer of buttons) peer.dataset.active = 'false';
      button.dataset.active = 'true';
      activateTab('explore');
    });
  }
}

bindTabs();
bindChecks('data-sop-id', 'sop');
bindChecks('data-action-id', 'actions');
bindToolPins();
bindChapterJumps();
updateProgress();
`;
}

function browserSmokeMjs(videoId: string): string {
  return `const url = process.env.SMOKE_URL || 'http://127.0.0.1:8080/';
const videoId = ${JSON.stringify(videoId)};

const response = await fetch(url, { signal: AbortSignal.timeout(15_000) });
const html = await response.text();
const hasMark = html.includes('data-testid="app-builder-sandbox"');
const hasVideo = html.includes(videoId);
const visible = hasMark && hasVideo && !/\\<main[^>]*>\\s*<\\/main>/i.test(html);
const verdict = {
  ok: response.ok && visible,
  url,
  status: response.status,
  visible,
  videoId,
};
console.log(JSON.stringify(verdict, null, 2));
if (!verdict.ok) {
  process.exit(1);
}
`;
}

function readme(input: AppBuilderSandboxInput): string {
  return `# UVAI▶ App Builder sandbox

Deterministic workspace emitted from Video Pack \`${input.videoId}\`.

Payload: action_items, stack.tools, SOP/requirements, transcript, and visual events. Architecture and code snippets are not shipped.

## Verify (Loop / agent)

1. Place these files at the workspace root (App Builder: \`/workspace\`).
2. \`npm install\`
3. \`sh startup.sh\` — probes \`http://127.0.0.1:8080/\`, then \`npm run dev\` on \`0.0.0.0:8080\`.
4. \`node scripts/browser-smoke.mjs\` — visible UI must include \`${input.videoId}\`.
5. \`npm run build\` and \`npm run typecheck\` must pass.
6. Optional \`mission.canvas\` is JSON Canvas 1.0 (https://github.com/groupthinking/jsoncanvas spec/1.0) from transcript + visual events + SOP only. Omitted when that slice is empty. Open in Obsidian or any JSON Canvas app. Keyframe \`image_path\` becomes a file node only when a captured frame was persisted.
7. Assembly (not emit-only): from the EventRelay repo run \`node apps/web/scripts/assemble-app-builder.mjs --from-sandbox sandbox.json --out <dir>\` or the focused Vitest gates. HTTP \`/api/video/assemble\` returns the identity receipt with gates labeled untested.

This cut does not claim a live deploy URL and does not run G.A.T.E. \`studio.deploy\`.
`;
}

export function visualEventsFromPack(input: {
  visual_context?: { visual_elements?: VideoPackVisualElement[] } | null;
  keyframes?: VideoPackKeyframe[];
}): AppBuilderVisualEvent[] {
  const fromVisual = (input.visual_context?.visual_elements ?? []).flatMap((element) => {
    const content = element.content.trim();
    if (!content) return [];
    return [
      {
        timestamp: element.timestamp,
        content,
        element_type: element.element_type,
      },
    ];
  });
  const fromFrames = (input.keyframes ?? []).flatMap((frame) => {
    const content = (frame.desc ?? '').trim();
    if (!content) return [];
    return [
      {
        timestamp: frame.t_s,
        content,
        element_type: 'keyframe',
        image_path: frame.image_path ?? null,
      },
    ];
  });
  return [...fromVisual, ...fromFrames];
}

export function actionItemsFromPack(input: {
  action_items?: VideoPackActionItem[];
  requirements?: VideoPackRequirement[];
}): AppBuilderActionItem[] {
  const parsed = parsePackActionItems(input.action_items ?? []);
  if (parsed.length > 0) {
    return parsed.map((item) => ({
      id: item.id,
      title: item.title,
      description: item.description,
      type: item.type ?? null,
      difficulty: item.difficulty ?? null,
      priority: item.priority ?? null,
    }));
  }
  return (input.requirements ?? []).flatMap((req, index) => {
    const title = req.title.trim();
    if (!title) return [];
    return [
      {
        id: req.id || `action_${index + 1}`,
        title,
        description: (req.detail ?? '').trim() || title,
        type: 'requirement',
        difficulty: null,
        priority: null,
      },
    ];
  });
}

export function stackToolsFromPack(stack?: { tools?: VideoPackStackTool[] } | null): AppBuilderStackTool[] {
  return (stack?.tools ?? []).flatMap((tool) => {
    const name = tool.name.trim();
    if (!name) return [];
    return [
      {
        name,
        kind: tool.kind ?? null,
        evidence: tool.evidence ?? null,
        docs_url: tool.docs_url ?? null,
      },
    ];
  });
}

export function chaptersFromPack(chapters?: VideoPackChapter[] | null): AppBuilderChapter[] {
  return (chapters ?? []).flatMap((chapter) => {
    const topic = chapter.topic.trim();
    if (!topic) return [];
    return [
      {
        start: chapter.start,
        end: chapter.end,
        topic,
        key_points: chapter.key_points ?? [],
      },
    ];
  });
}

export function sopStepsFromPack(input: {
  requirements?: VideoPackRequirement[];
  transcript?: AppBuilderTranscript | null;
}): AppBuilderSopStep[] {
  const requirements = input.requirements ?? [];
  if (requirements.length > 0) {
    return requirements.flatMap((req, index) => {
      const title = req.title.trim();
      if (!title) return [];
      return [
        {
          id: req.id || `sop_${index + 1}`,
          order: index + 1,
          title,
          description: (req.detail ?? '').trim(),
        },
      ];
    });
  }
  return (input.transcript?.segments ?? []).flatMap((segment, index) => {
    const text = segment.text.trim();
    if (!text) return [];
    return [
      {
        id: `sop_${index + 1}`,
        order: index + 1,
        title: excerpt(text, 80),
        description: text,
        timestamp: segment.start_s,
      },
    ];
  });
}

export function emitAppBuilderSandbox(input: AppBuilderSandboxInput): AppBuilderSandbox {
  assertIdentity(input);
  const videoId = input.videoId.trim();
  const sourceUrl = input.sourceUrl.trim();
  const sourceHash = input.sourceHash.trim();
  const packId = (input.packId || `vp:v0:${videoId}`).trim();
  const sopSteps = input.sopSteps ?? [];
  let actionItems = input.actionItems ?? [];
  if (actionItems.length === 0 && sopSteps.length > 0) {
    actionItems = sopSteps.map((step) => ({
      id: step.id,
      title: step.title,
      description: step.description,
      type: 'sop',
      difficulty: null,
      priority: null,
    }));
  }
  const normalized: AppBuilderSandboxInput = {
    videoId,
    sourceUrl,
    sourceHash,
    packId,
    transcript: input.transcript ?? { full_text: '', segments: [] },
    visualEvents: input.visualEvents ?? [],
    sopSteps,
    actionItems,
    stackTools: input.stackTools ?? [],
    chapters: input.chapters ?? [],
  };

  const sandbox: AppBuilderSandbox = {
    contract: APP_BUILDER_CONTRACT,
    cut: APP_BUILDER_CUT,
    videoId,
    sourceUrl,
    sourceHash,
    packId,
    preview: PREVIEW,
    ingredients: {
      transcript: normalized.transcript ?? { full_text: '', segments: [] },
      visualEvents: normalized.visualEvents ?? [],
      sopSteps: normalized.sopSteps ?? [],
      actionItems: normalized.actionItems ?? [],
      stackTools: normalized.stackTools ?? [],
      chapters: normalized.chapters ?? [],
    },
    files: {
      'startup.sh': startupSh(),
      'package.json': packageJson(),
      'tsconfig.json': tsconfigJson(),
      'vite.config.ts': viteConfigTs(),
      'index.html': indexHtml(normalized),
      'src/main.ts': mainTs(),
      'src/pack.ts': packTs(normalized),
      'src/styles.css': stylesCss(),
      'scripts/browser-smoke.mjs': browserSmokeMjs(videoId),
      'README.md': readme(normalized),
    },
  };
  const canvasFile = emitMissionCanvasFile(normalized);
  if (canvasFile) {
    sandbox.files[MISSION_CANVAS_FILENAME] = canvasFile;
  }
  return sandbox;
}

function isCitation(value: unknown): value is VideoPackCitation {
  if (value === null || typeof value !== 'object') return false;
  const row = value as VideoPackCitation;
  return (
    typeof row.videoId === 'string' &&
    typeof row.sourceUrl === 'string' &&
    typeof row.sourceHash === 'string' &&
    row.pack !== null &&
    typeof row.pack === 'object'
  );
}

function emitInputFromV0(pack: VideoPackV0Json | EmittedVideoPack): AppBuilderSandboxInput {
  const transcript = pack.transcript
    ? {
        full_text: pack.transcript.full_text,
        language: 'language' in pack.transcript ? pack.transcript.language : null,
        segments: pack.transcript.segments,
      }
    : null;
  return {
    videoId: pack.video_id,
    sourceUrl: pack.source_url,
    sourceHash: pack.provenance.source_hash,
    packId: pack.id,
    transcript,
    visualEvents: visualEventsFromPack({
      visual_context: pack.visual_context,
      keyframes: pack.keyframes,
    }),
    sopSteps: sopStepsFromPack({
      requirements: pack.requirements,
      transcript,
    }),
    actionItems: actionItemsFromPack({
      action_items: pack.action_items,
      requirements: pack.requirements,
    }),
    stackTools: stackToolsFromPack(pack.stack),
    chapters: chaptersFromPack(pack.chapters),
  };
}

/**
 * Materialize a sandbox from a stored Video Pack.
 * Architecture, artifacts, stack, and code_snippets are ignored on purpose
 * (cos-20260912-002) — packs invent types like SimpleKnotState / TireChangeContext.
 */
export function sandboxFromVideoPack(
  pack: VideoPackCitation | VideoPackV0Json | EmittedVideoPack,
): AppBuilderSandbox {
  if (isCitation(pack)) {
    return emitAppBuilderSandbox(emitInputFromV0(pack.pack));
  }
  return emitAppBuilderSandbox(emitInputFromV0(pack));
}
