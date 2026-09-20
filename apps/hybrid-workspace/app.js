import { attachFx, fxPrompt } from "./fx-adapter.js";

const FILES = {
  "index.html": {
    language: "html",
    value: `<!DOCTYPE html>\n<html>\n<head>\n  <link rel=\"stylesheet\" href=\"styles.css\" />\n  <title>Animal Trading Cards</title>\n</head>\n<body>\n  <article class=\"card\">\n    <h1>Clownfish</h1>\n    <img alt=\"Clownfish\" src=\"https://upload.wikimedia.org/wikipedia/commons/a/aa/Amphiprion_ocellaris_%28Clown_anemonefish%29_in_Heteractis_magnifica_%28Magnificent_sea_anemone%29.jpg\" width=\"280\" />\n    <p class=\"fact\">A layer of mucus on the clownfish skin makes it immune to the host anemone sting.</p>\n    <p class=\"sci\">Scientific Name: Amphiprioninae</p>\n  </article>\n  <script src=\"app.js\"><\\/script>\n</body>\n</html>`,
  },
  "styles.css": {
    language: "css",
    value: `body { font-family: Georgia, serif; background: #f3f7fb; }\n.card { max-width: 320px; margin: 24px auto; background: #fff; padding: 16px; border-radius: 12px; box-shadow: 0 8px 24px rgba(15,23,42,.08); }\nh1 { margin: 0 0 8px; }\n.fact { color: #334155; }\n.sci { font-style: italic; color: #64748b; }`,
  },
  "app.js": {
    language: "javascript",
    value: `document.querySelector(\".card\")?.addEventListener(\"click\", () => {\n  console.log(\"Inspected trading card\");\n});`,
  },
  "lesson.md": {
    language: "markdown",
    value: `# Project Overview: Animal Trading Cards\n\nRecreate a webpage from a design prototype using HTML and CSS.\n\nRequirements:\n- Build a card for an animal of your choice\n- Include an image, interesting fact, and scientific name\n- Submit a zip when complete\n\nThis is the common front-end workflow: prototype → markup → live page.`,
  },
};

const SUGGESTIONS = [
  { id: "summarize", label: "Summarize the video" },
  { id: "related", label: "Recommend related content" },
  { id: "why", label: "Why build custom design tools?" },
  { id: "what", label: "What is this workspace?" },
  { id: "list", label: "List the project key components" },
];

const state = {
  file: "index.html",
  models: {},
  editor: null,
  term: null,
  fx: null,
  tickets: 2023732,
};

const thread = document.getElementById("thread");
const filesEl = document.getElementById("files");
const preview = document.getElementById("preview");
const ask = document.getElementById("ask");

function addMsg(role, html) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.innerHTML = `<span class=\"meta\">${role === \"bot\" ? \"Workspace AI\" : \"You\"}</span>${html}`;
  thread.appendChild(el);
  thread.scrollTop = thread.scrollHeight;
}

