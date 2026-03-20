import { NextResponse } from 'next/server';
/**
 * POST /api/transcribe
 *
 * Multi-strategy transcript extraction:
 *   1. YouTube captions via backend (fast + free)
 *   2. OpenAI Responses API with web_search (finds transcripts online)
 *   3. Gemini fallback (if OpenAI unavailable)
 *   4. Direct audio STT via OpenAI Whisper
 */
export declare function POST(request: Request): Promise<NextResponse<{
    error: string;
}> | NextResponse<{
    success: boolean;
    transcript: any;
    segments: any;
    source: string;
    wordCount: any;
}> | NextResponse<{
    success: boolean;
    transcript: string;
    source: string;
    wordCount: number;
}> | NextResponse<{
    success: boolean;
    transcript: any;
    source: string;
    wordCount: any;
    metadata: {
        title: any;
        channel: any;
        chapters: any;
    } | undefined;
}>>;
