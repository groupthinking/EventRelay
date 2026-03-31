/**
 * Training Data Store — Auto-saves pipeline outputs as JSONL for fine-tuning.
 *
 * Every successful pipeline run is saved as a training example in:
 *   data/training/video-analysis.jsonl
 *
 * Format (Vertex AI SFT compatible):
 * {
 *   "contents": [
 *     { "role": "user", "parts": [{ "text": "<system_prompt + video_url>" }] },
 *     { "role": "model", "parts": [{ "text": "<structured_json_output>" }] }
 *   ]
 * }
 *
 * When the dataset reaches the configured threshold (default: 100),
 * the system can auto-trigger fine-tuning on Vertex AI.
 */

import { promises as fs } from 'fs';
import path from 'path';

/** Where training data lives */
const TRAINING_DIR = path.join(process.cwd(), 'data', 'training');
const TRAINING_FILE = path.join(TRAINING_DIR, 'video-analysis.jsonl');
const METADATA_FILE = path.join(TRAINING_DIR, 'metadata.json');
const BIGQUERY_PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT || 'uvai-730bb';
const BIGQUERY_DATASET = process.env.TRAINING_BIGQUERY_DATASET || 'eventrelay_training';
const BIGQUERY_TABLE = process.env.TRAINING_BIGQUERY_TABLE || 'video_analysis_examples';

/** Thresholds for auto-tuning triggers */
export const TUNING_THRESHOLD = 100;
export const TUNING_NOTIFY_AT = [25, 50, 75, 100];

/** Shape of a single training example (Vertex AI SFT format) */
export interface TrainingExample {
  contents: Array<{
    role: 'user' | 'model';
    parts: Array<{ text: string }>;
  }>;
}

/** Dataset metadata persisted alongside the JSONL */
export interface DatasetMetadata {
  totalExamples: number;
  lastUpdated: string;
  lastVideoUrl: string;
  lastVideoTitle: string;
  tuningTriggered: boolean;
  tuningTriggeredAt: string | null;
  tuningJobId: string | null;
  videosProcessed: string[]; // dedup list of URLs
}

const SYSTEM_PROMPT = `You are a video intelligence analysis engine. Given a YouTube video URL, analyze it and return a structured JSON response containing:
- title: Video title
- summary: Technical summary of the video content
- transcript: Array of timestamped transcript segments
- events: Array of key moments with timestamps, labels, descriptions, code mappings, and cloud service references
- actions: Array of actionable tasks with titles, descriptions, categories, and time estimates
- topics: Array of topic tags
- architectureCode: Mermaid diagram representing the system architecture discussed
- ingestScript: A code snippet for data ingestion
- e22Snippets: Array of code examples with titles, descriptions, code, and language

Output ONLY valid JSON matching this schema.`;

/**
 * Ensure the training directory exists.
 */
async function ensureDir(): Promise<void> {
  await fs.mkdir(TRAINING_DIR, { recursive: true });
}

/**
 * Load current metadata, or create defaults.
 */
export async function getMetadata(): Promise<DatasetMetadata> {
  await ensureDir();
  try {
    const raw = await fs.readFile(METADATA_FILE, 'utf-8');
    return JSON.parse(raw) as DatasetMetadata;
  } catch {
    return {
      totalExamples: 0,
      lastUpdated: '',
      lastVideoUrl: '',
      lastVideoTitle: '',
      tuningTriggered: false,
      tuningTriggeredAt: null,
      tuningJobId: null,
      videosProcessed: [],
    };
  }
}

/**
 * Save metadata to disk.
 */
async function saveMetadata(meta: DatasetMetadata): Promise<void> {
  await ensureDir();
  await fs.writeFile(METADATA_FILE, JSON.stringify(meta, null, 2), 'utf-8');
}

