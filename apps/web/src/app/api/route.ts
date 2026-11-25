import { NextResponse } from 'next/server';

/** GET /api — service descriptor. The body is a literal and does not call out. */
export async function GET() {
  return NextResponse.json({
    name: 'UVAI API',
    version: '2.0.0',
    status: 'operational',
    documentation: '/docs/api',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'production',
    endpoints: {
      video_pack: 'POST /api/video/pack - Emit a hashed Video Pack from a YouTube URL',
      transcribe: 'POST /api/transcribe - Extract video transcripts',
      pipeline: 'Legacy /api/pipeline routes are retired',
      health: 'GET /api - This endpoint',
    },
  });
}

export async function HEAD() {
  return new NextResponse(null, { status: 200 });
}
