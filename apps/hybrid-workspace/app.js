import { attachFx, fxPrompt } from "./fx-adapter.js";
import { escapeHtml, injectVirtualAssets, shouldEscalate, summarizeFrom } from "./logic.js";

const FILES = {
  "index.html": {
    language: "html",
    value: "<!DOCTYPE html>\n<html>\n<head>\n  <link rel=\"stylesheet\" href=\"styles.css\" />\n  <title>Animal Trading Cards</title>\n</head>\n<body>\n  <article class=\"card\">\n    <h1>Clownfish</h1>\n    <p class=\"fact\">A layer of mucus on the clownfish skin makes it immune to the host anemone sting.</p>\n    <p class=\"sci\">Scientific Name: Amphiprioninae</p>\n  </article>\n  <script src=\"app.js\"></script>\n</body>\n</html>",
  },
  "styles.css": {
    language: "css",
    value: "body { font-family: Georgia, serif; background: #f3f7fb; }\n.card { max-width: 320px; margin: 24px auto; background: #fff; padding: 16px; border-radius: 12px; }",
  },
  "app.js": {
    language: "javascript",
    value: "document.querySelector('.card')?.addEventListener('click', () => console.log('card'));",
  },
  "lesson.md": {
    language: "markdown",
    value: "# Project Overview: Animal Trading Cards\n\nRecreate a webpage from a design prototype using HTML and CSS.",
  },
};

const SUGGESTIONS = [
  { id: "summarize", label: "Summarize the video" },
  { id: "related", label: "Recommend related content" },
  { id: "why", label: "Why build custom design tools?" },
  { id: "what", label: "What is this workspace?" },
  { id: "list", label: "List the project key components" },
];

const state = { file: "index.html", models: {}, editor: null, term: null, tickets: 2023732 };
const thread = document.getElementById("thread");
const filesEl = document.getElementById("files");
const preview = document.getElementById("preview");
const ask = document.getElementById("ask");

function addMsg(role, html) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.innerHTML = `<span class=\"meta\">${role === "bot" ? "Workspace AI" : "You"}</span>${html}`;
  thread.appendChild(el);
  thread.scrollTop = thread.scrollHeight;
}

function renderPreview() {
  preview.srcdoc = injectVirtualAssets(FILES["index.html"].value, {
    "styles.css": FILES["styles.css"].value,
    "app.js": FILES["app.js"].value,
  });
}

function escalate() {
  const id = `#${state.tickets++}`;
  return `Local support reference <span class=\"ticket\">${id}</span> saved in this session only. No remote ticket queue is wired yet.`;
}

function answer(action, text) {
  if (shouldEscalate(text, action)) return escalate();
  if (action === "summarize") return summarizeFrom(FILES).html;
  if (action === "extract") {
    const sel = state.editor?.getModel()?.getValueInRange(state.editor.getSelection()) || "";
    const clip = sel.trim() || FILES[state.file].value.slice(0, 280);
    return `Extracted from <b>${escapeHtml(state.file)}</b>:<blockquote>${escapeHtml(clip)}</blockquote>`;
  }
  if (action === "embed") return `Split screen stays locked: workspace left, assistant right.`;
  if (action === "list") return `<ol><li>Requirements</li><li>HTML card, CSS, image</li><li>Submit zip</li></ol>`;
  if (action === "what") return `This is the UVAI hybrid workspace pane: Monaco, Split.js, sandboxed iframe, local activity log. EventRelay is internal-only.`;
  if (action === "why") return `Keep lesson, code, and AI in one surface.`;
  if (action === "related") return `Related: HTML structure, CSS card layout, zip checklist.`;
  if ((text || "").toLowerCase().includes("summar")) return summarizeFrom(FILES).html;
  return `I can summarize, extract, embed, or create a local support reference. You asked: <i>${escapeHtml(text || "")}</i>`;
}

function runAction(action, text) {
  document.querySelectorAll("#actions button").forEach((b) => {
    b.classList.toggle("active", b.dataset.action === action);
  });
  addMsg("user", escapeHtml(text || fxPrompt(action, text)));
  addMsg("bot", answer(action, text));
  state.term?.writeln(`log> ${action}${text ? " " + text : ""}`);
}

function mountFiles() {
  Object.keys(FILES).forEach((name) => {
    const btn = document.createElement("button");
    btn.textContent = name;
    btn.className = name === state.file ? "active" : "";
    btn.onclick = () => {
      state.file = name;
      filesEl.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b.textContent === name));
      if (state.models[name] && state.editor) state.editor.setModel(state.models[name]);
    };
    filesEl.appendChild(btn);
  });
}

function mountPrompts() {
  SUGGESTIONS.forEach((s) => {
    const b = document.createElement("button");
    b.className = "chip";
    b.textContent = s.label;
    b.onclick = () => runAction(s.id, s.label);
    document.getElementById("prompts").appendChild(b);
  });
}

document.getElementById("actions").addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (btn?.dataset.action) runAction(btn.dataset.action);
});
document.getElementById("composer").addEventListener("submit", (e) => {
  e.preventDefault();
  const text = ask.value.trim();
  if (!text) return;
  ask.value = "";
  runAction("ask", text);
});

Split(["#workspace", "#assistant"], { sizes: [64, 36], minSize: [320, 260], gutterSize: 8 });
Split(["#main", "#termwrap"], { direction: "vertical", sizes: [74, 26], minSize: [240, 120], gutterSize: 8 });

require.config({ paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs" } });
require(["vs/editor/editor.main"], () => {
  Object.entries(FILES).forEach(([name, file]) => {
    state.models[name] = monaco.editor.createModel(file.value, file.language);
  });
  state.editor = monaco.editor.create(document.getElementById("editor"), {
    model: state.models[state.file],
    theme: "vs-dark",
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
  theme: { background: "#0b1220", foreground: "#e2e8f0" },
});
state.term.open(document.getElementById("terminal"));
attachFx(state.term, { onCommand: (action, text) => runAction(action, text) });
mountFiles();
mountPrompts();
addMsg("bot", "UVAI split workspace is ready. Embed / Summarize / Extract / Escalate stay in this layout.");
