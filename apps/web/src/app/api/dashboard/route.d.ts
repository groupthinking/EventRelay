import { NextResponse } from 'next/server';
export declare function GET(): Promise<NextResponse<{
    status: string;
    timestamp: string;
    metrics: {
        activeWorkflows: any;
        totalProcessed: any;
        errorRate: number;
    };
}>>;
