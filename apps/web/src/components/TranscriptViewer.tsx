'use client';

import { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { useToast } from '@/components/ui/Toast';

interface TranscriptViewerProps {
  transcript: string;
  className?: string;
}

export default function TranscriptViewer({ transcript, className }: TranscriptViewerProps) {
  const [expanded, setExpanded] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);
  const { addToast } = useToast();

  const paragraphs = transcript.split('\n').filter((p) => p.trim().length > 0);
  const displayParagraphs = expanded ? paragraphs : paragraphs.slice(0, 8);

  // Word count derived from full transcript
  const wordCount = transcript.split(/\s+/).filter(Boolean).length;

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(transcript);
      setCopied(true);
      addToast('Transcript copied to clipboard', 'success');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      addToast('Failed to copy — please select and copy manually', 'error');
    }
  }, [transcript, addToast]);

  const highlight = (text: string) => {
    if (!searchQuery) return text;
    const regex = new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);
    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-primary-500/30 text-primary-300 rounded px-0.5">
          {part}
        </mark>
      ) : (
        part
      ),
    );
  };

  return (
    <div className={clsx('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          Transcript
        </h3>
        <div className="flex items-center gap-3">
          {/* Word + line count */}
          <span className="text-xs text-white/30">
            {paragraphs.length} lines · {wordCount.toLocaleString()} words
          </span>
          {/* Copy button */}
          <button
            onClick={handleCopy}
            title="Copy full transcript"
            className={clsx(
              'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border transition-all',
              copied
                ? 'bg-green-500/15 border-green-500/30 text-green-400'
                : 'bg-white/[0.03] border-white/[0.08] text-white/40 hover:text-white/70 hover:border-white/20'
            )}
          >
            {copied ? (
              <>✓ Copied</>
            ) : (
              <>
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </>
            )}
          </button>
        </div>
      </div>

      {/* Search */}
      <input
        type="text"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        placeholder="Search transcript..."
        className="w-full px-3 py-2 text-sm rounded-lg bg-white/[0.03] border border-white/[0.08] text-white placeholder:text-white/25 focus:outline-none focus:border-primary-500/30"
      />

      {/* Content */}
      <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
        {displayParagraphs.map((para, i) => (
          <p
            key={i}
            className="text-sm text-white/70 leading-relaxed p-2 rounded-lg hover:bg-white/[0.03] transition-colors"
          >
            <span className="text-white/25 text-xs mr-2 select-none">{i + 1}</span>
            {highlight(para)}
          </p>
        ))}
      </div>

      {paragraphs.length > 8 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-sm text-primary-400 hover:text-primary-300 transition-colors"
        >
          {expanded ? '▲ Show less' : `▼ Show all ${paragraphs.length} lines`}
        </button>
      )}
    </div>
  );
}
