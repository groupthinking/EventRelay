'use client';

import { useState, useCallback, useId } from 'react';
import { Check } from 'lucide-react';
import { submitFeedback } from '@/lib/feedback';

interface FeedbackWidgetProps {
  videoId: string;
  tab: string;
  compact?: boolean;
}

/**
 * Inline feedback widget with star rating + optional comment.
 * Appears at the bottom of each dashboard tab to collect user signals
 * that feed into the correction loop.
 */
export default function FeedbackWidget({ videoId, tab, compact = false }: FeedbackWidgetProps) {
  const [rating, setRating] = useState<number>(0);
  const [hoveredStar, setHoveredStar] = useState<number>(0);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const commentId = useId();

  const handleSubmit = useCallback(async () => {
    if (rating === 0) return;
    setSubmitting(true);
    try {
      await submitFeedback({
        videoId,
        tab,
        rating,
        comment: comment.trim() || undefined,
      });
      setSubmitted(true);
    } catch (err) {
      console.error('Feedback submission failed:', err);
    } finally {
      setSubmitting(false);
    }
  }, [videoId, tab, rating, comment]);

  if (submitted) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex items-center gap-2 px-4 py-3 mt-6 text-xs"
        style={{
          background: 'rgba(34, 197, 94, 0.08)',
          border: '1px solid rgba(34, 197, 94, 0.2)',
          color: '#22c55e',
        }}
      >
        <Check className="h-3.5 w-3.5" aria-hidden="true" />
        <span className="font-heading tracking-wider uppercase">Feedback recorded</span>
      </div>
    );
  }

  return (
    <div
      className="mt-6 px-4 py-3"
      style={{
        background: 'rgba(37, 37, 44, 0.4)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
      }}
    >
      <div className="flex items-center justify-between">
        <span
          className="text-[10px] font-heading font-bold uppercase tracking-[0.2em]"
          style={{ color: 'rgba(248, 245, 253, 0.35)' }}
        >
          Rate this {tab}
        </span>

        {/* Star rating */}
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              type="button"
              onClick={() => {
                setRating(star);
                if (!expanded) setExpanded(true);
              }}
              onMouseEnter={() => setHoveredStar(star)}
              onMouseLeave={() => setHoveredStar(0)}
              aria-pressed={star <= rating}
              className="text-lg transition-transform duration-150 motion-reduce:transition-none hover:scale-110 active:scale-95 motion-reduce:hover:scale-100 motion-reduce:active:scale-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40 rounded"
              style={{
                color:
                  star <= (hoveredStar || rating)
                    ? '#6af2de'
                    : 'rgba(255, 255, 255, 0.15)',
                filter:
                  star <= (hoveredStar || rating)
                    ? 'drop-shadow(0 0 4px rgba(106, 242, 222, 0.4))'
                    : 'none',
              }}
              aria-label={`Rate ${star} out of 5`}
            >
              ★
            </button>
          ))}
        </div>
      </div>

      {/* Expandable comment area */}
      {expanded && (
        <div className="mt-3 space-y-3 animate-fade-in-up motion-reduce:animate-none">
          <label htmlFor={commentId} className="sr-only">
            What could be improved? (optional)
          </label>
          <textarea
            id={commentId}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What could be improved? (optional)"
            rows={2}
            className="w-full px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40 resize-none"
            style={{
              background: 'rgba(25, 25, 31, 0.8)',
              border: '1px solid rgba(106, 242, 222, 0.15)',
              color: '#f8f5fd',
            }}
          />
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting || rating === 0}
              aria-busy={submitting || undefined}
              className="px-4 py-1.5 font-heading font-bold text-[10px] tracking-wider uppercase transition-[transform,opacity] motion-reduce:transition-none focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40 disabled:opacity-30 active:scale-95 motion-reduce:active:scale-100"
              style={{
                background: 'rgba(16, 183, 165, 0.9)',
                color: '#002b26',
              }}
            >
              {submitting ? 'Sending…' : 'Submit'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
