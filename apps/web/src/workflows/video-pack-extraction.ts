/**
 * Durable Video Pack extraction.
 *
 * The API claims the idempotent pack record before starting this workflow. The
 * workflow always persists either a ready pack or a visible error record, so a
 * provider outage or billing interruption never leaves a successful-looking
 * response without durable state.
 */
import type { VideoPackV0Json } from '@/lib/video-pack';

export async function videoPackExtractionWorkflow(
  identity: VideoPackV0Json,
): Promise<{ state: 'ready' | 'error' }> {
  'use workflow';

  return persistVideoPackExtractionStep(identity);
}

async function persistVideoPackExtractionStep(
  identity: VideoPackV0Json,
): Promise<{ state: 'ready' | 'error' }> {
  'use step';

  const { persistVideoPackExtraction } = await import('@/lib/video-pack');
  return persistVideoPackExtraction(identity);
}
