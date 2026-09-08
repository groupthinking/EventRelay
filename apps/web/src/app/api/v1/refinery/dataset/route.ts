import { NextResponse } from 'next/server';
import { applyVerifiedBillingCookie, requireProFeatureAccess } from '@/lib/billing/pro-feature-gate';
import { getTrainingStatus, readTrainingFile } from '@/lib/training-store';

export const runtime = 'nodejs';

export async function GET(request: Request) {
  const url = new URL(request.url);
  const access = await requireProFeatureAccess(request, {
    featureKey: 'refinery_dataset',
    featureLabel: 'Refinery dataset access',
    sessionId: url.searchParams.get('sessionId') ?? url.searchParams.get('session_id'),
  });
  if (!access.ok) {
    return access.response;
  }

  const status = await getTrainingStatus();
  if (url.searchParams.get('download') !== '1') {
    const response = NextResponse.json({
      dataset: {
        totalExamples: status.metadata.totalExamples,
        readyForTuning: status.readyForTuning,
        progress: status.progress,
        nextMilestone: status.nextMilestone,
        lastUpdated: status.metadata.lastUpdated,
      },
      downloadUrl: '/api/v1/refinery/dataset?download=1',
    });
    applyVerifiedBillingCookie(response, access.signedBillingEmail);
    return response;
  }

  const dataset = await readTrainingFile();
  if (!dataset) {
    return NextResponse.json(
      { error: 'dataset_not_found', code: 'dataset_not_found' },
      { status: 404 },
    );
  }

  const response = new NextResponse(dataset, {
    status: 200,
    headers: {
      'cache-control': 'no-store',
      'content-disposition': 'attachment; filename="refinery-dataset.jsonl"',
      'content-type': 'application/x-ndjson; charset=utf-8',
      'x-training-examples': String(status.metadata.totalExamples),
    },
  });
  applyVerifiedBillingCookie(response, access.signedBillingEmail);
  return response;
}
