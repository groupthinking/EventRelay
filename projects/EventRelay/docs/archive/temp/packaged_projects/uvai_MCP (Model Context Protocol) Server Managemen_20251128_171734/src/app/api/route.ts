import { NextRequest, NextResponse } from 'next/server';

// Simple request type
interface ApiRequest {
  message?: string;
  action?: string;
}

// Health check endpoint
export async function GET() {
  return NextResponse.json({
    status: 'online',
    service: 'API Service',
    timestamp: new Date().toISOString(),
  });
}

// Main API handler
export async function POST(req: NextRequest) {
  try {
    const body: ApiRequest = await req.json();
    const { message, action } = body;

    // Process the request
    const result = {
      success: true,
      message: message || 'Request processed successfully',
      action: action || 'default',
      timestamp: new Date().toISOString(),
    };

    return NextResponse.json(result);
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json(
      { error: 'Internal Server Error', message: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
