'use client';

import { useEffect, useState } from 'react';

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Reveal newly arrived list items a few at a time so rows fill in place
 * instead of the whole list appearing at once. Shrinking targets (new run,
 * other video) snap immediately; reduced-motion users always see the target.
 */
export function useProgressiveCount(target: number, { stepMs = 45, batch = 1 }: { stepMs?: number; batch?: number } = {}): number {
  const [shown, setShown] = useState(0);
  const visible = Math.min(shown, target);

  useEffect(() => {
    if (shown > target) {
      setShown(target);
      return;
    }
    if (shown === target) return;
    if (prefersReducedMotion()) {
      setShown(target);
      return;
    }
    const timer = window.setTimeout(() => setShown((value) => Math.min(target, value + batch)), stepMs);
    return () => window.clearTimeout(timer);
  }, [shown, target, stepMs, batch]);

  return visible;
}
