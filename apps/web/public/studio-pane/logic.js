export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
export function injectVirtualAssets(html, assets) {
  let out = String(html);
  for (const [name, body] of Object.entries(assets)) {
    if (name.endsWith(".css")) {
      out = out.replace(new RegExp(`<link\\b[^>]*href=["']${name}["'][^>]*>`, "i"), `<style>${body}</style>`);
    } else if (name.endsWith(".js")) {
      out = out.replace(new RegExp(`<script\\b[^>]*src=["']${name}["'][^>]*>\\s*</script>`, "i"), `<script>${body}</script>`);
    }
  }
  return out;
}
export function shouldEscalate(text, action) {
  if (action === "escalate") return true;
  return /\\b(escalate|file a ticket|human support|support ticket)\\b/.test(String(text || "").toLowerCase());
}
export function summarizeFrom(files) {
  const lesson = files["lesson.md"]?.value || "";
  const html = files["index.html"]?.value || "";
  const title = (html.match(/<title>([^<]+)<\\/title>/i) || [, "Untitled"])[1];
  const headings = [...html.matchAll(/<h1[^>]*>([^<]+)<\\/h1>/gi)].map((m) => m[1]);
  return {
    title,
    headings,
    excerpt: lesson.split("\n").slice(0, 8).join("\n"),
    html: `Current lesson title in preview: <b>${escapeHtml(title)}</b>. Headings: ${escapeHtml(headings.join(", ") || "(none)")}.<pre>${escapeHtml(lesson.split("\n").slice(0, 8).join("\n"))}</pre>`,
  };
}
export function parseTermCommand(line) {
  const raw = String(line || "").trim();
  const [cmd, ...rest] = raw.split(/\s+/);
  const text = rest.join(" ");
  if (["summarize", "extract", "escalate", "embed"].includes(cmd)) return { action: cmd, text };
  if (cmd === "ask") return { action: "ask", text };
  return { action: "ask", text: raw };
}
