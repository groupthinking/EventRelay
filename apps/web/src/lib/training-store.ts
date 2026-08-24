import 'server-only';

/**
 * Training Data Store — accumulates pipeline outputs for fine-tuning.
 *
 * Backed by Postgres (`training_examples`, `training_runs`). Examples are
 * serialised to Vertex AI SFT-compatible JSONL on demand by
 * `readTrainingFile()`; nothing is written to the local filesystem.
 *
 * Why this was rewritten (audit finding F4):
 *
 * This module previously appended to `data/training/video-analysis.jsonl` under
 * `process.cwd()`. On Vercel that directory is part of a read-only bundle, so
 * `fs.mkdir` rejected with EROFS and **every** save threw. Because
 * `getMetadata()` also called `ensureDir()` before reading, the read path threw
 * too — so `/api/training/status` returned a 500 instead of reporting an empty
 * dataset. The system had been reporting a growing training corpus that did not
 * exist.
 *
 * Dedup is now a UNIQUE index on `video_url` rather than a
 * `videosProcessed.includes(url)` scan. The old check was read-then-write with
 * no atomicity: two concurrent runs of the same video could both pass the check
 * and both append. `ON CONFLICT DO NOTHING` plus the index makes duplicates
 * impossible under any interleaving.
 *
 * BigQuery export remains best-effort with explicit timeouts, unchanged.
 */

import { sql } from 'drizzle-orm';
import { getDb, queryRows, requireDb } from '@/lib/db/client';

const BIGQUERY_PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT;
const BIGQUERY_DATASET = process.env.TRAINING_BIGQUERY_DATASET;
const BIGQUERY_TABLE = process.env.TRAINING_BIGQUERY_TABLE;

/** Network timeouts (ms) */
const METADATA_SERVER_TIMEOUT_MS = 3_000; // metadata server responds instantly on GCP
const BIGQUERY_INSERT_TIMEOUT_MS = 10_000;

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

/**
 * Dataset metadata.
 *
 * Shape preserved from the file-backed implementation so the four existing
 * callers need no changes. It is now derived from the tables on read rather
 * than stored as a mutable JSON blob, which removes a second read-then-write
 * race on the counter itself.
 */
