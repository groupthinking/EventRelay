export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

export function injectVirtualAssets(html, assets) {
  // Native HTML parsing gives real attribute, duplicate, comment and end-tag
  // semantics. This substitutes virtual assets; it is not an HTML sanitizer.
  // Edited JavaScript executes only in the opaque-origin sandboxed preview.
  const original = String(html);
  const doc = new DOMParser().parseFromString(original, 'text/html');
  let changed = false;
  for (const [name, body] of Object.entries(assets)) {
    if (name.endsWith('.css')) {
      for (const link of doc.querySelectorAll('link[href]')) {
        if (link.getAttribute('href') !== name) continue;
        const style = doc.createElement('style');
        if (link.hasAttribute('media')) style.setAttribute('media', link.getAttribute('media'));
        style.textContent = String(body).replace(/<\/style/gi, '<\\/style');
        link.replaceWith(style);
        changed = true;
      }
    } else if (name.endsWith('.js')) {
      for (const script of doc.querySelectorAll('script[src]')) {
        if (script.getAttribute('src') !== name) continue;
        script.removeAttribute('src');
        script.textContent = String(body).replace(/<\/script/gi, '<\\/script');
        changed = true;
      }
    }
  }
  if (!changed) return original;
  return (doc.doctype ? '<!DOCTYPE html>\n' : '') + doc.documentElement.outerHTML;
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

