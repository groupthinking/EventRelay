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
declare global {
    interface Window {
        ai?: {
            languageModel?: {
                capabilities(): Promise<{
                    available: 'no' | 'after-download' | 'readily';
                }>;
                create(options?: {
                    systemPrompt?: string;
                    temperature?: number;
                    topK?: number;
                }): Promise<LanguageModelSession>;
            };
            summarizer?: {
                capabilities(): Promise<{
                    available: 'no' | 'after-download' | 'readily';
                }>;
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
export declare function checkCapabilities(): Promise<BuiltInAICapabilities>;
/**
 * Summarize transcript text using the on-device Summarizer API.
 * Falls back to the Prompt API if Summarizer is unavailable.
 */
export declare function summarizeTranscript(transcript: string): Promise<string | null>;
/**
 * Extract events/actions from transcript using the on-device Prompt API.
 */
export declare function extractEventsLocal(transcript: string): Promise<string | null>;
export {};
