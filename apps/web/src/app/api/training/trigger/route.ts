/**
 * POST /api/training/trigger
 *
 * Triggers fine-tuning of Gemini 2.5 Flash on Vertex AI using the
 * collected training dataset.
 *
 * Modes:
 *   - "check"   → Returns status only, no action (default)
 *   - "upload"   → Uploads JSONL to GCS bucket
 *   - "trigger"  → Uploads + submits the Vertex AI SFT job
 *
 * Prerequisites:
 *   - GOOGLE_CLOUD_PROJECT env var (defaults to uvai-730bb)
 *   - GCS bucket: gs://{project}-training/
 *   - Vertex AI API enabled
 *   - Service account with roles/aiplatform.user
 */

import { NextResponse } from 'next/server';
import {
  getTrainingStatus,
  readTrainingFile,
  markTuningTriggered,
  TUNING_THRESHOLD,
} from '@/lib/training-store';

export const runtime = 'nodejs';
export const maxDuration = 300;

const PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT || 'uvai-730bb';
const REGION = process.env.VERTEX_AI_REGION || 'us-central1';
const BUCKET = process.env.TRAINING_BUCKET || `${PROJECT_ID}-training`;
const BASE_MODEL = 'gemini-2.5-flash';

interface TriggerRequest {
  mode?: 'check' | 'upload' | 'trigger';
  force?: boolean;
}

