import { readFileSync } from 'node:fs';
import {
  canonicalJson, createManifest, readProfile, sha256, type BrowserCapability, type LoadedSource, type Profile,
} from './contract.ts';

const template = (file: string) => readFileSync(new URL(`./templates/${file}`, import.meta.url), 'utf8');
const escape = (value: string) => value.replace(/[&<>"']/g, (character) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]!);

const acceptance: Record<BrowserCapability, string> = {
  'youtube-attachment': 'Validate, attach and remove a YouTube URL.',
  'summary-renderer': 'Import, read and clear a timestamped summary.',
  'box-renderer': 'Display a local image with imported boxes, toggle overlays and inspect the JSON.',
};

const videoMarkup = `<section id="video" class="view" hidden aria-labelledby="video-title">
  <div class="view-heading">
    <div><h1 id="video-title">Video analysis</h1><p>Attach a video link and review a structured summary.</p></div>
  </div>
  <div class="card-grid">
    <section id="prompt-card" class="card" aria-labelledby="prompt-title">
      <header class="card-heading"><div><h2 id="prompt-title">Prompt</h2><p>Keep your source and instructions together.</p></div></header>
      <div id="media-controls" hidden>
        <div id="attachment-empty" class="attachment-empty">
          <span class="media-symbol" aria-hidden="true">▶</span>
          <div><strong>YouTube video</strong><p>Attach a link for reference.</p></div>
          <button id="add-media" type="button" class="secondary">Add media</button>
        </div>
        <div id="attachment" class="attachment-empty" hidden>
          <span class="media-symbol" aria-hidden="true">▶</span>
          <div><strong>YouTube attachment</strong><p id="attached-url" class="url"></p></div>
          <button id="remove-media" type="button" class="secondary">Remove</button>
        </div>
        <p class="quiet tokens">Token count: <strong>Unknown</strong></p>
      </div>
      <label for="prompt">Instructions</label>
      <textarea id="prompt" maxlength="8000" rows="5" placeholder="Describe what to look for in your video"></textarea>
      <div class="model-controls">
        <button type="button" class="primary" disabled aria-describedby="model-reason">Run model</button>
        <p id="model-reason" class="quiet">Model inference requires a live backend.</p>
      </div>
    </section>
    <section id="summary-card" class="card" hidden aria-labelledby="summary-title">
      <header class="card-heading">
        <div><h2 id="summary-title">Structured summary</h2><p>Review sections in timestamp order.</p></div>
        <button id="import-summary" type="button" class="secondary">Import summary</button>
      </header>
      <div id="summary-empty" class="empty">
        <strong>No summary imported</strong>
        <p>Import a JSON file or paste summary data.</p>
      </div>
      <div id="summary-result" hidden>
        <div class="result-bar"><span class="tag">User-supplied output</span><button id="clear-summary" type="button" class="text-button">Clear summary</button></div>
        <h3 id="summary-name"></h3>
        <ol id="summary-sections" class="timeline"></ol>
      </div>
    </section>
  </div>
</section>`;

const spatialMarkup = `<section id="spatial" class="view" hidden aria-labelledby="spatial-title">
  <div class="view-heading">
    <div><h1 id="spatial-title">Spatial view</h1><p>Inspect a local image with user-supplied annotations.</p></div>
  </div>
  <div class="card-grid spatial-grid">
    <section class="card" aria-labelledby="image-title">
      <header class="card-heading">
        <div><h2 id="image-title">Image preview</h2><p>PNG, JPEG or WebP up to 8 MiB.</p></div>
        <label for="image-file" class="secondary file-label">Choose image<input id="image-file" type="file" accept="image/png,image/jpeg,image/webp"></label>
      </header>
      <p id="image-error" class="error" role="alert" hidden></p>
      <div id="spatial-empty" class="empty image-empty"><strong>No image selected</strong><p>Choose a local image to start.</p></div>
      <div id="image-container" class="image-container" hidden>
        <div id="image-stage" class="image-stage">
          <img id="local-image" alt="Selected local image">
          <div id="box-layer" class="box-layer" aria-hidden="true"></div>
        </div>
        <p id="image-name" class="quiet"></p>
      </div>
    </section>
    <section class="card" aria-labelledby="annotation-title">
      <header class="card-heading"><div><h2 id="annotation-title">Annotations</h2><p>Boxes use normalized image coordinates.</p></div><button id="import-boxes" class="secondary" type="button" disabled>Import boxes</button></header>
      <p id="boxes-empty" class="empty">Choose an image, then import its box data.</p>
      <div id="boxes-result" hidden>
        <div class="result-bar"><span class="tag">User-supplied annotations</span><label class="check-label"><input id="toggle-boxes" type="checkbox" checked> Show boxes</label></div>
        <ul id="box-list" class="box-list"></ul>
        <details id="box-source"><summary>Box JSON</summary><pre id="exact-box-json" tabindex="0"></pre></details>
      </div>
    </section>
  </div>
</section>`;

const mediaDialog = `<dialog id="media-dialog" aria-labelledby="media-dialog-title">
  <form id="media-form" novalidate>
    <h2 id="media-dialog-title">Attach YouTube video</h2>
    <label for="youtube-url">YouTube URL</label>
    <input id="youtube-url" type="url" inputmode="url" autocomplete="off" spellcheck="false" maxlength="2048" required autofocus aria-describedby="media-error">
    <p id="media-error" class="error" role="alert" hidden></p>
    <div class="dialog-actions"><button type="button" class="secondary" data-dismiss>Cancel</button><button class="primary" type="submit">Attach video</button></div>
  </form>
</dialog>`;

const jsonDialog = `<dialog id="json-dialog" aria-labelledby="json-title">
  <form id="json-form" novalidate>
    <h2 id="json-title"></h2>
    <p id="json-hint" class="quiet"></p>
    <label for="json-text">JSON data</label>
    <textarea id="json-text" class="json-text" rows="7" spellcheck="false" maxlength="65536" autofocus aria-describedby="json-hint json-error"></textarea>
    <p id="json-error" class="error" role="alert" hidden></p>
    <div class="dialog-actions">
      <label for="json-file" class="secondary file-label">Choose JSON file<input id="json-file" type="file" accept="application/json,.json"></label>
      <button type="button" class="secondary" data-dismiss>Cancel</button><button class="primary" type="submit">Import data</button>
    </div>
  </form>
</dialog>`;

function renderHtml(source: LoadedSource, profile: Profile) {
  const capabilities = new Set(profile.mappings.map(({ capability }) => capability));
  const media = capabilities.has('youtube-attachment');
  const summary = capabilities.has('summary-renderer');
  const spatial = capabilities.has('box-renderer');
  const videoMarkupForProfile = videoMarkup
    .replace('id="media-controls" hidden', media ? 'id="media-controls"' : 'id="media-controls" hidden')
    .replace('id="summary-card" class="card" hidden', summary ? 'id="summary-card" class="card"' : 'id="summary-card" class="card" hidden')
    .replace('Attach a video link and review a structured summary.', media && summary ? 'Attach a video link and review a structured summary.' :
      media ? 'Attach a video link and draft your instructions.' : 'Import a structured summary for review.');
  const entries = profile.mappings.map(({ capability, requirementId }) =>
    `<li><code>${escape(requirementId)}</code><span>${acceptance[capability]}</span></li>`).join('');
  // The grounded source adapter validates the video identity; construct the known safe watch URL.
  const watchUrl = `https://www.youtube.com/watch?v=${source.identity.videoId}`;
  return `<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'none'; base-uri 'none'; form-action 'none'; object-src 'none'">
<title>${escape(profile.name)}</title>
<link rel="icon" href="favicon.png" type="image/png">
<link rel="stylesheet" href="app.css">
<script defer src="app.js"></script>
</head>
<body>
<a class="skip" href="#main-content">Skip to workspace</a>
<div class="shell">
  <aside class="sidebar" aria-label="Workspace sidebar">
    <header class="brand">
      <div class="brand-mark" aria-hidden="true"><span></span></div>
      <div><strong>UVAI</strong><span>Video reconstruction</span></div>
    </header>
    <nav aria-label="Workspace views">
      ${media || summary ? '<a href="#video" data-view="video"><span class="nav-icon play-icon" aria-hidden="true"></span>Video analysis</a>' : ''}
      ${spatial ? '<a href="#spatial" data-view="spatial"><span class="nav-icon spatial-icon" aria-hidden="true"></span>Spatial view</a>' : ''}
    </nav>
    <details class="source">
      <summary>Source &amp; scope</summary>
      <p>${escape(profile.description)}</p>
      <p class="url"><a href="${watchUrl}" target="_blank" rel="noopener noreferrer">Watch source on YouTube ↗</a></p>
      <h2>Local acceptance</h2>
      <ul>${entries}</ul>
      <p>Full tutorial acceptance · <strong>HOLD</strong></p>
    </details>
  </aside>
  <main id="main-content" tabindex="-1">
    <header class="topbar"><div class="workspace-name">${escape(profile.name)}</div><button id="theme" type="button" class="secondary" aria-pressed="false">Dark mode</button></header>
    ${media || summary ? videoMarkupForProfile : ''}
    ${spatial ? spatialMarkup : ''}
  </main>
</div>
${media ? mediaDialog : ''}
${summary || spatial ? jsonDialog : ''}
</body>
</html>
`;
}

export function emitReconstruction(source: LoadedSource, profile: unknown) {
  const validated = readProfile(profile, source);
  const files = {
    'index.html': renderHtml(source, validated),
    'app.css': template('app.css'),
    'app.js': template('app.js'),
    'favicon.png': readFileSync(new URL('./templates/favicon.png', import.meta.url)),
  };
  const builderRevision = sha256(canonicalJson({
    emitter: sha256(readFileSync(new URL('./emitter.ts', import.meta.url))),
    css: sha256(files['app.css']),
    runtime: sha256(files['app.js']),
    icon: sha256(files['favicon.png']),
    contract: sha256(readFileSync(new URL('./contract.ts', import.meta.url))),
  }));
  return { files, manifest: createManifest(source, validated, { builderRevision, files }) };
}
