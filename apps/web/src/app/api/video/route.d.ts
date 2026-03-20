import { NextResponse } from 'next/server';
/**
 * POST /api/video
 *
 * Tries the full backend pipeline first (FastAPI transcript-action workflow).
 * If the backend is unreachable — common on Vercel where no Python server
 * runs — falls through to a frontend-only path that chains /api/transcribe
 * and /api/extract-events serverless functions directly.
 */
export declare function POST(request: Request): Promise<NextResponse<{
    error: string;
}> | NextResponse<{
    id: string;
    status: string;
    processing_time_ms: number;
    result: {
        success: any;
        insights: {
            summary: string;
            actions: any;
            topics: any;
            sentiment: any;
            strategy: any;
            project_scaffold: any;
        };
        transcript_segments: any;
        agents_used: any;
        errors: any;
        raw_response: any;
    };
}> | NextResponse<{
    id: string;
    status: string;
    processing_time_ms: number;
    result: {
        success: boolean;
        insights: {
            summary: any;
            actions: any;
            topics: any;
            sentiment: string;
        };
        transcript_segments: any;
        transcript_source: string;
        agents_used: string[];
        errors: never[];
        raw_response: {
            title: any;
            transcript: any;
            events: any;
            actions: any;
            architectureCode: any;
            ingestScript: any;
        };
    };
}> | NextResponse<{
    id: string;
    status: string;
    processing_time_ms: number;
    result: {
        success: boolean;
        insights: {
            summary: string;
            actions: string[];
            topics: string[];
            sentiment: string;
        };
        transcript_segments: number;
        transcript_source: string;
        agents_used: string[];
        errors: string[];
        raw_response: {
            transcript: {
                text: string;
            };
            extraction: {
                events?: Array<{
                    type: string;
                    title: string;
                    description?: string;
                    timestamp?: string;
                    priority?: string;
                }>;
                actions?: Array<{
                    title: string;
                }>;
                summary?: string;
                topics?: string[];
            };
        };
    };
}>>;
export declare function GET(): Promise<NextResponse<{
    name: string;
    version: string;
    backend_status: any;
    backend_components: any;
    endpoints: {
        analyze: string;
        health: string;
    };
}> | NextResponse<{
    name: string;
    version: string;
    backend_status: string;
    frontend_pipeline: string;
    endpoints: {
        analyze: string;
        pipeline: string;
    };
}>>;
