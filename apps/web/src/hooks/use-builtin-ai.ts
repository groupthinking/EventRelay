'use client';

import { useEffect, useState } from 'react';
import {
  type BuiltInAICapabilities,
  checkCapabilities,
  summarizeTranscript,
  extractEventsLocal,
} from '@/lib/services/builtin-ai';

/**
 * React hook exposing Chrome Built-in AI capabilities.
 *
 * Usage:
 * ```tsx
 * const { available, summarize, extractEvents } = useBuiltInAI();
 * if (available.promptAPI) {
 *   const summary = await summarize(transcript);
 * }
 * ```
 */
export function useBuiltInAI() {
  const [available, setAvailable] = useState<BuiltInAICapabilities>({
    promptAPI: false,
    summarizerAPI: false,
  });

  useEffect(() => {
    checkCapabilities().then(setAvailable);
  }, []);

  return {
    available,
    summarize: summarizeTranscript,
    extractEvents: extractEventsLocal,
  };
}
