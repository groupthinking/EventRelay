export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function attributeValue(tag, wanted) {
  // Consume complete quoted values so href/src-looking text inside another
  // attribute cannot become an active asset reference. First duplicate wins.
  const attributes = tag.replace(/^<\w+\b/, '');
  const pattern = /\s+([^\s"'<>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
  for (const match of attributes.matchAll(pattern)) {
    if (match[1].toLowerCase() === wanted) return match[2] ?? match[3] ?? match[4] ?? '';
  }
  return null;
}

export function injectVirtualAssets(html, assets) {
  let out = String(html);
  for (const [name, body] of Object.entries(assets)) {
    if (name.endsWith('.css')) {
      out = out.replace(/<link\b(?:[^>"']|"[^"]*"|'[^']*')*>/gi, tag =>
        attributeValue(tag, 'href') === name
          ? `<style>${String(body).replace(/<\/style/gi, '<\\/style')}</style>` : tag);
    } else if (name.endsWith('.js')) {
      out = out.replace(/(<script\b(?:[^>"']|"[^"]*"|'[^']*')*>)\s*<\/script>/gi, (whole, tag) =>
        attributeValue(tag, 'src') === name
          ? `<script>${String(body).replace(/<\/script/gi, '<\\/script')}</script>` : whole);
    }
  }
  return out;
}

export function shouldEscalate(text, action) {
  if (action === "escalate") return true;
  const q = String(text || "").toLowerCase();
  return /\b(escalate|file a ticket|human support|support ticket)\b/.test(q);
}

export function summarizeFrom(files) {
  const lesson = files["lesson.md"]?.value || "";
  const html = files["index.html"]?.value || "";
  const title = (html.match(/<title>([^<]+)<\/title>/i) || [, "Untitled"])[1];
  const headings = [...html.matchAll(/<h1[^>]*>([^<]+)<\/h1>/gi)].map((m) => m[1]);
  const excerpt = lesson.split("\n").slice(0, 8).join("\n");
  return {
    title,
    headings,
    excerpt,
    html: `Current lesson title in preview: <b>${escapeHtml(title)}</b>. Headings: ${escapeHtml(headings.join(", ") || "(none)")}.<pre>${escapeHtml(excerpt)}</pre>`,
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