function renderPreview() {
  const html = FILES[\"index.html\"].value
    .replace(`<link rel=\"stylesheet\" href=\"styles.css\" />`, `<style>${FILES[\"styles.css\"].value}</style>`)
    .replace(`<script src=\"app.js\"><\\/script>`, `<script>${FILES[\"app.js\"].value}<\\/script>`);
  preview.srcdoc = html;
}

function summarize() {
  const lesson = FILES[\"lesson.md\"].value;
  return `The project asks you to turn a design prototype into a live Animal Trading Card page with HTML and CSS. You apply layout, typography, and an image plus a scientific fact, then submit a zip. Keep the preview open while you edit so you never leave the workspace.<pre>${lesson.split(\"\\n\").slice(0, 6).join(\"\\n\")}</pre>`;
}

function extract() {
  const sel = state.editor?.getModel()?.getValueInRange(state.editor.getSelection()) || \"\";
  const clip = sel.trim() || FILES[state.file].value.slice(0, 280);
  return `Extracted from <b>${state.file}</b>:<blockquote>${escapeHtml(clip)}</blockquote>This is the source the preview is rendering. Clarify structure (card, fact, scientific name) before changing styles.`;
}

function escalate() {
  const id = `#${state.tickets++}`;
  return `Problem summary captured from this session (preview + editor + last action). Human support ticket <span class=\"ticket\">${id}</span> is filed. You should hear from a support person soon.`;
}

function embedCopy() {
  return `Split screen stays locked: project workspace on the left (tree + Monaco + live iframe), assistant on the right. Use the gutters to resize without breaking focus.`;
}

function answer(action, text) {
  if (action === \"summarize\") return summarize();
  if (action === \"extract\") return extract();
  if (action === \"escalate\") return escalate();
  if (action === \"embed\") return embedCopy();
  if (action === \"list\") {
    return `<ol><li>Understand the requirements</li><li>Project components: HTML card, CSS, image</li><li>Design specs from the prototype</li><li>Submit the zip</li></ol>`;
  }
  if (action === \"what\") {
    return `This is EventRelay Hybrid Workspace: Monaco editor, Split.js layout, sandboxed iframe preview, and an fx terminal hook with a local fallback. Same interaction pattern as Cursor / Udacity AI Learning Assistant.`;
  }
  if (action === \"why\") {
    return `Custom design tools keep the lesson, the code, and the AI in one surface so you do not context-switch out of the project.`;
  }
  if (action === \"related\") {
    return `Related: HTML structure, CSS card layout, image accessibility, zip submission checklist.`;
  }
  const q = (text || \"\").toLowerCase();
  if (q.includes(\"ticket\") || q.includes(\"help\")) return escalate();
  if (q.includes(\"summar\")) return summarize();
  return `I can summarize the lesson, extract the current selection, embed this split view, or escalate to a human. You asked: <i>${escapeHtml(text || \"\")}</i>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>\"']/g, (c) => ({
    \"&\": \"&amp;\", \"<\": \"&lt;\", \">\": \"&gt;\", '\"': \"&quot;\", \"'\": \"&#39;\",
  }[c]));
}

function runAction(action, text) {
  document.querySelectorAll(\"#actions button\").forEach((b) => {
    b.classList.toggle(\"active\", b.dataset.action === action);
  });
  if (text) addMsg(\"user\", escapeHtml(text));
  else addMsg(\"user\", escapeHtml(fxPrompt(action, text)));
  addMsg(\"bot\", answer(action, text));
  state.term?.writeln(`fx> ${action}${text ? \" \" + text : \"\"}`);
}

function mountFiles() {
  Object.keys(FILES).forEach((name) => {
    const btn = document.createElement(\"button\");
    btn.textContent = name;
    btn.className = name === state.file ? \"active\" : \"\";
    btn.onclick = () => openFile(name);
    filesEl.appendChild(btn);
  });
}

function openFile(name) {
  state.file = name;
  filesEl.querySelectorAll(\"button\").forEach((b) => {
    b.classList.toggle(\"active\", b.textContent === name);
  });
  const model = state.models[name];
  if (model && state.editor) state.editor.setModel(model);
}

function mountPrompts() {
  const box = document.getElementById(\"prompts\");
  SUGGESTIONS.forEach((s) => {
    const b = document.createElement(\"button\");
    b.className = \"chip\";
    b.textContent = s.label;
    b.onclick = () => runAction(s.id, s.label);
    box.appendChild(b);
  });
}

document.getElementById(\"actions\").addEventListener(\"click\", (e) => {
  const btn = e.target.closest(\"button\");
  if (btn?.dataset.action) runAction(btn.dataset.action);
});

document.getElementById(\"composer\").addEventListener(\"submit\", (e) => {
  e.preventDefault();
  const text = ask.value.trim();
  if (!text) return;
  ask.value = \"\";
  runAction(\"ask\", text);
});

Split([\"#workspace\", \"#assistant\"], {
  sizes: [64, 36],
  minSize: [320, 260],
  gutterSize: 8,
});
Split([\"#main\", \"#termwrap\"], {
  direction: \"vertical\",
  sizes: [74, 26],
  minSize: [240, 120],
  gutterSize: 8,
});

require.config({ paths: { vs: \"https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs\" } });
require([\"vs/editor/editor.main\"], () => {
  Object.entries(FILES).forEach(([name, file]) => {
    state.models[name] = monaco.editor.createModel(file.value, file.language);
  });
  state.editor = monaco.editor.create(document.getElementById(\"editor\"), {
    model: state.models[state.file],
    theme: \"vs-dark\",
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 13,
  });
  state.editor.onDidChangeModelContent(() => {
    const model = state.editor.getModel();
    const name = Object.keys(state.models).find((k) => state.models[k] === model);
    if (name) FILES[name].value = model.getValue();
    renderPreview();
  });
  renderPreview();
});

state.term = new Terminal({
  convertEol: true,
  fontSize: 12,
  theme: { background: \"#0b1220\", foreground: \"#e2e8f0\" },
});
state.term.open(document.getElementById(\"terminal\"));

attachFx(state.term, {
  AI_GATEWAY_API_KEY: window.AI_GATEWAY_API_KEY || \"\",
}).then((fx) => {
  state.fx = fx;
  const live = fx.mode === \"fx\";
  document.getElementById(\"fxdot\").className = `status-dot ${live ? \"live\" : \"off\"}`;
  document.getElementById(\"fxlabel\").textContent = live ? \"libfx attached\" : \"local fallback\";
});

mountFiles();
mountPrompts();
addMsg(
  \"bot\",
  \"Hi — split-screen workspace is ready. Edit on the left, preview below the editor, ask here. Embed / Summarize / Extract / Escalate stay in this layout so you do not break focus.\",
);
