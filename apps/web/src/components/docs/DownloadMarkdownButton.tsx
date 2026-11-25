'use client';

import { downloadMarkdownFile } from '@/lib/download-file';

type DownloadMarkdownButtonProps = {
  filename: string;
  content: string;
  label?: string;
  className?: string;
};

/** Download documentation or checklists as Markdown without inline data: URIs. */
export default function DownloadMarkdownButton({
  filename,
  content,
  label = 'Download .md',
  className,
}: DownloadMarkdownButtonProps) {
  return (
    <button
      type="button"
      onClick={() => downloadMarkdownFile(filename, content)}
      className={className}
      title="Download Markdown for Claude, Cursor, or ChatGPT"
    >
      <span>{label}</span>
      <span aria-hidden="true">↓</span>
    </button>
  );
}
