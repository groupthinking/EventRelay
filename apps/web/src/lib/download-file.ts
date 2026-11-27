/**
 * Trigger a client-side text file download using an isolated Blob Object URL.
 */
export function downloadTextFile(
  filename: string,
  content: string,
  mimeType = 'text/plain;charset=utf-8',
): void {
  if (typeof document === 'undefined' || typeof URL === 'undefined') return;
  const safeName = filename.replace(/[^a-zA-Z0-9._-]/g, '') || 'uvai-export.txt';
  const blob = new Blob([content], { type: mimeType });
  const objectUrl = URL.createObjectURL(blob);
  try {
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = safeName;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
  }
}

/**
 * Trigger a client-side Markdown file download using an isolated Object URL.
 */
export function downloadMarkdownFile(filename: string, content: string): void {
  const safeName = filename.replace(/[^a-zA-Z0-9._-]/g, '') || 'uvai-export.md';
  const finalName = safeName.endsWith('.md') ? safeName : `${safeName}.md`;
  downloadTextFile(finalName, content, 'text/markdown;charset=utf-8');
}
