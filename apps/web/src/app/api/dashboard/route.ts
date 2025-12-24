import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    metrics: {
      activeWorkflows: 0,
      totalProcessed: 0,
      errorRate: 0,
    },
  });
}