import { NextResponse } from 'next/server';

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

export async function GET() {
  try {
    // Use the real backend health endpoint
    const response = await fetch(`${BACKEND_URL}/api/v1/health`, {
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      throw new Error(`Backend health check failed: ${response.status}`);
    }

    const healthData = await response.json();

    return NextResponse.json({
      status: 'operational',
      timestamp: new Date().toISOString(),
      metrics: {
        activeWorkflows: healthData.active_connections || 0,
        totalProcessed: healthData.total_requests || 0,
        errorRate: 0,
      },
    });
  } catch (error) {
    console.error('Dashboard stats error:', error);
    // Return honest fallback — backend is not reachable
    return NextResponse.json({
      status: 'degraded',
      timestamp: new Date().toISOString(),
      metrics: {
        activeWorkflows: 0,
        totalProcessed: 0,
        errorRate: 0,
      },
    });
  }
}