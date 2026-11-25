/**
 * Trigger a client-side Markdown file download using an isolated Object URL.
 */
export function downloadMarkdownFile(filename: string, content: string): void {
  if (typeof document === 'undefined' || typeof URL === 'undefined') return;
  const safeName = filename.replace(/[^a-zA-Z0-9._-]/g, '') || 'uvai-export.md';
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const objectUrl = URL.createObjectURL(blob);
  try {
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = safeName.endsWith('.md') ? safeName : `${safeName}.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
  }
}
