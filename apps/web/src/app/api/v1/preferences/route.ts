import { NextRequest, NextResponse } from 'next/server';
import { DEFAULT_PREFERENCES, type UserPreferences } from '@/lib/preferences';

export const runtime = 'nodejs';

let sessionPreferences: UserPreferences = DEFAULT_PREFERENCES;

const complexityValues = new Set<UserPreferences['complexity']>(['simple', 'moderate', 'complex']);
const toneValues = new Set<UserPreferences['tone']>(['technical', 'professional', 'casual', 'executive']);

function normalizePreferences(input: Partial<UserPreferences>): UserPreferences {
  return {
    industry: typeof input.industry === 'string' && input.industry.trim()
      ? input.industry.trim()
      : DEFAULT_PREFERENCES.industry,
    complexity: complexityValues.has(input.complexity as UserPreferences['complexity'])
      ? input.complexity as UserPreferences['complexity']
      : DEFAULT_PREFERENCES.complexity,
    tone: toneValues.has(input.tone as UserPreferences['tone'])
      ? input.tone as UserPreferences['tone']
      : DEFAULT_PREFERENCES.tone,
    targetAudience: typeof input.targetAudience === 'string'
      ? input.targetAudience.trim()
      : DEFAULT_PREFERENCES.targetAudience,
    businessModel: typeof input.businessModel === 'string' && input.businessModel.trim()
      ? input.businessModel.trim()
      : DEFAULT_PREFERENCES.businessModel,
  };
}

export async function GET() {
  return NextResponse.json({
    preferences: sessionPreferences,
    source: 'session-default',
  });
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json() as Partial<UserPreferences>;
    sessionPreferences = normalizePreferences(body);
    return NextResponse.json({
      ok: true,
      preferences: sessionPreferences,
    });
  } catch {
    return NextResponse.json(
      {
        ok: false,
        error: 'Invalid JSON body',
        preferences: sessionPreferences,
      },
      { status: 400 },
    );
  }
}

export const POST = PUT;
