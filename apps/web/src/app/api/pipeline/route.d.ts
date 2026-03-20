import { NextResponse } from 'next/server';
/**
 * POST /api/pipeline
 *
 * End-to-end pipeline: YouTube URL → Video Analysis → Code Generation → Deployment → Live URL
 *
 * This is the FULL pipeline that the user's notes describe (PK=999, PK=1021):
 *   Ingest → Translate → Transport → Execute
 *
 * Strategies:
 *   1. Backend pipeline (FastAPI /api/v1/video-to-software) — full pipeline with agents
 *   2. Gemini analysis + frontend deployment — when no backend is available
 */
export declare function POST(request: Request): Promise<NextResponse<{
    error: string;
}> | NextResponse<{
    id: string;
    status: any;
    pipeline: string;
    processing_time: any;
    result: {
        live_url: any;
        github_repo: any;
        build_status: any;
        video_analysis: any;
        code_generation: any;
        deployment: any;
        features_implemented: any;
    };
}> | NextResponse<{
    id: string;
    status: string;
    pipeline: string;
    processing_time: string;
    result: {
        live_url: null;
        github_repo: null;
        build_status: string;
        video_analysis: {
            title: any;
            summary: any;
            events: any;
            actions: any;
            topics: any;
            architectureCode: any;
        };
        code_generation: null;
        deployment: null;
        message: string;
    };
}>>;
export declare function GET(): Promise<NextResponse<{
    name: string;
    version: string;
    description: string;
    pipeline_stages: string[];
    backend_available: boolean;
    gemini_available: any;
    endpoints: {
        pipeline: string;
        video: string;
    };
}>>;