async function exportTrainingExampleToBigQuery(
  videoUrl: string,
  analysisOutput: Record<string, unknown>,
  example: TrainingExample,
  metadata: DatasetMetadata,
): Promise<void> {
  const tokenResponse = await fetch(
    'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',
    { headers: { 'Metadata-Flavor': 'Google' } },
  ).catch((error) => {
    console.debug('[Training] Metadata server unavailable for BigQuery export:', error);
    return null;
  });

  if (!tokenResponse?.ok) {
    return;
  }

  const tokenData = (await tokenResponse.json()) as { access_token?: string };
  if (!tokenData.access_token) {
    return;
  }

  const insertUrl =
    `https://bigquery.googleapis.com/bigquery/v2/projects/${BIGQUERY_PROJECT_ID}` +
    `/datasets/${BIGQUERY_DATASET}/tables/${BIGQUERY_TABLE}/insertAll`;

  const insertId = Buffer.from(videoUrl).toString('base64url');
  const insertResponse = await fetch(insertUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${tokenData.access_token}`,
    },
    body: JSON.stringify({
      rows: [
        {
          insertId,
          json: {
            video_url: videoUrl,
            video_title: String(analysisOutput.title || metadata.lastVideoTitle || 'Unknown'),
            exported_at: new Date().toISOString(),
            total_examples: metadata.totalExamples,
            analysis_output: analysisOutput,
            training_example: example,
          },
        },
      ],
    }),
  });

  if (!insertResponse.ok) {
    const errorText = await insertResponse.text().catch(() => '');
    throw new Error(`BigQuery export failed: ${insertResponse.status} ${errorText}`);
  }
}

/**
 * Save a pipeline run as a training example.
 *
 * Returns the updated metadata including the new example count.
 * If the video URL was already processed, it skips the save (dedup).
 */
export async function saveTrainingExample(
  videoUrl: string,
  analysisOutput: Record<string, unknown>,
): Promise<{ saved: boolean; metadata: DatasetMetadata; milestone: number | null }> {
  await ensureDir();

  const meta = await getMetadata();

  // Dedup: don't save the same video twice
  if (meta.videosProcessed.includes(videoUrl)) {
    return { saved: false, metadata: meta, milestone: null };
  }

  // Build the Vertex AI SFT training example
  const example: TrainingExample = {
    contents: [
      {
        role: 'user',
        parts: [
          {
            text: `${SYSTEM_PROMPT}\n\nAnalyze this video: ${videoUrl}`,
          },
        ],
      },
      {
        role: 'model',
        parts: [
          {
            text: JSON.stringify(analysisOutput),
          },
        ],
      },
    ],
  };

  // Append to JSONL file
  const line = JSON.stringify(example) + '\n';
  await fs.appendFile(TRAINING_FILE, line, 'utf-8');

  // Update metadata
  meta.totalExamples += 1;
  meta.lastUpdated = new Date().toISOString();
  meta.lastVideoUrl = videoUrl;
  meta.lastVideoTitle = (analysisOutput.title as string) || 'Unknown';
  meta.videosProcessed.push(videoUrl);
  await saveMetadata(meta);

  try {
    await exportTrainingExampleToBigQuery(videoUrl, analysisOutput, example, meta);
  } catch (error) {
    console.warn('[Training] BigQuery export failed (non-fatal):', error);
  }

  // Check if we hit a milestone
  const milestone = TUNING_NOTIFY_AT.find((n) => n === meta.totalExamples) || null;

  console.log(
    `[Training] Saved example #${meta.totalExamples} for "${meta.lastVideoTitle}" | ` +
    `${meta.totalExamples}/${TUNING_THRESHOLD} toward fine-tuning` +
    (milestone ? ` | 🎯 MILESTONE: ${milestone} examples reached!` : ''),
  );

  return { saved: true, metadata: meta, milestone };
}

/**
 * Get the current training dataset status.
 */
export async function getTrainingStatus(): Promise<{
  metadata: DatasetMetadata;
  readyForTuning: boolean;
  progress: number;
  nextMilestone: number | null;
}> {
  const meta = await getMetadata();
  const readyForTuning = meta.totalExamples >= TUNING_THRESHOLD;
  const progress = Math.min(100, Math.round((meta.totalExamples / TUNING_THRESHOLD) * 100));

  const nextMilestone =
    TUNING_NOTIFY_AT.find((n) => n > meta.totalExamples) || null;

  return { metadata: meta, readyForTuning, progress, nextMilestone };
}

/**
 * Read the raw JSONL file content for upload to Vertex AI.
 */
export async function readTrainingFile(): Promise<string | null> {
  try {
    return await fs.readFile(TRAINING_FILE, 'utf-8');
  } catch {
    return null;
  }
}

/**
 * Mark that fine-tuning has been triggered.
 */
export async function markTuningTriggered(jobId: string): Promise<void> {
  const meta = await getMetadata();
  meta.tuningTriggered = true;
  meta.tuningTriggeredAt = new Date().toISOString();
  meta.tuningJobId = jobId;
  await saveMetadata(meta);
}