export async function POST(request: Request) {
  try {
    const body: TriggerRequest = await request.json().catch(() => ({}));
    const mode = body.mode || 'check';
    const force = body.force || false;

    const status = await getTrainingStatus();

    // ── Check mode: just return status ──
    if (mode === 'check') {
      return NextResponse.json({
        mode: 'check',
        ready: status.readyForTuning,
        examples: status.metadata.totalExamples,
        threshold: TUNING_THRESHOLD,
        progress: status.progress,
        alreadyTriggered: status.metadata.tuningTriggered,
        message: status.readyForTuning
          ? '✅ Dataset ready for fine-tuning! POST with mode: "trigger" to start.'
          : `⏳ ${status.metadata.totalExamples}/${TUNING_THRESHOLD} examples collected. ` +
            `Need ${TUNING_THRESHOLD - status.metadata.totalExamples} more.`,
      });
    }

    // Check if we have enough data
    if (!status.readyForTuning && !force) {
      return NextResponse.json({
        error: 'Not enough training data',
        examples: status.metadata.totalExamples,
        threshold: TUNING_THRESHOLD,
        message: `Need ${TUNING_THRESHOLD - status.metadata.totalExamples} more examples. ` +
                 `Use "force: true" to override.`,
      }, { status: 400 });
    }

    // Check if already triggered
    if (status.metadata.tuningTriggered && !force) {
      return NextResponse.json({
        error: 'Fine-tuning already triggered',
        jobId: status.metadata.tuningJobId,
        triggeredAt: status.metadata.tuningTriggeredAt,
        message: 'Use "force: true" to trigger a new tuning job.',
      }, { status: 409 });
    }

    // Read the JSONL dataset
    const jsonlContent = await readTrainingFile();
    if (!jsonlContent) {
      return NextResponse.json(
        { error: 'Training file not found or empty' },
        { status: 404 },
      );
    }

    const exampleCount = jsonlContent.trim().split('\n').length;

    // ── Upload mode: upload to GCS ──
    if (mode === 'upload' || mode === 'trigger') {
      const gcsPath = `gs://${BUCKET}/video-analysis/${new Date().toISOString().split('T')[0]}/training.jsonl`;

      // Use the Google Cloud Storage JSON API
      const bucketName = BUCKET;
      const objectName = `video-analysis/${new Date().toISOString().split('T')[0]}/training.jsonl`;
      const uploadUrl = `https://storage.googleapis.com/upload/storage/v1/b/${bucketName}/o?uploadType=media&name=${encodeURIComponent(objectName)}`;

      try {
        // Try to get the default credentials token
        const tokenResponse = await fetch(
          'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',
          { headers: { 'Metadata-Flavor': 'Google' } },
        ).catch(() => null);

        let authHeader: string | undefined;
        if (tokenResponse?.ok) {
          const tokenData = await tokenResponse.json();
          authHeader = `Bearer ${tokenData.access_token}`;
        }

        // If running on GCP, upload with token. Otherwise, log the command.
        if (authHeader) {
          const uploadResponse = await fetch(uploadUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/jsonl',
              Authorization: authHeader,
            },
            body: jsonlContent,
          });

          if (!uploadResponse.ok) {
            throw new Error(`GCS upload failed: ${uploadResponse.status}`);
          }

          console.log(`[Training] Uploaded ${exampleCount} examples to ${gcsPath}`);
        } else {
          // Running locally — provide the manual command
          console.log(`[Training] Running locally. Upload manually with:`);
          console.log(`  gsutil cp data/training/video-analysis.jsonl ${gcsPath}`);
        }

        if (mode === 'upload') {
          return NextResponse.json({
            mode: 'upload',
            status: authHeader ? 'uploaded' : 'local_only',
            gcsPath,
            examples: exampleCount,
            message: authHeader
              ? `✅ Uploaded ${exampleCount} examples to ${gcsPath}`
              : `📁 File ready at data/training/video-analysis.jsonl — upload manually: gsutil cp data/training/video-analysis.jsonl ${gcsPath}`,
          });
        }

        // ── Trigger mode: submit Vertex AI SFT job ──
        const tuningJobId = `sft-video-analysis-${Date.now().toString(36)}`;

        if (authHeader) {
          // Submit the tuning job via Vertex AI REST API
          const tuningUrl = `https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/tuningJobs`;

          const tuningResponse = await fetch(tuningUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: authHeader,
            },
            body: JSON.stringify({
              baseModel: BASE_MODEL,
              supervisedTuningSpec: {
                trainingDatasetUri: gcsPath,
                hyperParameters: {
                  epochCount: 3,
                  learningRateMultiplier: 1.0,
                },
              },
              tunedModelDisplayName: `uvai-video-analyzer-${new Date().toISOString().split('T')[0]}`,
            }),
          });

          if (tuningResponse.ok) {
            const tuningResult = await tuningResponse.json();
            const vertexJobId = tuningResult.name || tuningJobId;
            await markTuningTriggered(vertexJobId);

            console.log(`\n🚀 FINE-TUNING STARTED: ${vertexJobId}`);
            console.log(`   Model: ${BASE_MODEL}`);
            console.log(`   Examples: ${exampleCount}`);
            console.log(`   Dataset: ${gcsPath}`);

            return NextResponse.json({
              mode: 'trigger',
              status: 'started',
              jobId: vertexJobId,
              model: BASE_MODEL,
              examples: exampleCount,
              gcsPath,
              region: REGION,
              project: PROJECT_ID,
              message: `🚀 Fine-tuning job submitted! Monitor at: https://console.cloud.google.com/vertex-ai/training/tuning-jobs?project=${PROJECT_ID}`,
            });
          } else {
            const errText = await tuningResponse.text();
            throw new Error(`Vertex AI tuning API returned ${tuningResponse.status}: ${errText}`);
          }
        } else {
          // Running locally — provide the gcloud command
          await markTuningTriggered(tuningJobId);

          const gcloudCmd = [
            'gcloud ai tuning-jobs create',
            `  --base-model=${BASE_MODEL}`,
            `  --training-data=${gcsPath}`,
            `  --tuned-model-display-name=uvai-video-analyzer-${new Date().toISOString().split('T')[0]}`,
            `  --epoch-count=3`,
            `  --region=${REGION}`,
            `  --project=${PROJECT_ID}`,
          ].join(' \\\n');

          return NextResponse.json({
            mode: 'trigger',
            status: 'local_ready',
            jobId: tuningJobId,
            model: BASE_MODEL,
            examples: exampleCount,
            gcsPath,
            message: '📁 Dataset ready. Run these commands to fine-tune:',
            commands: [
              `gsutil cp data/training/video-analysis.jsonl ${gcsPath}`,
              gcloudCmd,
            ],
            consoleUrl: `https://console.cloud.google.com/vertex-ai/training/tuning-jobs?project=${PROJECT_ID}`,
          });
        }
      } catch (uploadError) {
        return NextResponse.json({
          error: 'Upload/trigger failed',
          fallback: {
            message: 'Run manually:',
            commands: [
              `gsutil mb gs://${BUCKET}`,
              `gsutil cp data/training/video-analysis.jsonl gs://${BUCKET}/video-analysis/training.jsonl`,
              `gcloud ai tuning-jobs create --base-model=${BASE_MODEL} --training-data=gs://${BUCKET}/video-analysis/training.jsonl --tuned-model-display-name=uvai-video-analyzer --epoch-count=3 --region=${REGION} --project=${PROJECT_ID}`,
            ],
          },
        }, { status: 500 });
      }
    }

    return NextResponse.json({ error: 'Invalid mode. Use: check, upload, or trigger' }, { status: 400 });
  } catch (error) {
    console.error('Training trigger error:', error);
    return NextResponse.json(
      { error: 'Failed to process training request' },
      { status: 500 },
    );
  }
}
