import { NextResponse } from 'next/server';
export declare function GET(): Promise<NextResponse<{
    name: string;
    version: string;
    status: string;
    documentation: string;
}>>;
