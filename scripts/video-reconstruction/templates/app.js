'use strict';

const byId = (id) => document.getElementById(id);
const maxJsonBytes = 64 * 1024;
const maxImageBytes = 8 * 1024 * 1024;
const maxSeconds = 604800;
const show = (element, visible) => { element.hidden = !visible; };

function setError(element, message) {
  element.textContent = message;
  show(element, Boolean(message));
}

const views = [...document.querySelectorAll('[data-view]')];
function changeView() {
  const active = views.find((link) => link.hash === location.hash) ??
    (location.hash === '#main-content' ? views.find((link) => link.hasAttribute('aria-current')) : undefined) ?? views[0];
  for (const link of views) {
    const selected = link === active;
    show(byId(link.dataset.view), selected);
    if (selected) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
}
window.addEventListener('hashchange', changeView);
changeView();

const themeButton = byId('theme');
function setTheme(dark) {
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  themeButton.setAttribute('aria-pressed', String(dark));
}
setTheme(matchMedia('(prefers-color-scheme: dark)').matches);
themeButton.addEventListener('click', () => setTheme(themeButton.getAttribute('aria-pressed') !== 'true'));

for (const button of document.querySelectorAll('[data-dismiss]')) {
  button.addEventListener('click', () => button.closest('dialog').close());
}

function youtubeUrl(raw) {
  const input = raw.trim();
  const authority = /^https:\/\/([a-z0-9.-]+)(?=[/?#]|$)/i.exec(input);
  if (!authority || input.length > 2048 || /[\s\\]/.test(input)) {
    throw new Error('Enter an HTTPS YouTube URL without credentials or a port.');
  }
  const url = new URL(input);
  const host = authority[1].toLowerCase();
  let id;
  if (host === 'youtu.be') {
    id = /^\/([A-Za-z0-9_-]{11})\/?$/.exec(url.pathname)?.[1];
  } else if (['youtube.com', 'www.youtube.com', 'm.youtube.com'].includes(host)) {
    if (url.pathname === '/watch' && url.searchParams.getAll('v').length === 1) id = url.searchParams.get('v');
    else id = /^\/shorts\/([A-Za-z0-9_-]{11})\/?$/.exec(url.pathname)?.[1];
  }
  if (!id || !/^[A-Za-z0-9_-]{11}$/.test(id)) throw new Error('Enter a supported YouTube watch, short link or Shorts URL with a valid video ID.');
  return 'https://www.youtube.com/watch?v=' + id;
}

const mediaDialog = byId('media-dialog');
if (mediaDialog) {
  const field = byId('youtube-url');
  const error = byId('media-error');
  byId('add-media').addEventListener('click', () => {
    field.value = '';
    field.removeAttribute('aria-invalid');
    setError(error, '');
    mediaDialog.showModal();
  });
  byId('media-form').addEventListener('submit', (event) => {
    event.preventDefault();
    try {
      byId('attached-url').textContent = youtubeUrl(field.value);
      show(byId('attachment-empty'), false);
      show(byId('attachment'), true);
      mediaDialog.close();
      byId('remove-media').focus();
    } catch (cause) {
      setError(error, cause instanceof Error ? cause.message : 'Enter a valid YouTube URL.');
      field.setAttribute('aria-invalid', 'true');
      field.focus();
    }
  });
  byId('remove-media').addEventListener('click', () => {
    byId('attached-url').textContent = '';
    show(byId('attachment'), false);
    show(byId('attachment-empty'), true);
    byId('add-media').focus();
  });
}

function exactKeys(value, fields) {
  return value !== null && typeof value === 'object' && !Array.isArray(value) &&
    Object.keys(value).length === fields.length && fields.every((field) => Object.hasOwn(value, field));
}

function validText(value, max) {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= max;
}

function validSeconds(value) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= maxSeconds;
}

function parseSummary(value) {
  if (!exactKeys(value, ['title', 'sections']) || !validText(value.title, 160) ||
      !Array.isArray(value.sections) || value.sections.length < 1 || value.sections.length > 32) {
    throw new Error('Summary data needs a title and 1–32 sections.');
  }
  let previousStart = 0;
  for (const section of value.sections) {
    if (!exactKeys(section, ['heading', 'startSeconds', 'endSeconds', 'text']) ||
        !validText(section.heading, 160) || !validText(section.text, 3000) ||
        !validSeconds(section.startSeconds) || !validSeconds(section.endSeconds) ||
        section.startSeconds < previousStart || section.endSeconds < section.startSeconds) {
      throw new Error('Each section needs a heading, text and an ordered timestamp range from 0 to 604800 seconds.');
    }
    previousStart = section.startSeconds;
  }
  return value;
}

function timestamp(seconds) {
  const milliseconds = Math.round(seconds * 1000);
  const clock = new Date(milliseconds).toISOString().slice(11, milliseconds % 1000 ? 23 : 19);
  const days = Math.floor(milliseconds / 86400000);
  const prefix = days ? days + 'd ' : '';
  return prefix + clock;
}

function showSummary(value) {
  byId('summary-name').textContent = value.title;
  const rows = value.sections.map((section) => {
    const item = document.createElement('li');
    const time = document.createElement('time');
    const start = section.startSeconds;
    const end = section.endSeconds;
    time.textContent = timestamp(start) + ' – ' + timestamp(end);
    time.dateTime = 'PT' + start + 'S';
    const heading = document.createElement('h4');
    heading.textContent = section.heading;
    const text = document.createElement('p');
    text.textContent = section.text;
    item.append(time, heading, text);
    return item;
  });
  byId('summary-sections').replaceChildren(...rows);
  show(byId('summary-empty'), false);
  show(byId('summary-result'), true);
}

function readBoxes(value) {
  if (!exactKeys(value, ['boxes']) || !Array.isArray(value.boxes) || value.boxes.length > 100) {
    throw new Error('Box data needs a boxes array with up to 100 entries.');
  }
  for (const box of value.boxes) {
    if (!exactKeys(box, ['label', 'x', 'y', 'width', 'height']) || !validText(box.label, 80) ||
        ![box.x, box.y, box.width, box.height].every((number) => typeof number === 'number' && Number.isFinite(number) && number >= 0 && number <= 1) ||
        box.width <= 0 || box.height <= 0 || box.x + box.width > 1 || box.y + box.height > 1) {
      throw new Error('Every box needs a label and positive normalized dimensions fully inside the image.');
    }
  }
  return value.boxes;
}

function showBoxes(boxes, raw) {
  const overlays = [];
  const labels = [];
  for (const box of boxes) {
    const overlay = document.createElement('div');
    overlay.className = 'box';
    overlay.style.left = box.x * 100 + '%';
    overlay.style.top = box.y * 100 + '%';
    overlay.style.width = box.width * 100 + '%';
    overlay.style.height = box.height * 100 + '%';
    const label = document.createElement('span');
    label.className = 'box-label';
    label.textContent = box.label;
    overlay.append(label);
    overlays.push(overlay);
    const listItem = document.createElement('li');
    listItem.textContent = box.label;
    labels.push(listItem);
  }
  if (labels.length === 0) {
    const message = document.createElement('li');
    message.textContent = 'No boxes in the imported data';
    labels.push(message);
  }
  byId('box-layer').replaceChildren(...overlays);
  byId('box-list').replaceChildren(...labels);
  byId('exact-box-json').textContent = raw;
  byId('toggle-boxes').checked = true;
  byId('box-source').open = false;
  show(byId('box-layer'), true);
  show(byId('boxes-empty'), false);
  show(byId('boxes-result'), true);
}

function resetBoxes() {
  byId('box-layer').replaceChildren();
  byId('box-list').replaceChildren();
  byId('exact-box-json').textContent = '';
  byId('boxes-empty').textContent = 'Import box data for this image.';
  show(byId('boxes-empty'), true);
  show(byId('boxes-result'), false);
}

async function imageMime(file) {
  if (!file.size || file.size > maxImageBytes) throw new Error('Choose a local PNG, JPEG or WebP image up to 8 MiB.');
  const header = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  let mime;
  if ([137, 80, 78, 71, 13, 10, 26, 10].every((byte, index) => header[index] === byte)) mime = 'image/png';
  if (header[0] === 255 && header[1] === 216 && header[2] === 255) mime = 'image/jpeg';
  const signature = String.fromCharCode(...header);
  if (signature.startsWith('RIFF') && signature.slice(8) === 'WEBP') mime = 'image/webp';
  if (!mime || (file.type && file.type !== mime)) throw new Error('Choose a valid PNG, JPEG or WebP image.');
  return mime;
}

const imageFile = byId('image-file');
if (imageFile) {
  let selection = 0;
  let imageUrl;
  imageFile.addEventListener('change', async () => {
    const file = imageFile.files[0];
    imageFile.value = '';
    if (!file) return;
    const request = ++selection;
    const error = byId('image-error');
    setError(error, '');
    let candidate;
    try {
      const mime = await imageMime(file);
      if (request !== selection) return;
      candidate = URL.createObjectURL(file.slice(0, file.size, mime));
      const decoded = new Image();
      decoded.src = candidate;
      await decoded.decode().catch(() => { throw new Error('The selected image cannot be decoded.'); });
      if (decoded.naturalWidth > 8192 || decoded.naturalHeight > 8192 || decoded.naturalWidth * decoded.naturalHeight > 24_000_000) {
        throw new Error('Choose an image within 8192 × 8192 pixels and 24 megapixels.');
      }
      if (request !== selection) return;
      const previous = byId('local-image');
      decoded.id = previous.id;
      decoded.alt = previous.alt;
      const displayWidth = Math.min(decoded.naturalWidth, 560 * decoded.naturalWidth / decoded.naturalHeight);
      byId('image-stage').style.width = displayWidth + 'px';
      previous.replaceWith(decoded);
      if (imageUrl) URL.revokeObjectURL(imageUrl);
      imageUrl = candidate;
      candidate = undefined;
      byId('image-name').textContent = file.name;
      resetBoxes();
      show(byId('spatial-empty'), false);
      show(byId('image-container'), true);
      byId('import-boxes').disabled = false;
    } catch (cause) {
      if (request === selection) setError(error, cause instanceof Error ? cause.message : 'The image could not be opened.');
    } finally {
      if (candidate) URL.revokeObjectURL(candidate);
    }
  });
  byId('toggle-boxes').addEventListener('change', (event) => show(byId('box-layer'), event.target.checked));
}

const jsonDialog = byId('json-dialog');
if (jsonDialog) {
  const field = byId('json-text');
  const fileInput = byId('json-file');
  const error = byId('json-error');
  const form = byId('json-form');
  const submit = form.querySelector('button[type="submit"]');
  let importer;
  let exactFileText;
  let fileRequest = 0;
  const discardFile = () => {
    fileRequest++;
    exactFileText = undefined;
    submit.disabled = false;
  };
  const startImport = (title, hint, apply) => {
    importer = apply;
    discardFile();
    field.value = '';
    fileInput.value = '';
    byId('json-title').textContent = title;
    byId('json-hint').textContent = hint;
    field.removeAttribute('aria-invalid');
    setError(error, '');
    jsonDialog.showModal();
  };
  const summaryButton = byId('import-summary');
  if (summaryButton && !byId('summary-card').hidden) {
    summaryButton.addEventListener('click', () => startImport('Import structured summary',
      'Use a title and sections with heading, startSeconds, endSeconds and text fields.',
      (value) => showSummary(parseSummary(value))));
    byId('clear-summary').addEventListener('click', () => {
      byId('summary-name').textContent = '';
      byId('summary-sections').replaceChildren();
      show(byId('summary-result'), false);
      show(byId('summary-empty'), true);
      summaryButton.focus();
    });
  }
  byId('import-boxes')?.addEventListener('click', () => startImport('Import normalized boxes',
    'Use a boxes array with label, x, y, width and height fields. Coordinates range from 0 to 1.',
    (value, raw) => showBoxes(readBoxes(value), raw)));
  jsonDialog.addEventListener('close', () => {
    if (!jsonDialog.open) discardFile();
  });
  field.addEventListener('input', discardFile);
  fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    fileInput.value = '';
    if (!file) return;
    discardFile();
    const request = fileRequest;
    field.value = '';
    field.removeAttribute('aria-invalid');
    setError(error, '');
    submit.disabled = true;
    try {
      if (!file.size || file.size > maxJsonBytes) throw new Error('Choose a nonempty JSON file up to 64 KiB.');
      const raw = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(await file.arrayBuffer());
      if (request !== fileRequest || !jsonDialog.open) return;
      exactFileText = raw;
      field.value = raw;
      field.removeAttribute('aria-invalid');
      setError(error, '');
    } catch (cause) {
      if (request === fileRequest && jsonDialog.open) {
        setError(error, cause instanceof Error ? cause.message : 'The JSON file could not be opened.');
      }
    } finally {
      if (request === fileRequest && jsonDialog.open) submit.disabled = false;
    }
  });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    const raw = exactFileText ?? field.value;
    try {
      if (!raw.trim() || new TextEncoder().encode(raw).byteLength > maxJsonBytes) {
        throw new Error('Enter JSON data up to 64 KiB.');
      }
      let value;
      try { value = JSON.parse(raw); }
      catch { throw new Error('Enter valid JSON data.'); }
      importer(value, raw);
      jsonDialog.close();
    } catch (cause) {
      setError(error, cause instanceof Error ? cause.message : 'The JSON data could not be imported.');
      field.setAttribute('aria-invalid', 'true');
      field.focus();
    }
  });
}