export interface DatasetMetadata {
  totalExamples: number;
  lastUpdated: string;
  lastVideoUrl: string;
  lastVideoTitle: string;
  tuningTriggered: boolean;
  tuningTriggeredAt: string | null;
  tuningJobId: string | null;
  videosProcessed: string[];
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

/** Metadata for a dataset that has no storage configured or no rows yet. */
function emptyMetadata(): DatasetMetadata {
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

/**
 * Load dataset metadata.
 *
 * Read-only: unlike the previous implementation this never attempts to create
 * storage as a side effect of reading, so a status check cannot fail because of
 * a write permission problem.
 */
export async function getMetadata(): Promise<DatasetMetadata> {
  const db = getDb();
  if (!db) return emptyMetadata();

  const [stats] = await queryRows<{
    total: number;
    last_updated: string | null;
    last_url: string | null;
    last_title: string | null;
  }>(
    db,
    sql`
    SELECT
      COUNT(*)::int                                        AS total,
      MAX(created_at)                                      AS last_updated,
      (SELECT video_url   FROM training_examples ORDER BY created_at DESC LIMIT 1) AS last_url,
      (SELECT video_title FROM training_examples ORDER BY created_at DESC LIMIT 1) AS last_title
    FROM training_examples
  `,
  );

  const [job] = await queryRows<{
    tuning_triggered_at: string | null;
    tuning_job_id: string | null;
  }>(db, sql`SELECT tuning_triggered_at, tuning_job_id FROM training_runs WHERE id = 1`);

  // `videosProcessed` is retained for API compatibility. It is intentionally
  // capped: the original unbounded array was serialised into every response and
  // grew without limit. Dedup no longer depends on it.
  const processed = await queryRows<{ video_url: string }>(
    db,
    sql`SELECT video_url FROM training_examples ORDER BY created_at DESC LIMIT 500`,
  );

  return {
    totalExamples: stats?.total ?? 0,
    lastUpdated: stats?.last_updated ? new Date(stats.last_updated).toISOString() : '',
    lastVideoUrl: stats?.last_url ?? '',
    lastVideoTitle: stats?.last_title ?? '',
    tuningTriggered: Boolean(job?.tuning_triggered_at),
    tuningTriggeredAt: job?.tuning_triggered_at
      ? new Date(job.tuning_triggered_at).toISOString()
      : null,
    tuningJobId: job?.tuning_job_id ?? null,
    videosProcessed: processed.map((r) => r.video_url),
  };
}

/**
 * Export a training example to BigQuery. Best-effort with explicit timeouts.
 *
 * On non-GCP hosts (e.g. Vercel) the metadata server fetch aborts in 3s instead
 * of hanging — this was the root cause of the 95% pipeline hang, see
 * https://github.com/groupthinking/EventRelay/issues/139
 */
async function exportTrainingExampleToBigQuery(
  videoUrl: string,
  analysisOutput: Record<string, unknown>,
  example: TrainingExample,
  metadata: DatasetMetadata,
): Promise<void> {
  if (!BIGQUERY_PROJECT_ID || !BIGQUERY_DATASET || !BIGQUERY_TABLE) {
    console.debug('[Training] BigQuery env vars not configured — skipping export.');
    return;
  }

  let tokenResponse: Response | null = null;
  try {
    tokenResponse = await fetch(
      'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',
      {
        headers: { 'Metadata-Flavor': 'Google' },
        signal: AbortSignal.timeout(METADATA_SERVER_TIMEOUT_MS),
      },
    );
  } catch (error) {
    console.debug('[Training] Metadata server unavailable for BigQuery export:', error);
    return;
  }

  if (!tokenResponse || !tokenResponse.ok) {
    console.debug(
      '[Training] Metadata server returned error for BigQuery export (status: ' +
        (tokenResponse?.status || 'unavailable') +
        '). Training data saved to Postgres only.',
    );
    return;
  }

  const tokenData = (await tokenResponse.json()) as { access_token?: string };
  if (!tokenData.access_token) {
    console.debug(
      '[Training] Google Cloud access token missing from metadata response. ' +
        'Training data saved to Postgres only.',
    );
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
    signal: AbortSignal.timeout(BIGQUERY_INSERT_TIMEOUT_MS),
  });

  if (!insertResponse.ok) {
    const errorText = await insertResponse.text().catch(() => '');
    throw new Error(`BigQuery export failed: ${insertResponse.status} ${errorText}`);
  }
}

/**
 * Save a pipeline run as a training example.
 *
 * Returns `saved: false` when the video was already recorded. Dedup is decided
 * by the database via `ON CONFLICT DO NOTHING`, so the answer is authoritative
 * even when two runs race.
 */
export async function saveTrainingExample(
  videoUrl: string,
  analysisOutput: Record<string, unknown>,
): Promise<{ saved: boolean; metadata: DatasetMetadata; milestone: number | null }> {
  // requireDb, not getDb: a save that cannot persist must fail loudly. Silently
  // discarding it is what produced a phantom training corpus.
  const db = requireDb();

  const example: TrainingExample = {
    contents: [
      { role: 'user', parts: [{ text: `${SYSTEM_PROMPT}\n\nAnalyze this video: ${videoUrl}` }] },
      { role: 'model', parts: [{ text: JSON.stringify(analysisOutput) }] },
    ],
  };

  const title = (analysisOutput.title as string) || 'Unknown';

  const inserted = await queryRows<{ id: string }>(db, sql`
    INSERT INTO training_examples (video_url, video_title, example, analysis)
    VALUES (
      ${videoUrl},
      ${title},
      ${JSON.stringify(example)}::jsonb,
      ${JSON.stringify(analysisOutput)}::jsonb
    )
    ON CONFLICT (video_url) DO NOTHING
    RETURNING id
  `);

  // Empty result means the unique index rejected it: already present.
  if (inserted.length === 0) {
    return { saved: false, metadata: await getMetadata(), milestone: null };
  }

  const meta = await getMetadata();

  try {
    await exportTrainingExampleToBigQuery(videoUrl, analysisOutput, example, meta);
  } catch (error) {
    console.warn('[Training] BigQuery export failed (non-fatal):', error);
  }

  const milestone = TUNING_NOTIFY_AT.find((n) => n === meta.totalExamples) || null;

  console.log(
    `[Training] Saved example #${meta.totalExamples} for "${meta.lastVideoTitle}" | ` +
      `${meta.totalExamples}/${TUNING_THRESHOLD} toward fine-tuning` +
      (milestone ? ` | MILESTONE: ${milestone} examples reached!` : ''),
  );

  return { saved: true, metadata: meta, milestone };
}

/** Current training dataset status. */
export async function getTrainingStatus(): Promise<{
  metadata: DatasetMetadata;
  readyForTuning: boolean;
  progress: number;
  nextMilestone: number | null;
}> {
  const meta = await getMetadata();
  const readyForTuning = meta.totalExamples >= TUNING_THRESHOLD;
  const progress = Math.min(100, Math.round((meta.totalExamples / TUNING_THRESHOLD) * 100));
  const nextMilestone = TUNING_NOTIFY_AT.find((n) => n > meta.totalExamples) || null;

  return { metadata: meta, readyForTuning, progress, nextMilestone };
}

/**
 * Serialise the dataset as JSONL for upload to Vertex AI.
 *
 * Returns null when there is nothing to upload, preserving the previous
 * contract for callers that treat null as "no dataset".
 */
export async function readTrainingFile(): Promise<string | null> {
  const db = getDb();
  if (!db) return null;

  const rows = await queryRows<{ example: TrainingExample }>(
    db,
    sql`SELECT example FROM training_examples ORDER BY created_at ASC`,
  );
  if (rows.length === 0) return null;

  return rows.map((r) => JSON.stringify(r.example)).join('\n') + '\n';
}

/** Mark that fine-tuning has been triggered. */
export async function markTuningTriggered(jobId: string): Promise<void> {
  const db = requireDb();
  await db.execute(sql`
    UPDATE training_runs
       SET tuning_triggered_at = now(), tuning_job_id = ${jobId}
     WHERE id = 1
  `);
}
