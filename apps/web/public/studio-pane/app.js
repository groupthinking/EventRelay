import { attachFx, fxPrompt } from "./fx-adapter.js";
import { escapeHtml, injectVirtualAssets, shouldEscalate, summarizeFrom } from "./logic.js";
const FILES = {
  "index.html": { language: "html", value: "<!DOCTYPE html><html><head><link rel=\"stylesheet\" href=\"styles.css\" /><title>Animal Trading Cards</title></head><body><article class=\"card\"><h1>Clownfish</h1><p class=\"fact\">Mucus on the skin blocks the anemone sting.</p></article><script src=\"app.js\"></script></body></html>" },
  "styles.css": { language: "css", value: "body{font-family:Georgia,serif;background:#f3f7fb}.card{max-width:320px;margin:24px auto;background:#fff;padding:16px;border-radius:12px}" },
  "app.js": { language: "javascript", value: "document.querySelector('.card')?.addEventListener('click',()=>console.log('card'))" },
  "lesson.md": { language: "markdown", value: "# Animal Trading Cards\nRecreate the card with HTML and CSS." },
};
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
  preview.srcdoc = injectVirtualAssets(FILES["index.html"].value, { "styles.css": FILES["styles.css"].value, "app.js": FILES["app.js"].value });
}
function escalate() { return `Local support reference <span class=\"ticket\">#${state.tickets++}</span> saved in this session only.`; }
function answer(action, text) {
  if (shouldEscalate(text, action)) return escalate();
  if (action === "summarize") return summarizeFrom(FILES).html;
  if (action === "extract") {
    const sel = state.editor?.getModel()?.getValueInRange(state.editor.getSelection()) || "";
    return `Extracted from <b>${escapeHtml(state.file)}</b>:<blockquote>${escapeHtml((sel.trim() || FILES[state.file].value).slice(0, 280))}</blockquote>`;
  }
  if (action === "embed") return "Split screen stays on /studio. Workspace left, assistant right.";
  if (action === "what") return "UVAI hybrid pane inside Studio. EventRelay is internal-only.";
  return `I can summarize, extract, embed, or create a local reference. You asked: <i>${escapeHtml(text || "")}</i>`;
}
function runAction(action, text) {
  document.querySelectorAll("#actions button").forEach((b) => b.classList.toggle("active", b.dataset.action === action));
  addMsg("user", escapeHtml(text || fxPrompt(action, text)));
  addMsg("bot", answer(action, text));
  state.term?.writeln(`log> ${action}${text ? " " + text : ""}`);
}
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
[["summarize", "Summarize the video"], ["what", "What is this workspace?"]].forEach(([id, label]) => {
  const b = document.createElement("button");
  b.className = "chip";
  b.textContent = label;
  b.onclick = () => runAction(id, label);
  document.getElementById("prompts").appendChild(b);
});
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
Split(["#workspace", "#assistant"], { sizes: [64, 36], minSize: [280, 240], gutterSize: 8 });
Split(["#main", "#termwrap"], { direction: "vertical", sizes: [74, 26], minSize: [200, 100], gutterSize: 8 });
require.config({ paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs" } });
require(["vs/editor/editor.main"], () => {
  Object.entries(FILES).forEach(([name, file]) => { state.models[name] = monaco.editor.createModel(file.value, file.language); });
  state.editor = monaco.editor.create(document.getElementById("editor"), { model: state.models[state.file], theme: "vs-dark", automaticLayout: true, minimap: { enabled: false }, fontSize: 13 });
  state.editor.onDidChangeModelContent(() => {
    const model = state.editor.getModel();
    const name = Object.keys(state.models).find((k) => state.models[k] === model);
    if (name) FILES[name].value = model.getValue();
    renderPreview();
  });
  renderPreview();
});
state.term = new Terminal({ convertEol: true, fontSize: 12, theme: { background: "#0b1220", foreground: "#e2e8f0" } });
state.term.open(document.getElementById("terminal"));
attachFx(state.term, { onCommand: (action, text) => runAction(action, text) });
addMsg("bot", "UVAI split workspace on /studio. Pack view stays the YouTube pipeline.");
