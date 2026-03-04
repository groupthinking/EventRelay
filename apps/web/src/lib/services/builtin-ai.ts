/**
 * Chrome Built-in AI — client-side fallback for video analysis.
 *
 * Uses the Chrome Prompt API (`LanguageModel.create()`) and
 * Summarizer API to perform on-device text processing when
 * server-side API keys are unavailable or the user is offline.
 *
 * Reference: Chrome Built-in AI Early Preview Program
 * @see https://developer.chrome.com/docs/ai/built-in
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

// Type declarations for Chrome Built-in AI APIs (not yet in lib.dom.d.ts)
declare global {
  interface Window {
    ai?: {
      languageModel?: {
        capabilities(): Promise<{ available: 'no' | 'after-download' | 'readily' }>;
        create(options?: {
          systemPrompt?: string;
          temperature?: number;
          topK?: number;
        }): Promise<LanguageModelSession>;
      };
      summarizer?: {
        capabilities(): Promise<{ available: 'no' | 'after-download' | 'readily' }>;
        create(options?: {
          type?: 'tl;dr' | 'key-points' | 'teaser' | 'headline';
          format?: 'plain-text' | 'markdown';
          length?: 'short' | 'medium' | 'long';
        }): Promise<SummarizerSession>;
      };
    };
  }
}

interface LanguageModelSession {
  prompt(input: string): Promise<string>;
  promptStreaming(input: string): ReadableStream<string>;
  destroy(): void;
}

interface SummarizerSession {
  summarize(input: string): Promise<string>;
  destroy(): void;
}

export interface BuiltInAICapabilities {
  promptAPI: boolean;
  summarizerAPI: boolean;
}

/**
 * Check which Chrome Built-in AI APIs are available.
 */
export async function checkCapabilities(): Promise<BuiltInAICapabilities> {
  const result: BuiltInAICapabilities = { promptAPI: false, summarizerAPI: false };

  if (typeof window === 'undefined' || !window.ai) return result;

  try {
    const lm = await window.ai.languageModel?.capabilities();
    result.promptAPI = lm?.available === 'readily';
  } catch { /* not available */ }

  try {
    const sm = await window.ai.summarizer?.capabilities();
    result.summarizerAPI = sm?.available === 'readily';
  } catch { /* not available */ }

  return result;
}

/**
 * Summarize transcript text using the on-device Summarizer API.
 * Falls back to the Prompt API if Summarizer is unavailable.
 */
export async function summarizeTranscript(
  transcript: string,
): Promise<string | null> {
  if (typeof window === 'undefined' || !window.ai) return null;

  // Try Summarizer API first
  if (window.ai.summarizer) {
    try {
      const caps = await window.ai.summarizer.capabilities();
      if (caps.available === 'readily') {
        const session = await window.ai.summarizer.create({
          type: 'key-points',
          format: 'markdown',
          length: 'medium',
        });
        try {
          return await session.summarize(transcript);
        } finally {
          session.destroy();
        }
      }
    } catch (e) {
      console.warn('[BuiltInAI] Summarizer failed:', e);
    }
  }

  // Fall back to Prompt API
  return promptExtract(
    transcript,
    'Summarize the following video transcript into key points in markdown format.',
  );
}

/**
 * Extract events/actions from transcript using the on-device Prompt API.
 */
export async function extractEventsLocal(
  transcript: string,
): Promise<string | null> {
  return promptExtract(
    transcript,
    `Analyze this video transcript and extract:
1. Key events (what happened, when)
2. Action items (tasks, next steps)
3. Topics discussed
4. Overall sentiment

Return as JSON with keys: events, actions, topics, sentiment.`,
  );
}

/**
 * Low-level Prompt API call with automatic session lifecycle.
 */
async function promptExtract(
  text: string,
  systemPrompt: string,
): Promise<string | null> {
  if (typeof window === 'undefined' || !window.ai?.languageModel) return null;

  try {
    const caps = await window.ai.languageModel.capabilities();
    if (caps.available !== 'readily') return null;

    const session = await window.ai.languageModel.create({
      systemPrompt,
      temperature: 0.3,
      topK: 3,
    });

    try {
      return await session.prompt(text);
    } finally {
      session.destroy();
    }
  } catch (e) {
    console.warn('[BuiltInAI] Prompt API failed:', e);
    return null;
  }
}
