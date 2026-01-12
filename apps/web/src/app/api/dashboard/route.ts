import { NextResponse } from 'next/server';

const PRESCIENT_TWIN_URL = process.env.PRESCIENT_TWIN_URL || 'http://localhost:8000';

export async function GET() {
  try {
    // Get stats from Prescient Twin
    const response = await fetch(`${PRESCIENT_TWIN_URL}/stats`);

    if (!response.ok) {
      throw new Error('Failed to fetch stats from Prescient Twin');
    }

    const stats = await response.json();

    // Transform to dashboard format
    return NextResponse.json({
      status: 'operational',
      timestamp: new Date().toISOString(),
      metrics: {
        activeWorkflows: stats.router?.agents_active?.length || 0,
        totalProcessed: Object.values(stats.router?.routing_counts || {}).reduce((a: number, b: any) => a + (b as number), 0),
        errorRate: 0.5,
        availableBrains: stats.router?.available_brains || [],
        lessonsLearned: stats.lessons || 0,
      }
    });
  } catch (error) {
    console.error('Dashboard stats error:', error);
    // Return fallback data if Prescient Twin is unavailable
    return NextResponse.json({
      status: 'degraded',
      timestamp: new Date().toISOString(),
      metrics: {
        activeWorkflows: 0,
        totalProcessed: 0,
        errorRate: 0,
        availableBrains: [],
        lessonsLearned: 0,
      }
    });
  }
}