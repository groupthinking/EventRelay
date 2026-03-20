/**
 * Agentic Video Intelligence Engine — Gemini + Google Search grounding.
 *
 * Uses the googleSearch tool as the PRIMARY mechanism to retrieve real-time
 * transcripts, descriptions, chapters, and metadata from YouTube videos.
 * Based on the UVAI PK=998 implementation pattern.
 *
 * Uses gemini-3-pro-preview which supports responseSchema + googleSearch
 * together (older models like gemini-2.5-flash do not).
 */
export interface VideoAnalysisResult {
    title: string;
    summary: string;
    transcript: {
        start: number;
        duration: number;
        text: string;
    }[];
    events: {
        timestamp: number;
        label: string;
        description: string;
        codeMapping: string;
        cloudService: string;
    }[];
    actions: {
        title: string;
        description: string;
        category: string;
        estimatedMinutes: number | null;
    }[];
    topics: string[];
    architectureCode: string;
    ingestScript: string;
    e22Snippets: {
        title: string;
        description: string;
        code: string;
        language: string;
    }[];
}
/**
 * Executes a deep agentic analysis of a YouTube video using Gemini + Google Search.
 * Uses gemini-3-pro-preview with responseSchema + googleSearch (PK=998 pattern).
 * This is a single API call that handles both transcription AND extraction.
 */
export declare function analyzeVideoWithGemini(videoUrl: string): Promise<VideoAnalysisResult>;
