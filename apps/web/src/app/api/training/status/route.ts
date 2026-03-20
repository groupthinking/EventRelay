/**
 * GET /api/training/status
 *
 * Returns the current state of the fine-tuning training dataset:
 *  - Total examples collected
 *  - Progress toward the tuning threshold (100)
 *  - Whether fine-tuning is ready to trigger
 *  - Recent videos processed
 */

import { NextResponse } from 'next/server';
import { getTrainingStatus, TUNING_THRESHOLD, TUNING_NOTIFY_AT } from '@/lib/training-store';

export async function GET() {
  try {
    const status = await getTrainingStatus();

    return NextResponse.json({
      dataset: {
        totalExamples: status.metadata.totalExamples,
        threshold: TUNING_THRESHOLD,
        progress: status.progress,
        readyForTuning: status.readyForTuning,
        nextMilestone: status.nextMilestone,
        milestones: TUNING_NOTIFY_AT,
      },
      tuning: {
        triggered: status.metadata.tuningTriggered,
        triggeredAt: status.metadata.tuningTriggeredAt,
        jobId: status.metadata.tuningJobId,
      },
      lastUpdate: {
        timestamp: status.metadata.lastUpdated,
        videoUrl: status.metadata.lastVideoUrl,
        videoTitle: status.metadata.lastVideoTitle,
      },
      recentVideos: status.metadata.videosProcessed.slice(-10),
    });
  } catch (error) {
    console.error('Training status error:', error);
    return NextResponse.json(
      { error: 'Failed to read training status', details: String(error) },
      { status: 500 },
    );
  }
}
