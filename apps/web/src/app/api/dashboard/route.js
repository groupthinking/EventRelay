"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.GET = GET;
const server_1 = require("next/server");
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
async function GET() {
    try {
        // Use the real backend health endpoint
        const response = await fetch(`${BACKEND_URL}/api/v1/health`, {
            signal: AbortSignal.timeout(5000),
        });
        if (!response.ok) {
            throw new Error(`Backend health check failed: ${response.status}`);
        }
        const healthData = await response.json();
        return server_1.NextResponse.json({
            status: 'operational',
            timestamp: new Date().toISOString(),
            metrics: {
                activeWorkflows: healthData.active_connections || 0,
                totalProcessed: healthData.total_requests || 0,
                errorRate: 0,
            },
        });
    }
    catch (error) {
        console.error('Dashboard stats error:', error);
        // Return honest fallback — backend is not reachable
        return server_1.NextResponse.json({
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
//# sourceMappingURL=route.js.map