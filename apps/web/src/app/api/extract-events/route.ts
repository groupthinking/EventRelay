import { NextResponse } from 'next/server';
import { extractEvents } from '@/lib/event-extraction-service';

export async function POST(request: Request) {
  try {
    const { transcript, videoTitle, videoUrl } = await request.json();

    // Accept either transcript text OR videoUrl for direct Gemini analysis
    if ((!transcript || typeof transcript !== 'string') && !videoUrl) {
      return NextResponse.json(
        { error: 'transcript (string) or videoUrl is required' },
        { status: 400 }
      );
    }

    const result = await extractEvents({ transcript, videoTitle, videoUrl });

    if (!result.success) {
      return NextResponse.json({
        success: false,
        error: result.error,
        data: result.data,
      });
    }

    return NextResponse.json({ success: true, provider: result.provider, data: result.data });
  } catch (error) {
    console.error('Event extraction error:', error);
    const message = error instanceof Error ? error.message : String(error);

    return NextResponse.json({
      success: false,
      error: message,
      data: { events: [], actions: [], summary: '', topics: [] },
    });
  }
}
