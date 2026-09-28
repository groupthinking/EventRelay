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
import { uvaiEnterpriseTokensCss } from '@/lib/uvai-enterprise-tokens';

export const APP_BUILDER_CONTRACT = 'app-builder-workspace' as const;
export const APP_BUILDER_CUT = 'ingest→App Builder sandbox emit' as const;
/** Bumped when emitted mini-app chrome/CSS/JS changes (hosted /d re-emits on each request). */
export const APP_BUILDER_EMIT_REV = 'p1.13-pack-ask-light' as const;
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

/** Floor chapter start for DOM + embed; NaN/negative → omit seek (empty string). */
export function chapterStartSecondsAttr(start: number): string {
  if (!Number.isFinite(start) || start < 0) return '';
  return String(Math.floor(start));
}

/** YouTube nocookie embed URL with optional seek (used by emitted mini-app + unit tests). */
export function youtubeNocookieEmbedSrc(videoId: string, startSeconds?: number): string {
  const id = videoId.trim();
  const base = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}`;
  if (startSeconds === undefined) {
    return `${base}?enablejsapi=1`;
  }
  const start = Math.floor(startSeconds);
  if (!Number.isFinite(start) || start < 0) {
    return `${base}?enablejsapi=1`;
  }
  return `${base}?start=${start}&autoplay=1&enablejsapi=1`;
}

function visualList(events: AppBuilderVisualEvent[]): string {
  if (events.length === 0) {
    return '<p class="empty" data-testid="visual-empty">No visual events on this pack.</p>';
  }
  return `<ol class="events" data-testid="visual-events">${events
    .map((event) => {
      const stamp = Number.isFinite(event.timestamp) ? `${event.timestamp}s` : '';
      const kind = event.element_type ? ` · ${escapeHtml(event.element_type)}` : '';
      const startAttr = chapterStartSecondsAttr(event.timestamp);
      const startData = startAttr ? ` data-start-seconds="${escapeHtml(startAttr)}"` : '';
      const inner = `<span class="stamp">${escapeHtml(stamp)}${kind}</span> ${escapeHtml(event.content)}`;
      if (startData) {
        return `<li><button type="button" class="visual-event-row" data-testid="visual-event"${startData}>${inner}</button></li>`;
      }
      return `<li class="visual-event-static">${inner}</li>`;
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
        step.timestamp != null && Number.isFinite(step.timestamp)
          ? ` <span class="stamp">${escapeHtml(String(step.timestamp))}s</span>`
          : '';
      const startAttr =
        step.timestamp != null && Number.isFinite(step.timestamp)
          ? chapterStartSecondsAttr(step.timestamp)
          : '';
      const startData = startAttr ? ` data-start-seconds="${escapeHtml(startAttr)}"` : '';
      const titleHtml = startData
        ? `<button type="button" class="sop-title-seek" data-testid="sop-seek" data-sop-id="${escapeHtml(step.id)}"${startData}><strong>${escapeHtml(step.title)}</strong>${stamp}</button>`
        : `<strong>${escapeHtml(step.title)}</strong>${stamp}`;
      return `<li class="sop-step"><label><input type="checkbox" data-testid="sop-check" data-sop-id="${escapeHtml(step.id)}" /></label> ${titleHtml}<p>${escapeHtml(step.description)}</p></li>`;
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
  return `${uvaiEnterpriseTokensCss()}
:root {
  color-scheme: light;
  --surface-950: var(--uvai-surface);
  --surface-900: var(--uvai-elevated);
  --ink: var(--uvai-text);
  --muted: color-mix(in srgb, var(--uvai-text) 78%, transparent);
  --muted-tertiary: color-mix(in srgb, var(--uvai-muted) 90%, transparent);
  --line: var(--uvai-border);
  --accent: var(--uvai-primary);
  --accent-hover: var(--uvai-primary-hover);
  --evidence: var(--uvai-primary);
  --verified: var(--uvai-success);
  --radius-shell: 12px;
  --radius-row: 8px;
  --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  --font-sans: var(--uvai-font-sans);
}
/* Opt-in dark enterprise telemetry theme (option 1: not the default). */
:root[data-pack-theme="enterprise-dark"] {
  color-scheme: dark;
  --surface-950: #09090b;
  --surface-900: #111827;
  --ink: #fafafa;
  --muted: rgba(250, 250, 250, 0.7);
  --muted-tertiary: rgba(156, 163, 175, 0.9);
  --line: rgba(55, 65, 81, 0.9);
  --accent: #0c5cab;
  --accent-hover: #0a4a8a;
  --evidence: #38bdf8;
  --verified: #10b981;
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
.shell-viewport {
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
  max-height: 100dvh;
  overflow: hidden;
}
.app-chrome {
  flex-shrink: 0;
  z-index: 30;
  padding: 10px 14px 12px;
  background: var(--surface-900);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(8px);
}
.chrome-title h1 {
  font-family: var(--uvai-font-display, Georgia, "Times New Roman", serif);
  font-weight: 600;
  letter-spacing: -0.01em;
}
.saas-shell {
  flex: 1;
  min-height: 0;
  display: flex;
  width: 100%;
  background: var(--surface-950);
}
.shell-nav {
  flex: 0 0 auto;
  width: var(--shell-nav-w, 240px);
  min-width: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--line);
  background: var(--surface-900);
  overflow: hidden;
}
.shell-nav[data-collapsed="true"] {
  width: 44px;
  min-width: 44px;
}
.shell-nav-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 10px 8px;
  border-bottom: 1px solid var(--line);
}
.shell-nav-header h2 {
  margin: 0;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-tertiary);
  font-weight: 600;
}
.shell-nav[data-collapsed="true"] .shell-nav-header h2,
.shell-nav[data-collapsed="true"] .outline-body { display: none; }
.shell-icon-btn {
  flex-shrink: 0;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--muted);
  border-radius: 6px;
  width: 28px;
  height: 28px;
  padding: 0;
  font-size: 14px;
  line-height: 1;
}
.shell-icon-btn:hover { color: var(--ink); border-color: rgba(255, 255, 255, 0.2); }
.shell-icon-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.outline-body {
  flex: 1;
  overflow: auto;
  padding: 8px 8px 16px;
  font-size: 12px;
}
.outline-group { margin-bottom: 14px; }
.outline-group h3 {
  margin: 0 0 6px;
  font-size: 9px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted-tertiary);
  font-weight: 600;
}
.outline-list { list-style: none; margin: 0; padding: 0; }
.outline-list button {
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  color: var(--muted);
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 12px;
}
.outline-list button:hover { background: rgba(255, 255, 255, 0.04); color: var(--ink); }
.outline-list button[data-active="true"] {
  color: var(--accent);
  background: rgba(20, 184, 166, 0.1);
}
.outline-list button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.shell-splitter {
  flex: 0 0 5px;
  cursor: col-resize;
  background: transparent;
  position: relative;
  touch-action: none;
}
.shell-splitter::after {
  content: "";
  position: absolute;
  inset: 0 2px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
}
.shell-splitter:hover::after,
.shell-splitter[data-dragging="true"]::after {
  background: rgba(20, 184, 166, 0.35);
}
.shell-center {
  flex: 1 1 auto;
  min-width: 280px;
  min-height: 0;
  overflow: auto;
  padding: 0 12px 24px;
}
.shell-chat {
  flex: 0 0 auto;
  width: var(--shell-chat-w, 320px);
  min-width: 0;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--line);
  background: var(--surface-900);
}
.shell-chat[data-closed="true"] { display: none; }
.shell-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
}
.shell-chat-header h2 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.shell-chat-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.chat-bubble {
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.45;
  max-width: 100%;
}
.chat-bubble-system {
  background: var(--uvai-panel);
  border: 1px solid var(--line);
  color: var(--muted);
}
.chat-bubble-user {
  align-self: flex-end;
  background: rgba(12, 92, 171, 0.1);
  border: 1px solid rgba(12, 92, 171, 0.35);
  color: var(--ink);
}
.chat-bubble-assistant {
  align-self: flex-start;
  background: var(--surface-950);
  border: 1px solid var(--line);
  color: var(--ink);
}
.chat-cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chat-cta {
  border: 1px solid var(--line);
  background: var(--surface-950);
  color: var(--ink);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 500;
}
.chat-cta:hover { border-color: var(--accent); color: var(--accent); }
.chat-cta:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.chat-prompt-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.chat-prompt {
  width: 100%;
  text-align: left;
  border: 1px solid var(--line);
  background: var(--surface-950);
  color: var(--ink);
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}
.chat-prompt:hover { border-color: var(--accent); }
.chat-prompt:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.chat-prompt .prompt-hint {
  display: block;
  font-weight: 400;
  font-size: 11px;
  color: var(--muted);
}
/* Narrow viewports: assistant becomes a bottom sheet (YouTube-Ask pattern). */
@media (max-width: 900px) {
  .saas-shell { flex-direction: column; }
  .shell-chat {
    position: sticky;
    bottom: 0;
    z-index: 20;
    width: 100%;
    max-height: 52dvh;
    border-left: none;
    border-top: 1px solid var(--line);
    border-radius: 16px 16px 0 0;
    box-shadow: 0 -8px 24px rgba(15, 23, 42, 0.12);
  }
}
.shell-chat-composer {
  flex-shrink: 0;
  padding: 10px 12px 12px;
  border-top: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.shell-chat-composer textarea {
  width: 100%;
  min-height: 72px;
  resize: vertical;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--surface-950);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 13px;
  padding: 8px 10px;
}
.shell-chat-composer textarea:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
.shell-chat-composer .composer-note {
  margin: 0;
  font-size: 10px;
  color: var(--muted-tertiary);
}
.shell-chat-composer .composer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.shell-chat-composer button[type="submit"] {
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 600;
  background: var(--accent);
  color: #ffffff;
}
.shell-chat-composer button[type="submit"]:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.shell-chat-reopen {
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 40;
  border: none;
  border-radius: 999px;
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  background: var(--accent);
  color: #ffffff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
  display: none;
}
.shell-chat-reopen[data-visible="true"] { display: block; }
.workspace-hero {
  margin: 12px 0 10px;
  border: 1px solid var(--line);
  border-radius: var(--radius-shell);
  overflow: hidden;
  background: #000;
  aspect-ratio: 16 / 9;
  max-height: min(42vh, 420px);
}
.workspace-hero iframe {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
}
.workbench { max-width: none; margin: 0; padding: 0; }
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
.sop-step { display: grid; grid-template-columns: auto 1fr; gap: 4px 8px; align-items: start; }
.sop-step > label { display: inline-flex; padding-top: 2px; cursor: pointer; }
.sop-step > p { grid-column: 2; margin: 4px 0 0; }
.sop input[type="checkbox"] { margin: 0; accent-color: var(--accent); }
.sop-title-seek {
  grid-column: 2;
  display: inline;
  padding: 0;
  border: none;
  background: none;
  color: inherit;
  font: inherit;
  text-align: left;
}
.sop-title-seek:hover strong { color: var(--accent); text-decoration: underline; }
.sop li.is-done { opacity: 0.55; }
.sop li.is-done strong { text-decoration: line-through; }
.events { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.visual-event-row {
  width: 100%;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: var(--radius-row);
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.02);
  color: var(--ink);
  font: inherit;
}
.visual-event-row:hover { border-color: var(--accent); background: rgba(20, 184, 166, 0.08); }
.visual-event-static {
  border: 1px solid var(--line);
  border-radius: var(--radius-row);
  padding: 8px 10px;
  color: var(--muted);
}
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
.chapter-knowledge-list { display: grid; gap: 10px; margin-bottom: 16px; }
.chapter-knowledge-card {
  border: 1px solid var(--line);
  border-radius: var(--radius-row);
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.02);
}
.chapter-knowledge-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.chapter-knowledge-head h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}
.chapter-knowledge-seek {
  border: 1px solid var(--line);
  background: transparent;
  color: var(--muted);
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
}
.chapter-knowledge-seek:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.chapter-key-points {
  margin: 0;
  padding-left: 18px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
}
.chapter-key-points li { margin: 4px 0; }
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

export function filterChapterKeyPoints(key_points: string[] | undefined): string[] {
  return (key_points ?? [])
    .map((point) => (typeof point === 'string' ? point.trim() : ''))
    .filter((point) => point.length > 0);
}

function chapterKnowledgeExploreHtml(chapters: AppBuilderChapter[]): string {
  if (chapters.length === 0) return '';
  const cards = chapters
    .map((chapter, index) => {
      const points = filterChapterKeyPoints(chapter.key_points);
      const startAttr = chapterStartSecondsAttr(chapter.start);
      const startData = startAttr ? ` data-start-seconds="${escapeHtml(startAttr)}"` : '';
      const seekBtn = startAttr
        ? `<button type="button" class="chapter-knowledge-seek" data-chapter-index="${index}" data-testid="chapter-knowledge-seek"${startData}>Seek video</button>`
        : '';
      const bullets =
        points.length > 0
          ? `<ul class="chapter-key-points" data-testid="chapter-key-points">${points
              .map((point) => `<li>${escapeHtml(point)}</li>`)
              .join('')}</ul>`
          : '';
      return `<article class="chapter-knowledge-card" data-testid="chapter-knowledge-card" data-chapter-index="${index}">
        <header class="chapter-knowledge-head">
          <h3>${escapeHtml(chapter.topic)}</h3>
          ${seekBtn}
        </header>
        ${bullets}
      </article>`;
    })
    .join('');
  return `<section data-testid="pack-chapter-knowledge">
    <h2>Chapter knowledge</h2>
    <div class="chapter-knowledge-list">${cards}</div>
  </section>`;
}

function chapterJumpButtons(chapters: AppBuilderChapter[]): string {
  if (chapters.length === 0) return '';
  const buttons = chapters
    .map((chapter, index) => {
      const label = excerpt(chapter.topic, 48);
      const startAttr = chapterStartSecondsAttr(chapter.start);
      const startData = startAttr ? ` data-start-seconds="${escapeHtml(startAttr)}"` : '';
      return `<button type="button" data-chapter-index="${index}" data-testid="chapter-jump"${startData}>${escapeHtml(label)}</button>`;
    })
    .join('');
  return `<div class="chapter-jump" data-testid="chapter-jumps">${buttons}</div>`;
}

function outlineNavHtml(
  chapters: AppBuilderChapter[],
  sopSteps: AppBuilderSopStep[],
): string {
  const workspaceTabs = [
    { id: 'actions', label: 'Ship actions' },
    { id: 'runbook', label: 'Runbook' },
    { id: 'stack', label: 'Stack' },
    { id: 'explore', label: 'Explore' },
  ]
    .map(
      (tab) =>
        `<li><button type="button" data-outline-tab="${escapeHtml(tab.id)}" data-testid="outline-tab">${escapeHtml(tab.label)}</button></li>`,
    )
    .join('');
  const chapterItems =
    chapters.length === 0
      ? '<li><p class="empty" style="margin:0;padding:6px 8px;">No chapters on this pack.</p></li>'
      : chapters
          .map((chapter, index) => {
            const label = excerpt(chapter.topic, 56);
            const startAttr = chapterStartSecondsAttr(chapter.start);
            const startData = startAttr ? ` data-start-seconds="${escapeHtml(startAttr)}"` : '';
            return `<li><button type="button" data-outline-chapter="${index}" data-testid="outline-chapter"${startData}>${escapeHtml(label)}</button></li>`;
          })
          .join('');
  const sopItems =
    sopSteps.length === 0
      ? ''
      : `<div class="outline-group" data-testid="outline-sop">
          <h3>SOP</h3>
          <ul class="outline-list">
            ${sopSteps
              .map((step) => {
                const startAttr =
                  step.timestamp != null && Number.isFinite(step.timestamp)
                    ? chapterStartSecondsAttr(step.timestamp)
                    : '';
                const startData = startAttr ? ` data-start-seconds="${escapeHtml(startAttr)}"` : '';
                return `<li><button type="button" data-outline-tab="runbook" data-testid="outline-sop-jump"${startData}>${escapeHtml(excerpt(step.title, 52))}</button></li>`;
              })
              .join('')}
          </ul>
        </div>`;
  return `<nav class="outline-body" aria-label="Pack outline">
    <div class="outline-group" data-testid="outline-workspace">
      <h3>Workspace</h3>
      <ul class="outline-list">${workspaceTabs}</ul>
    </div>
    <div class="outline-group" data-testid="outline-chapters">
      <h3>Chapters</h3>
      <ul class="outline-list">${chapterItems}</ul>
    </div>
    ${sopItems}
  </nav>`;
}

function workspaceHeroHtml(videoId: string, sourceUrl: string): string {
  const embed = youtubeNocookieEmbedSrc(videoId);
  return `<section class="workspace-hero" data-testid="workspace-hero" aria-label="Source video">
    <iframe
      data-testid="source-youtube"
      src="${escapeHtml(embed)}"
      title="YouTube source for ${escapeHtml(videoId)}"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
      allowfullscreen
      loading="lazy"
      referrerpolicy="strict-origin-when-cross-origin"
    ></iframe>
    <p class="meta-collapsed" style="padding:6px 10px;margin:0;background:rgba(0,0,0,0.65);">
      <a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">Open on YouTube</a>
    </p>
  </section>`;
}

function chatRailHtml(_videoId: string): string {
  return `<aside class="shell-chat" data-testid="shell-chat-panel" data-closed="false" aria-label="Ask about this pack">
    <header class="shell-chat-header">
      <h2>Ask about this pack</h2>
      <button type="button" class="shell-icon-btn" data-testid="shell-chat-close" aria-label="Close assistant panel">×</button>
    </header>
    <div class="shell-chat-body" data-testid="shell-chat-messages">
      <div class="chat-bubble chat-bubble-system" data-testid="shell-chat-honesty">
        Pack-grounded answers only — I use stored pack fields (transcript, SOP, events). I will not invent ship receipts or G.A.T.E. PASS.
      </div>
      <div class="chat-prompt-row" data-testid="shell-chat-prompts" role="group" aria-label="Suggested questions">
        <button type="button" class="chat-prompt" data-chat-prompt="Summarize the video" data-testid="chat-prompt-summarize">Summarize the video<span class="prompt-hint">Key ideas from this pack</span></button>
        <button type="button" class="chat-prompt" data-chat-prompt="Recommend related content" data-testid="chat-prompt-recommend">Recommend related content<span class="prompt-hint">Chapters and SOP inside this pack</span></button>
        <button type="button" class="chat-prompt" data-chat-prompt="List the key components" data-testid="chat-prompt-components">List the key components<span class="prompt-hint">Actions, SOP steps, stack.tools</span></button>
      </div>
      <div class="chat-cta-row" data-testid="shell-chat-ctas" role="group" aria-label="Pack actions">
        <button type="button" class="chat-cta" data-chat-cta="summarize" data-testid="chat-cta-summarize">Summarize</button>
        <button type="button" class="chat-cta" data-chat-cta="extract" data-testid="chat-cta-extract">Extract</button>
        <button type="button" class="chat-cta" data-chat-cta="escalate" data-testid="chat-cta-escalate">Escalate</button>
      </div>
    </div>
    <form class="shell-chat-composer" data-testid="shell-chat-composer">
      <textarea
        name="message"
        rows="3"
        placeholder="Ask a question…"
        aria-label="Ask about this pack"
        data-testid="shell-chat-input"
      ></textarea>
      <p class="composer-note">AI can make mistakes — answers stay inside this pack. Not a deploy or G.A.T.E. claim.</p>
      <div class="composer-actions">
        <button type="submit" data-testid="shell-chat-send">Send</button>
      </div>
    </form>
  </aside>
  <button type="button" class="shell-chat-reopen" data-testid="shell-chat-reopen" data-visible="false" aria-label="Open pack assistant">Ask about this pack</button>`;
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
<html lang="en" data-pack-theme="light">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>UVAI▶ Video Pack · ${escapeHtml(input.videoId)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&amp;display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="/src/styles.css" />
  </head>
  <body>
    <div class="shell-viewport" data-testid="saas-three-panel-shell">
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
      <div class="saas-shell" data-testid="saas-shell-panels">
        <aside class="shell-nav" data-testid="shell-nav-panel" data-collapsed="false" aria-label="Pack navigation">
          <div class="shell-nav-header">
            <h2>Outline</h2>
            <button type="button" class="shell-icon-btn" data-testid="shell-nav-collapse" aria-label="Collapse navigation" title="Collapse">‹</button>
          </div>
          ${outlineNavHtml(chapters, sopSteps)}
        </aside>
        <div class="shell-splitter shell-splitter-left" data-testid="shell-splitter-left" role="separator" aria-orientation="vertical" aria-label="Resize navigation"></div>
        <main class="shell-center workbench">
          ${workspaceHeroHtml(input.videoId, input.sourceUrl)}
          <div
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
              ${chapterKnowledgeExploreHtml(chapters)}
              <section data-testid="pack-transcript-section">
                <h2>Transcript</h2>
                ${transcriptBlock(input.transcript)}
              </section>
              <section data-testid="pack-visual">
                <h2>Visual events</h2>
                ${visualList(input.visualEvents ?? [])}
              </section>
            </section>
          </div>
        </main>
        <div class="shell-splitter shell-splitter-right" data-testid="shell-splitter-right" role="separator" aria-orientation="vertical" aria-label="Resize assistant"></div>
        ${chatRailHtml(input.videoId)}
      </div>
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
  syncOutlineTabs(tabId);
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

function parseStartSecondsFromButton(button: HTMLElement): number | null {
  const raw = button.getAttribute('data-start-seconds');
  if (raw == null || raw === '') return null;
  const n = Number(raw);
  if (!Number.isFinite(n) || n < 0) return null;
  return Math.floor(n);
}

function seekSourceVideo(startSeconds: number | null): void {
  if (startSeconds == null) return;
  const iframe = document.querySelector<HTMLIFrameElement>('[data-testid="source-youtube"]');
  if (!iframe) return;
  iframe.src = \`https://www.youtube-nocookie.com/embed/\${encodeURIComponent(pack.videoId)}?start=\${startSeconds}&autoplay=1&enablejsapi=1\`;
}

function highlightChapterJump(chapterIndex: string): void {
  const jumpButtons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-chapter-index]'));
  const match = jumpButtons.find((b) => b.dataset.chapterIndex === chapterIndex);
  for (const peer of jumpButtons) peer.dataset.active = 'false';
  if (match) {
    match.dataset.active = 'true';
    match.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  const outlineButtons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-outline-chapter]'));
  for (const peer of outlineButtons) peer.dataset.active = 'false';
  const outlineMatch = outlineButtons.find((b) => b.dataset.outlineChapter === chapterIndex);
  if (outlineMatch) outlineMatch.dataset.active = 'true';
}

function bindChapterJumps(): void {
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-chapter-index]'));
  for (const button of buttons) {
    button.addEventListener('click', () => {
      seekSourceVideo(parseStartSecondsFromButton(button));
      const idx = button.dataset.chapterIndex;
      if (idx != null) highlightChapterJump(idx);
      activateTab('explore');
      syncOutlineTabs('explore');
    });
  }
}

function bindVisualEventJumps(): void {
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-testid="visual-event"]'));
  for (const button of buttons) {
    button.addEventListener('click', () => {
      seekSourceVideo(parseStartSecondsFromButton(button));
      activateTab('explore');
      syncOutlineTabs('explore');
    });
  }
}

function bindSopTitleSeek(): void {
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-testid="sop-seek"]'));
  for (const button of buttons) {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      seekSourceVideo(parseStartSecondsFromButton(button));
      activateTab('runbook');
      syncOutlineTabs('runbook');
    });
  }
}

function syncOutlineTabs(tabId: string): void {
  const outlineTabs = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-outline-tab]'));
  for (const btn of outlineTabs) {
    btn.dataset.active = btn.dataset.outlineTab === tabId ? 'true' : 'false';
  }
}

function bindOutlineNav(): void {
  const tabButtons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-outline-tab]'));
  for (const btn of tabButtons) {
    btn.addEventListener('click', () => {
      seekSourceVideo(parseStartSecondsFromButton(btn));
      const tabId = btn.dataset.outlineTab;
      if (!tabId) return;
      activateTab(tabId);
      syncOutlineTabs(tabId);
    });
  }
  const chapterButtons = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-outline-chapter]'));
  for (const btn of chapterButtons) {
    btn.addEventListener('click', () => {
      seekSourceVideo(parseStartSecondsFromButton(btn));
      const idx = btn.dataset.outlineChapter;
      if (idx != null) highlightChapterJump(idx);
      activateTab('explore');
      syncOutlineTabs('explore');
    });
  }
  syncOutlineTabs('actions');
}

function bindPackTheme(): void {
  try {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get('theme');
    const stored = window.localStorage.getItem('uvai:pack-theme');
    const theme = requested === 'enterprise-dark' || stored === 'enterprise-dark' ? 'enterprise-dark' : 'light';
    document.documentElement.dataset.packTheme = theme;
    if (requested === 'enterprise-dark' || requested === 'light') {
      window.localStorage.setItem('uvai:pack-theme', requested);
    }
  } catch {
    document.documentElement.dataset.packTheme = 'light';
  }
}

function bindChatRail(): void {
  const messages = document.querySelector('[data-testid="shell-chat-messages"]');
  const input = document.querySelector<HTMLTextAreaElement>('[data-testid="shell-chat-input"]');
  const send = document.querySelector<HTMLButtonElement>('[data-testid="shell-chat-send"]');
  const form = document.querySelector<HTMLFormElement>('[data-testid="shell-chat-composer"]');
  const chat = document.querySelector<HTMLElement>('[data-testid="shell-chat-panel"]');
  const reopen = document.querySelector<HTMLElement>('[data-testid="shell-chat-reopen"]');
  const closeBtn = document.querySelector<HTMLButtonElement>('[data-testid="shell-chat-close"]');
  const ctas = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-chat-cta]'));
  const prompts = Array.from(document.querySelectorAll<HTMLButtonElement>('button[data-chat-prompt]'));

  const chatHistory: Array<{ role: 'user' | 'assistant'; content: string }> = [];
  let inFlight = false;

  function appendBubble(text: string, kind: 'user' | 'assistant' | 'system'): void {
    if (!messages) return;
    const bubble = document.createElement('div');
    if (kind === 'user') {
      bubble.className = 'chat-bubble chat-bubble-user';
    } else if (kind === 'assistant') {
      bubble.className = 'chat-bubble chat-bubble-assistant';
    } else {
      bubble.className = 'chat-bubble chat-bubble-system';
    }
    bubble.textContent = text;
    messages.appendChild(bubble);
    bubble.scrollIntoView({ block: 'nearest' });
  }

  function setComposerBusy(busy: boolean): void {
    inFlight = busy;
    if (send) {
      send.disabled = busy || !input || input.value.trim().length === 0;
      send.textContent = busy ? 'Sending…' : 'Send';
    }
    if (input) input.disabled = busy;
  }

  if (input && send) {
    input.addEventListener('input', () => {
      if (!inFlight) send.disabled = input.value.trim().length === 0;
    });
    send.disabled = input.value.trim().length === 0;
  }

  async function postLiveChat(text: string): Promise<void> {
    setComposerBusy(true);
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          query: text,
          video_id: pack.videoId,
          pack_id: pack.packId,
          video_url: pack.sourceUrl,
          history: chatHistory,
        }),
        signal: AbortSignal.timeout(60_000),
      });
      const data = (await response.json()) as { answer?: string };
      const answer =
        typeof data.answer === 'string' && data.answer.trim()
          ? data.answer.trim()
          : 'No assistant reply returned.';
      if (!response.ok) {
        appendBubble(answer, 'system');
        return;
      }
      chatHistory.push({ role: 'user', content: text });
      chatHistory.push({ role: 'assistant', content: answer });
      appendBubble(answer, 'assistant');
    } catch (error) {
      console.error('[shell-chat] live chat failed', error);
      appendBubble(
        'Could not reach /api/chat. Check your connection or try again later (rate limits apply).',
        'system',
      );
    } finally {
      setComposerBusy(false);
    }
  }

  if (form && input) {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text || inFlight) return;
      appendBubble(text, 'user');
      input.value = '';
      void postLiveChat(text);
    });
  }

  for (const cta of ctas) {
    cta.addEventListener('click', () => {
      const kind = cta.dataset.chatCta;
      if (!input) return;
      if (kind === 'summarize') {
        input.value = 'Summarize the transcript already shown in the Explore tab for this pack.';
      } else if (kind === 'extract') {
        input.value = 'List ship actions and SOP steps already on this page — do not invent new ones.';
      } else if (kind === 'escalate') {
        input.value = 'I need human help with this pack: ';
        appendBubble(
          'Escalation sends as a normal pack chat message — there is no separate support queue on this page yet.',
          'system',
        );
      }
      input.focus();
      if (send) send.disabled = input.value.trim().length === 0;
    });
  }

  for (const prompt of prompts) {
    prompt.addEventListener('click', () => {
      if (!input) return;
      const text = prompt.dataset.chatPrompt;
      if (!text) return;
      input.value = text;
      input.focus();
      if (send) send.disabled = input.value.trim().length === 0;
    });
  }

  function setChatClosed(closed: boolean): void {
    if (chat) chat.dataset.closed = closed ? 'true' : 'false';
    const rightSplitter = document.querySelector<HTMLElement>('[data-testid="shell-splitter-right"]');
    if (rightSplitter) rightSplitter.style.display = closed ? 'none' : '';
    if (reopen) reopen.dataset.visible = closed ? 'true' : 'false';
    try {
      localStorage.setItem(\`\${storagePrefix}:chat-closed\`, closed ? '1' : '0');
    } catch {
      // ignore
    }
  }

  closeBtn?.addEventListener('click', () => setChatClosed(true));
  reopen?.addEventListener('click', () => setChatClosed(false));

  try {
    const stored = localStorage.getItem(\`\${storagePrefix}:chat-closed\`);
    if (stored === '1') setChatClosed(true);
  } catch {
    // ignore
  }
}

function bindShellLayout(): void {
  const nav = document.querySelector<HTMLElement>('[data-testid="shell-nav-panel"]');
  const navToggle = document.querySelector<HTMLButtonElement>('[data-testid="shell-nav-collapse"]');
  const leftSplitter = document.querySelector<HTMLElement>('[data-testid="shell-splitter-left"]');
  const rightSplitter = document.querySelector<HTMLElement>('[data-testid="shell-splitter-right"]');
  const chat = document.querySelector<HTMLElement>('[data-testid="shell-chat-panel"]');
  const shell = document.querySelector<HTMLElement>('[data-testid="saas-shell-panels"]');
  const root = document.documentElement;

  const MIN_NAV = 180;
  const MAX_NAV = 420;
  const MIN_CHAT = 260;
  const MAX_CHAT = 480;

  function loadShellNumber(key: string, fallback: number): number {
    try {
      const raw = localStorage.getItem(\`\${storagePrefix}:\${key}\`);
      if (!raw) return fallback;
      const n = Number(raw);
      return Number.isFinite(n) ? n : fallback;
    } catch {
      return fallback;
    }
  }

  function saveShellNumber(key: string, value: number): void {
    try {
      localStorage.setItem(\`\${storagePrefix}:\${key}\`, String(Math.round(value)));
    } catch {
      // ignore
    }
  }

  const navW = loadShellNumber('nav-w', 240);
  const chatW = loadShellNumber('chat-w', 320);
  root.style.setProperty('--shell-nav-w', \`\${navW}px\`);
  root.style.setProperty('--shell-chat-w', \`\${chatW}px\`);

  function setNavCollapsed(collapsed: boolean): void {
    if (!nav || !navToggle) return;
    nav.dataset.collapsed = collapsed ? 'true' : 'false';
    navToggle.textContent = collapsed ? '›' : '‹';
    navToggle.setAttribute('aria-label', collapsed ? 'Expand navigation' : 'Collapse navigation');
    if (leftSplitter) leftSplitter.style.display = collapsed ? 'none' : '';
    try {
      localStorage.setItem(\`\${storagePrefix}:nav-collapsed\`, collapsed ? '1' : '0');
    } catch {
      // ignore
    }
  }

  navToggle?.addEventListener('click', () => {
    const collapsed = nav?.dataset.collapsed === 'true';
    setNavCollapsed(!collapsed);
  });

  try {
    if (localStorage.getItem(\`\${storagePrefix}:nav-collapsed\`) === '1') setNavCollapsed(true);
  } catch {
    // ignore
  }

  function startResize(
    side: 'left' | 'right',
    splitter: HTMLElement,
    onMove: (clientX: number) => void,
  ): void {
    splitter.dataset.dragging = 'true';
    const onPointerMove = (event: PointerEvent) => onMove(event.clientX);
    const onPointerUp = () => {
      splitter.dataset.dragging = 'false';
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
  }

  leftSplitter?.addEventListener('pointerdown', (event) => {
    if (nav?.dataset.collapsed === 'true') return;
    event.preventDefault();
    startResize('left', leftSplitter, (clientX) => {
      const bounds = shell?.getBoundingClientRect();
      if (!bounds) return;
      const next = Math.min(MAX_NAV, Math.max(MIN_NAV, clientX - bounds.left));
      root.style.setProperty('--shell-nav-w', \`\${next}px\`);
      saveShellNumber('nav-w', next);
    });
  });

  rightSplitter?.addEventListener('pointerdown', (event) => {
    if (chat?.dataset.closed === 'true') return;
    event.preventDefault();
    startResize('right', rightSplitter, (clientX) => {
      const bounds = shell?.getBoundingClientRect();
      if (!bounds) return;
      const next = Math.min(MAX_CHAT, Math.max(MIN_CHAT, bounds.right - clientX));
      root.style.setProperty('--shell-chat-w', \`\${next}px\`);
      saveShellNumber('chat-w', next);
    });
  });
}

bindTabs();
bindPackTheme();
bindChecks('data-sop-id', 'sop', 'li');
bindChecks('data-action-id', 'actions', '.action-card');
bindToolPins();
bindChapterJumps();
bindVisualEventJumps();
bindSopTitleSeek();
bindOutlineNav();
bindChatRail();
bindShellLayout();
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

/** Normalize text for honest SOP ↔ chapter/visual matching (no fuzzy guessing). */
function sopMatchNormalize(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function sopMatchTokens(text: string): Set<string> {
  const tokens = sopMatchNormalize(text).split(/\s+/).filter((w) => w.length > 3);
  return new Set(tokens);
}

function sopTokenOverlapScore(left: string, right: string): number {
  const a = sopMatchTokens(left);
  const b = sopMatchTokens(right);
  if (a.size === 0 || b.size === 0) return 0;
  let overlap = 0;
  for (const token of a) {
    if (b.has(token)) overlap += 1;
  }
  return overlap;
}

/**
 * Derive a seek timestamp only from existing pack fields (chapter starts or visual timestamps).
 * Requires a strong token overlap (≥2) or a clear substring relation — never invent times.
 */
export function deriveSopTimestampFromPackFields(
  step: { title: string; description: string },
  chapters: AppBuilderChapter[],
  visualEvents: AppBuilderVisualEvent[],
): number | undefined {
  const titleNorm = sopMatchNormalize(step.title);
  let bestChapter: { start: number; score: number } | null = null;
  for (const chapter of chapters) {
    const topicNorm = sopMatchNormalize(chapter.topic);
    const overlap = Math.max(
      sopTokenOverlapScore(step.title, chapter.topic),
      sopTokenOverlapScore(step.description, chapter.topic),
    );
    const substring =
      (titleNorm.length >= 8 && topicNorm.includes(titleNorm)) ||
      (topicNorm.length >= 8 && titleNorm.includes(topicNorm))
        ? 3
        : 0;
    const score = Math.max(overlap, substring);
    if (score >= 2 && Number.isFinite(chapter.start) && chapter.start >= 0) {
      if (!bestChapter || score > bestChapter.score) {
        bestChapter = { start: chapter.start, score };
      }
    }
  }
  if (bestChapter) return bestChapter.start;

  let bestVisual: { timestamp: number; score: number } | null = null;
  for (const event of visualEvents) {
    if (!Number.isFinite(event.timestamp) || event.timestamp < 0) continue;
    const score = Math.max(
      sopTokenOverlapScore(step.title, event.content),
      sopTokenOverlapScore(step.description, event.content),
    );
    if (score >= 2) {
      if (!bestVisual || score > bestVisual.score) {
        bestVisual = { timestamp: event.timestamp, score };
      }
    }
  }
  if (bestVisual) return bestVisual.timestamp;

  return undefined;
}

export function sopStepsFromPack(input: {
  requirements?: VideoPackRequirement[];
  transcript?: AppBuilderTranscript | null;
  chapters?: AppBuilderChapter[];
  visualEvents?: AppBuilderVisualEvent[];
}): AppBuilderSopStep[] {
  const requirements = input.requirements ?? [];
  const chapters = input.chapters ?? [];
  const visualEvents = input.visualEvents ?? [];
  if (requirements.length > 0) {
    return requirements.flatMap((req, index) => {
      const title = req.title.trim();
      if (!title) return [];
      const description = (req.detail ?? '').trim();
      const timestamp = deriveSopTimestampFromPackFields({ title, description }, chapters, visualEvents);
      return [
        {
          id: req.id || `sop_${index + 1}`,
          order: index + 1,
          title,
          description,
          ...(timestamp !== undefined ? { timestamp } : {}),
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
      chapters: chaptersFromPack(pack.chapters),
      visualEvents: visualEventsFromPack({
        visual_context: pack.visual_context,
        keyframes: pack.keyframes,
      }),
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
