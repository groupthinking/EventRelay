import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    name: 'EventRelay API',
    version: '2.0.0',
    status: 'operational',
    documentation: '/api/docs',
  });
}