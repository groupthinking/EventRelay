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
/** Bumped when emitted mini-app chrome/CSS/JS changes (hosted /d re-emits on each request). */
export const APP_BUILDER_EMIT_REV = 'p1.2-workbench-chrome' as const;
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

function truncateHash(hash: string, visible = 12): string {
  if (hash.length <= visible + 1) return hash;
  return `${hash.slice(0, visible)}…`;
}

function tabLabel(name: string, count: number): string {
  return count > 0 ? `${name} · ${count}` : name;
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
  --surface-950: #020617;
  --surface-900: #0f172a;
  --ink: #f8fafc;
  --muted: rgba(248, 250, 252, 0.7);
  --muted-tertiary: rgba(248, 250, 252, 0.45);
  --line: rgba(255, 255, 255, 0.1);
  --accent: #14b8a6;
  --accent-hover: #2dd4bf;
  --evidence: #22d3ee;
  --verified: #22c55e;
  --radius-shell: 12px;
  --radius-row: 8px;
  --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  --font-sans: Inter, ui-sans-serif, system-ui, sans-serif;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  min-height: 100%;
  background: var(--surface-950);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.45;
}
.mono { font-family: var(--font-mono); font-size: 0.92em; }
.workbench { max-width: 960px; margin: 0 auto; padding: 0 16px 48px; }
.app-chrome {
  position: sticky;
  top: 0;
  z-index: 20;
  margin: 0 -16px;
  padding: 10px 16px 12px;
  background: rgba(2, 6, 23, 0.92);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(8px);
}
.chrome-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.chrome-title h1 {
  margin: 2px 0 0;
  font-size: 1.05rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.chrome-label {
  display: block;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-tertiary);
}
.status-chip {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid rgba(34, 197, 94, 0.45);
  color: var(--verified);
  background: rgba(34, 197, 94, 0.08);
}
.provenance {
  margin: 8px 0 0;
  font-size: 11px;
  color: var(--muted);
  word-break: break-all;
}
.mini-shell { display: flex; flex-direction: column; gap: 12px; padding-top: 12px; }
.honesty {
  font-size: 12px;
  color: var(--muted);
  border-left: 2px solid var(--accent);
  padding: 6px 10px;
  margin: 0;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 0 var(--radius-row) var(--radius-row) 0;
}
.workbench-rail {
  border: 1px solid var(--line);
  border-radius: var(--radius-shell);
  background: var(--surface-900);
  overflow: hidden;
}
.mini-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  padding: 6px;
  border-bottom: 1px solid var(--line);
}
.mini-toolbar button {
  border: none;
  background: transparent;
  color: var(--muted);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.02em;
}
.mini-toolbar button:hover { color: var(--ink); background: rgba(255, 255, 255, 0.04); }
.mini-toolbar button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.mini-toolbar button[aria-selected="true"] {
  color: var(--ink);
  background: rgba(20, 184, 166, 0.14);
  box-shadow: inset 0 0 0 1px rgba(20, 184, 166, 0.35);
}
.status-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.status-strip strong { color: var(--ink); font-weight: 600; }
.progress-track {
  flex: 1;
  min-width: 80px;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, var(--accent), var(--evidence));
  transition: width 0.2s ease;
}
@media (prefers-reduced-motion: reduce) {
  .progress-fill { transition: none; }
}
.panel { display: none; padding: 12px 14px 16px; }
.panel[data-active="true"] { display: block; }
.panel h2 {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted-tertiary);
  margin: 0 0 10px;
  font-weight: 600;
}
.panel-split {
  display: grid;
  gap: 12px;
}
@media (min-width: 720px) {
  .panel-split { grid-template-columns: 1fr minmax(200px, 240px); align-items: start; }
}
.panel-aside {
  border: 1px solid var(--line);
  border-radius: var(--radius-row);
  padding: 10px 12px;
  background: rgba(2, 6, 23, 0.5);
  font-size: 12px;
  color: var(--muted);
}
.panel-aside h3 {
  margin: 0 0 8px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--muted-tertiary);
}
.panel-aside .stat { margin: 0 0 6px; color: var(--ink); font-size: 13px; }
.empty {
  border: 1px dashed var(--line);
  padding: 10px 12px;
  border-radius: var(--radius-row);
  color: var(--muted);
  font-size: 13px;
}
.stamp { color: var(--evidence); font-size: 11px; font-family: var(--font-mono); }
.transcript { white-space: pre-wrap; color: var(--muted); font-size: 13px; }
button, [role="button"] { cursor: pointer; }
.sop label { display: block; cursor: pointer; }
.sop input[type="checkbox"] { margin-right: 8px; accent-color: var(--accent); }
.sop li.is-done { opacity: 0.55; }
.sop li.is-done strong { text-decoration: line-through; }
.action-list, .tool-grid { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.action-card, .tool-card {
  border: 1px solid var(--line);
  border-radius: var(--radius-row);
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.02);
}
.action-card.is-done { opacity: 0.62; }
.action-card.is-done strong { text-decoration: line-through; color: var(--muted); }
.action-card label { display: flex; gap: 10px; align-items: flex-start; cursor: pointer; }
.action-card input { margin-top: 3px; accent-color: var(--accent); flex-shrink: 0; }
.action-card input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.action-card strong { display: block; font-size: 13px; margin-bottom: 4px; }
.action-card p { margin: 4px 0 0; font-size: 12px; color: var(--muted); }
.action-meta { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }
.badge {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid rgba(20, 184, 166, 0.35);
  color: var(--accent);
  background: rgba(20, 184, 166, 0.08);
}
.badge-priority-high { border-color: rgba(250, 204, 21, 0.45); color: #facc15; }
.badge-priority-low { border-color: var(--line); color: var(--muted-tertiary); }
.tool-card[data-pinned="true"] { border-color: rgba(20, 184, 166, 0.45); background: rgba(20, 184, 166, 0.06); }
.tool-card button {
  width: 100%;
  text-align: left;
  border: 1px dashed var(--line);
  background: transparent;
  color: var(--ink);
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 13px;
}
.tool-card button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.tool-card button[data-pinned="true"] {
  border-style: solid;
  border-color: var(--accent);
}
.tool-card button::before {
  content: "Pin";
  display: inline-block;
  font-size: 9px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-right: 8px;
  color: var(--muted-tertiary);
}
.tool-card button[data-pinned="true"]::before { content: "Pinned"; color: var(--accent); }
.chapter-jump { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.chapter-jump button {
  border: 1px solid var(--line);
  background: transparent;
  color: var(--muted);
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 11px;
}
.chapter-jump button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.chapter-jump button[data-active="true"] { color: var(--accent); border-color: var(--accent); }
.meta-collapsed {
  margin: 0;
  font-size: 11px;
  color: var(--muted-tertiary);
}
.meta-collapsed a { color: var(--evidence); text-decoration: none; }
.meta-collapsed a:hover { text-decoration: underline; }
`;
}

function actionItemsList(items: AppBuilderActionItem[]): string {
  if (items.length === 0) {
    return '<p class="empty" data-testid="action-items-empty">No ship actions on this pack yet — use SOP steps in Runbook.</p>';
  }
  const rows = items
    .map((item) => {
      const diff = item.difficulty
        ? `<span class="badge badge-difficulty">${escapeHtml(item.difficulty)}</span>`
        : '';
      const pri = item.priority
        ? `<span class="badge badge-priority badge-priority-${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span>`
        : '';
      const kind = item.type ? `<span class="badge badge-kind">${escapeHtml(item.type)}</span>` : '';
      const meta = [diff, pri, kind].filter(Boolean).join('');
      const metaRow = meta ? `<span class="action-meta">${meta}</span>` : '';
      return `<li class="action-card" data-testid="action-item"><label><input type="checkbox" data-action-id="${escapeHtml(item.id)}" data-testid="action-check" aria-label="Mark action complete: ${escapeHtml(item.title)}" /><span><strong>${escapeHtml(item.title)}</strong>${metaRow}<p>${escapeHtml(item.description)}</p></span></label></li>`;
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
      return `<li class="tool-card" data-testid="stack-tool"><button type="button" data-tool-name="${escapeHtml(tool.name)}" data-testid="tool-pin" aria-pressed="false">${escapeHtml(tool.name)}${kind}</button>${evidence}${docs}</li>`;
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
  const sopSteps = input.sopSteps ?? [];
  const packId = input.packId || `vp:v0:${input.videoId}`;
  const hashShort = truncateHash(input.sourceHash);
  const actionsTab = tabLabel('Actions', actionItems.length);
  const runbookTab = tabLabel('Runbook', sopSteps.length);
  const stackTab = tabLabel('Stack', stackTools.length);
  const exploreTab = tabLabel('Explore', chapters.length > 0 ? chapters.length : 2);
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>UVAI▶ Video Pack · ${escapeHtml(input.videoId)}</title>
    <link rel="stylesheet" href="/src/styles.css" />
  </head>
  <body>
    <div class="workbench">
      <header class="app-chrome" data-testid="workbench-chrome">
        <div class="chrome-row">
          <div class="chrome-title">
            <span class="chrome-label">Video Pack</span>
            <h1 class="mono" title="Video Pack ${escapeHtml(input.videoId)}">${escapeHtml(input.videoId)}</h1>
          </div>
          <span class="status-chip" data-testid="pack-ready-chip">READY</span>
        </div>
        <p class="provenance mono" data-testid="pack-provenance">source_hash ${escapeHtml(hashShort)} · ${escapeHtml(packId)}</p>
      </header>
      <main
        id="app"
        class="mini-shell"
        data-testid="app-builder-sandbox"
        data-video-id="${escapeHtml(input.videoId)}"
        data-emit-rev="${APP_BUILDER_EMIT_REV}"
      >
        <p class="honesty" data-testid="assembly-honesty">Interactive controls are grounded in pack fields (action_items, requirements/SOP, stack.tools). This does not recreate the demonstrated application or claim deploy. Same-origin <code>/d/${escapeHtml(input.videoId)}</code> when the hosted spec is READY. Origin G.A.T.E. <code>studio.deploy</code> stays separate — checking items here is not G.A.T.E. PASS.</p>
        <p class="meta-collapsed"><a href="${escapeHtml(input.sourceUrl)}" target="_blank" rel="noopener noreferrer">Source</a> · <span class="mono">${escapeHtml(hashShort)}</span></p>
        <div class="workbench-rail">
          <div class="mini-toolbar" data-testid="pack-mini-app" role="tablist" aria-label="Pack workbench">
            <button type="button" role="tab" data-mini-tab="actions" data-testid="mini-app-tab" aria-selected="true">${escapeHtml(actionsTab)}</button>
            <button type="button" role="tab" data-mini-tab="runbook" data-testid="mini-app-tab" aria-selected="false">${escapeHtml(runbookTab)}</button>
            <button type="button" role="tab" data-mini-tab="stack" data-testid="mini-app-tab" aria-selected="false">${escapeHtml(stackTab)}</button>
            <button type="button" role="tab" data-mini-tab="explore" data-testid="mini-app-tab" aria-selected="false">${escapeHtml(exploreTab)}</button>
          </div>
          <div class="status-strip" data-testid="mini-app-progress" role="status" aria-live="polite">
            <span data-testid="progress-label">0 / 0 · 0%</span>
            <div class="progress-track" aria-hidden="true"><div class="progress-fill" data-testid="progress-fill"></div></div>
          </div>
        </div>
        ${chapterJumpButtons(chapters)}
        <section class="panel" data-panel="actions" data-active="true" data-testid="panel-actions">
          <div class="panel-split">
            <div class="panel-primary">
              <h2>Ship actions</h2>
              ${actionItemsList(actionItems)}
            </div>
            <aside class="panel-aside" data-testid="actions-progress-summary" aria-label="Ship progress summary">
              <h3>Summary</h3>
              <p class="stat" data-testid="actions-done-stat">Actions done: 0 / ${actionItems.length}</p>
              <p class="stat" data-testid="workbench-total-stat">Workbench: 0 / 0</p>
              <p>Local checklist — not deploy evidence.</p>
            </aside>
          </div>
        </section>
        <section class="panel" data-panel="runbook" data-testid="pack-sop">
          <h2>SOP steps</h2>
          ${sopList(sopSteps)}
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
    </div>
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

function setCheckVisual(box: HTMLInputElement, rowSelector: string): void {
  const row = box.closest(rowSelector);
  if (row) row.classList.toggle('is-done', box.checked);
}

function bindChecks(attr: string, storageKey: string, rowSelector: string): void {
  const state = loadMap(storageKey);
  const boxes = Array.from(document.querySelectorAll<HTMLInputElement>(\`input[\${attr}]\`));
  for (const box of boxes) {
    const id = box.getAttribute(attr);
    if (!id) continue;
    box.checked = state[id] === true;
    setCheckVisual(box, rowSelector);
    box.addEventListener('change', () => {
      const next = loadMap(storageKey);
      next[id] = box.checked;
      saveMap(storageKey, next);
      setCheckVisual(box, rowSelector);
      updateProgress();
    });
  }
}

function sortPinnedTools(): void {
  const grid = document.querySelector('[data-testid="stack-tools"]');
  if (!grid) return;
  const items = Array.from(grid.querySelectorAll<HTMLElement>(':scope > li'));
  items.sort((a, b) => {
    const ap = a.querySelector('button')?.dataset.pinned === 'true' ? 0 : 1;
    const bp = b.querySelector('button')?.dataset.pinned === 'true' ? 0 : 1;
    return ap - bp;
  });
  for (const item of items) grid.appendChild(item);
}

function bindToolPins(): void {
  const state = loadMap('tools');
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-tool-name]'));
  for (const button of buttons) {
    const name = button.dataset.toolName;
    if (!name) continue;
    const card = button.closest<HTMLElement>('[data-testid="stack-tool"]');
    const pinned = state[name] === true;
    button.dataset.pinned = pinned ? 'true' : 'false';
    button.setAttribute('aria-pressed', pinned ? 'true' : 'false');
    if (card) card.dataset.pinned = pinned ? 'true' : 'false';
    button.addEventListener('click', () => {
      const next = loadMap('tools');
      const now = !(next[name] === true);
      next[name] = now;
      saveMap('tools', next);
      button.dataset.pinned = now ? 'true' : 'false';
      button.setAttribute('aria-pressed', now ? 'true' : 'false');
      if (card) card.dataset.pinned = now ? 'true' : 'false';
      sortPinnedTools();
      updateProgress();
    });
  }
  sortPinnedTools();
}

function updateProgress(): void {
  const actionBoxes = Array.from(document.querySelectorAll<HTMLInputElement>('input[data-action-id]'));
  const sopBoxes = Array.from(document.querySelectorAll<HTMLInputElement>('input[data-sop-id]'));
  const toolButtons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-tool-name]'));
  const checks = [...actionBoxes, ...sopBoxes];
  const doneChecks = checks.filter((el) => el.checked).length;
  const actionsDone = actionBoxes.filter((el) => el.checked).length;
  const pinned = toolButtons.filter((el) => el.dataset.pinned === 'true').length;
  const total = checks.length + toolButtons.length;
  const done = doneChecks + pinned;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const label = document.querySelector('[data-testid="progress-label"]');
  const fill = document.querySelector<HTMLElement>('[data-testid="progress-fill"]');
  if (label) label.textContent = \`\${done} / \${total} · \${pct}%\`;
  if (fill) fill.style.width = \`\${pct}%\`;
  const actionsStat = document.querySelector('[data-testid="actions-done-stat"]');
  if (actionsStat) {
    actionsStat.textContent = \`Actions done: \${actionsDone} / \${actionBoxes.length}\`;
  }
  const workbenchStat = document.querySelector('[data-testid="workbench-total-stat"]');
  if (workbenchStat) {
    workbenchStat.textContent = \`Workbench: \${done} / \${total}\`;
  }
}

function activateTab(tabId: string): void {
  const tabs = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-mini-tab]'));
  const panels = Array.from(document.querySelectorAll<HTMLElement>('section[data-panel]'));
  for (const tab of tabs) {
    const active = tab.dataset.miniTab === tabId;
    tab.setAttribute('aria-selected', active ? 'true' : 'false');
    tab.tabIndex = active ? 0 : -1;
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
    tab.addEventListener('keydown', (event) => {
      if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
      const current = tabs.findIndex((t) => t.getAttribute('aria-selected') === 'true');
      if (current < 0) return;
      const delta = event.key === 'ArrowRight' ? 1 : -1;
      const next = tabs[(current + delta + tabs.length) % tabs.length];
      const id = next.dataset.miniTab;
      if (id) {
        activateTab(id);
        next.focus();
      }
      event.preventDefault();
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
bindChecks('data-sop-id', 'sop', 'li');
bindChecks('data-action-id', 'actions', '.action-card');
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
