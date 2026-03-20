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
export declare function useBuiltInAI(): {
    available: BuiltInAICapabilities;
    summarize: any;
    extractEvents: any;
};
