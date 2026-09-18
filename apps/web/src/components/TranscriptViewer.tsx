'use client';

import { useState, useId, useMemo } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { clsx } from 'clsx';
import { buildSearchConfig } from '@/lib/transcript-search';

interface TranscriptViewerProps {
  transcript: string;
  className?: string;
}

/**
 * Displays a searchable transcript with optional line expansion.
 *
 * @param transcript - Full transcript text split into separate lines for display.
 * @param className - Additional CSS classes for the outer container.
 */
export default function TranscriptViewer({ transcript, className }: TranscriptViewerProps) {
  const [expanded, setExpanded] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const searchId = useId();

  // Memoize splitting and filtering since transcript can be large and static
  const paragraphs = useMemo(() => {
    return transcript.split('\n').filter((p) => p.trim().length > 0);
  }, [transcript]);

  const displayParagraphs = expanded ? paragraphs : paragraphs.slice(0, 8);

  // Precompute the highlight regex and lowercased query once per query change
  // rather than per paragraph. See `@/lib/transcript-search` (issue #908).
  const searchConfig = useMemo(() => buildSearchConfig(searchQuery), [searchQuery]);

  const highlight = (text: string) => {
    if (!searchConfig) return text;
    const parts = text.split(searchConfig.regex);
    // ⚡ Bolt: Implementing safety check during map iteration when comparing split regex parts.
    return parts.map((part, i) => {
      const lowerPart = part ? part.toLowerCase() : '';
      return lowerPart === searchConfig.lower ? (
        <mark key={i} className="bg-primary-500/30 text-primary-300 rounded px-0.5">
          {part}
        </mark>
      ) : (
        part
      );
    });
  };

  return (
    <div className={clsx('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          Transcript
        </h3>
        <span className="text-xs text-white/30">{paragraphs.length} lines</span>
      </div>

      {/* Search */}
      <label htmlFor={searchId} className="sr-only">
        Search transcript
      </label>
      <input
        id={searchId}
        type="search"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        placeholder="Search transcript…"
        className="w-full px-3 py-2 text-sm rounded-lg bg-white/[0.03] border border-white/[0.08] text-white placeholder:text-white/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/40 focus:border-primary-500/30"
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
          type="button"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          className="inline-flex items-center gap-1 text-sm text-primary-400 hover:text-primary-300 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/40 rounded"
        >
          {expanded ? (
            <>
              <ChevronUp className="h-4 w-4" aria-hidden="true" /> Show less
            </>
          ) : (
            <>
              <ChevronDown className="h-4 w-4" aria-hidden="true" /> Show all {paragraphs.length} lines
            </>
          )}
        </button>
      )}
    </div>
  );
}
