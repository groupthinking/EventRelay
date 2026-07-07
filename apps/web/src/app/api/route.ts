import { NextResponse } from 'next/server';
import { formatApiError } from '@/lib/error-handling';

/**
 * GET /api
 * Health check and API information endpoint
 * 
 * This endpoint provides basic API information and should always return
 * a valid response. No external dependencies or error-prone operations.
 */
export async function GET() {
  try {
    return NextResponse.json({
      name: 'EventRelay API',
      version: '2.0.0',
      status: 'operational',
      documentation: '/docs/api',
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'production',
      endpoints: {
        pipeline: 'POST /api/pipeline - Full end-to-end video pipeline',
        pipeline_stream: 'POST /api/pipeline/stream - Real-time SSE streaming',
        transcribe: 'POST /api/transcribe - Extract video transcripts',
        video: 'POST /api/video - Video analysis only',
        health: 'GET /api - This endpoint',
      },
    });
  } catch (error) {
    console.error('Health check error:', error);
    const formatted = formatApiError(error);
    
    // Always return 200 OK for health checks, even if there are internal errors
    // but indicate degraded status
    return NextResponse.json(
      {
        name: 'EventRelay API',
        version: '2.0.0',
        status: 'degraded',
        documentation: '/docs/api',
        warning: 'Health check encountered an error',
        error: formatted.message,
      },
      { status: 200 } // Return 200 to indicate the endpoint itself is responding
    );
  }
}

export async function HEAD() {
  return new NextResponse(null, { status: 200 });
}
