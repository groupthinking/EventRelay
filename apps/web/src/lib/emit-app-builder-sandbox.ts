import type { VideoPackCitation, EmittedVideoPack } from '@/lib/emit-video-pack';
import { MISSION_CANVAS_FILENAME, emitMissionCanvasFile } from '@/lib/emit-json-canvas';
import type {
  VideoPackKeyframe,
  VideoPackRequirement,
  VideoPackV0Json,
  VideoPackVisualElement,
} from '@/lib/video-pack';

export const APP_BUILDER_CONTRACT = 'app-builder-workspace' as const;
export const APP_BUILDER_CUT = 'ingest→App Builder sandbox emit' as const;
export const APP_BUILDER_PREVIEW_HOST = '0.0.0.0' as const;
export const APP_BUILDER_PREVIEW_PORT = 8080;
export const APP_BUILDER_PROBE_URL = 'http://127.0.0.1:8080/';

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

export type AppBuilderSandboxInput = {
  videoId: string;
  sourceUrl: string;
  sourceHash: string;
  packId?: string;
  transcript?: AppBuilderTranscript | null;
  visualEvents?: AppBuilderVisualEvent[];
  sopSteps?: AppBuilderSopStep[];
};

export type AppBuilderSandboxPreview = {
  host: typeof APP_BUILDER_PREVIEW_HOST;
  port: typeof APP_BUILDER_PREVIEW_PORT;
  probe: typeof APP_BUILDER_PROBE_URL;
  start: 'npm run dev';
  smoke: 'node scripts/browser-smoke.mjs';
  gates: readonly ['npm run build', 'npm run typecheck'];
};

export type AppBuilderSandbox = {
  contract: typeof APP_BUILDER_CONTRACT;
  cut: typeof APP_BUILDER_CUT;
  videoId: string;
  sourceUrl: string;
  sourceHash: string;
  packId: string;
  preview: AppBuilderSandboxPreview;
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
  return `<ol class="sop" data-testid="sop-steps">${steps
    .map((step) => {
      const stamp = step.timestamp != null ? ` <span class="stamp">${escapeHtml(String(step.timestamp))}s</span>` : '';
      return `<li><strong>${escapeHtml(step.title)}</strong>${stamp}<p>${escapeHtml(step.description)}</p></li>`;
    })
    .join('')}</ol>`;
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
        typescript: '^5.7.0',
        vite: '^6.0.0',
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
        lib: ['ES2022', 'DOM'],
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
`;
}

function indexHtml(input: AppBuilderSandboxInput): string {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>UVAI▶ Video Pack · ${escapeHtml(input.videoId)}</title>
    <link rel="stylesheet" href="/src/styles.css" />
  </head>
  <body>
    <main id="app" data-testid="app-builder-sandbox" data-video-id="${escapeHtml(input.videoId)}">
      <p class="eyebrow">UVAI▶ App Builder sandbox</p>
      <h1>Video Pack ${escapeHtml(input.videoId)}</h1>
      <p class="lede">Running preview from paste-URL ingest. Payload is transcript, visual events, and SOP steps — not invented architecture.</p>
      <dl class="meta">
        <div><dt>Source</dt><dd>${escapeHtml(input.sourceUrl)}</dd></div>
        <div><dt>source_hash</dt><dd>${escapeHtml(input.sourceHash)}</dd></div>
        <div><dt>Pack id</dt><dd>${escapeHtml(input.packId || `vp:v0:${input.videoId}`)}</dd></div>
      </dl>
      <section data-testid="pack-transcript-section">
        <h2>Transcript</h2>
        ${transcriptBlock(input.transcript)}
      </section>
      <section data-testid="pack-visual">
        <h2>Visual events</h2>
        ${visualList(input.visualEvents ?? [])}
      </section>
      <section data-testid="pack-sop">
        <h2>SOP steps</h2>
        ${sopList(input.sopSteps ?? [])}
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
}
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

Payload: transcript + visual events + SOP steps. Architecture and code snippets are not shipped.

## Verify (Loop / agent)

1. Place these files at the workspace root (App Builder: \`/workspace\`).
2. \`npm install\`
3. \`sh startup.sh\` — probes \`http://127.0.0.1:8080/\`, then \`npm run dev\` on \`0.0.0.0:8080\`.
4. \`node scripts/browser-smoke.mjs\` — visible UI must include \`${input.videoId}\`.
5. \`npm run build\` and \`npm run typecheck\` must pass.
6. Optional \`mission.canvas\` is JSON Canvas 1.0 (https://github.com/groupthinking/jsoncanvas spec/1.0) from transcript + visual events + SOP only. Omitted when that slice is empty. Open in Obsidian or any JSON Canvas app. Keyframe \`image_path\` becomes a file node only when a captured frame was persisted.

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
  const normalized: AppBuilderSandboxInput = {
    videoId,
    sourceUrl,
    sourceHash,
    packId,
    transcript: input.transcript ?? { full_text: '', segments: [] },
    visualEvents: input.visualEvents ?? [],
    sopSteps: input.sopSteps ?? [],
  };

  const sandbox: AppBuilderSandbox = {
    contract: APP_BUILDER_CONTRACT,
    cut: APP_BUILDER_CUT,
    videoId,
    sourceUrl,
    sourceHash,
    packId,
    preview: PREVIEW,
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
