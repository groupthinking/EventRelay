/**
 * Embedding Service - Vector operations for RAG search
 *
 * Uses:
 * - Vertex AI text-embedding-004 for generating embeddings
 * - Cloud SQL PostgreSQL with pgvector for storage
 * - Firebase Data Connect for query operations
 *
 * ARCHITECTURE: The SDK doesn't support Vector type in mutations,
 * so we use Cloud SQL directly for inserts but Firebase Data Connect
 * SDK for queries.
 */

import { VertexAI } from "@google-cloud/vertexai";
import { Pool } from "pg";
import {
  listEmbeddings,
  getJobEmbeddings,
  deleteJobEmbeddings,
} from "../dataconnect-generated";

// =============================================================================
// Types
// =============================================================================

export interface EmbeddingRequest {
  jobId: string;
  segmentType: "summary" | "step" | "insight" | "code";
  segmentIndex: number;
  content: string;
}

export interface EmbeddingRecord {
  id: string;
  segmentType: string;
  segmentIndex: number;
  content: string;
  jobId: string;
  jobTitle?: string;
  videoUrl?: string;
}

export interface SearchResult {
  content: string;
  segmentType: string;
  jobId: string;
  jobTitle: string;
  videoUrl: string;
  similarity: number;
}

// =============================================================================
// Configuration
// =============================================================================

const PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT || "uvai-730bb";
const LOCATION = process.env.GCP_LOCATION || "us-central1";
const EMBEDDING_MODEL = "text-embedding-004";
const EMBEDDING_DIMENSION = 768;

// Cloud SQL connection config
// In production, use Cloud SQL Auth Proxy or private IP
const getPoolConfig = () => ({
  host: process.env.CLOUDSQL_HOST || "/cloudsql/uvai-730bb:us-central1:uvai-vector-db",
  database: process.env.CLOUDSQL_DATABASE || "uvai-730bb-database",
  user: process.env.CLOUDSQL_USER || "postgres",
  password: process.env.CLOUDSQL_PASSWORD,
  max: 5,
});

// =============================================================================
// Vertex AI Embeddings
// =============================================================================

let vertexAI: VertexAI | null = null;

function getVertexAI(): VertexAI {
  if (!vertexAI) {
    vertexAI = new VertexAI({ project: PROJECT_ID, location: LOCATION });
  }
  return vertexAI;
}

/**
 * Generate embedding for a single text using Vertex AI
 */
export async function generateEmbedding(text: string): Promise<number[]> {
  const vertexai = getVertexAI();
  const model = vertexai.getGenerativeModel({ model: EMBEDDING_MODEL });

  // Vertex AI embedding via content generation
  // For actual embeddings, use the Embeddings API
  const response = await fetch(
    `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${EMBEDDING_MODEL}:predict`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${await getAccessToken()}`,
      },
      body: JSON.stringify({
        instances: [{ content: text }],
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`Embedding API error: ${response.status} ${await response.text()}`);
  }

  const data = await response.json();
  return data.predictions[0].embeddings.values;
}

/**
 * Generate embeddings for multiple texts in batch
 */
export async function generateEmbeddings(texts: string[]): Promise<number[][]> {
  const response = await fetch(
    `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${EMBEDDING_MODEL}:predict`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${await getAccessToken()}`,
      },
      body: JSON.stringify({
        instances: texts.map((text) => ({ content: text })),
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`Embedding API error: ${response.status} ${await response.text()}`);
  }

  const data = await response.json();
  return data.predictions.map((p: { embeddings: { values: number[] } }) => p.embeddings.values);
}

/**
 * Get access token for Vertex AI API calls
 */
async function getAccessToken(): Promise<string> {
  // In Cloud Run, use the metadata server
  if (process.env.K_SERVICE) {
    const response = await fetch(
      "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
      { headers: { "Metadata-Flavor": "Google" } }
    );
    const data = await response.json();
    return data.access_token;
  }

  // Local development - use gcloud
  const { execSync } = await import("child_process");
  return execSync("gcloud auth print-access-token", { encoding: "utf-8" }).trim();
}

// =============================================================================
// Database Operations (Raw SQL for Vector inserts)
// =============================================================================

let pool: Pool | null = null;

function getPool(): Pool {
  if (!pool) {
    pool = new Pool(getPoolConfig());
  }
  return pool;
}

/**
 * Store embedding in pgvector via raw SQL
 */
export async function storeEmbedding(
  request: EmbeddingRequest,
  embedding: number[]
): Promise<string> {
  const client = getPool();

  const result = await client.query(
    `INSERT INTO video_embedding (job_id, segment_type, segment_index, content, embedding, created_at)
     VALUES ($1, $2, $3, $4, $5::vector, NOW())
     RETURNING id`,
    [
      request.jobId,
      request.segmentType,
      request.segmentIndex,
      request.content,
      `[${embedding.join(",")}]`,
    ]
  );

  return result.rows[0].id;
}

/**
 * Store multiple embeddings in batch
 */
export async function storeEmbeddings(
  requests: EmbeddingRequest[],
  embeddings: number[][]
): Promise<string[]> {
  const client = getPool();
  const ids: string[] = [];

  // Use a transaction for batch insert
  await client.query("BEGIN");
  try {
    for (let i = 0; i < requests.length; i++) {
      const result = await client.query(
        `INSERT INTO video_embedding (job_id, segment_type, segment_index, content, embedding, created_at)
         VALUES ($1, $2, $3, $4, $5::vector, NOW())
         RETURNING id`,
        [
          requests[i].jobId,
          requests[i].segmentType,
          requests[i].segmentIndex,
          requests[i].content,
          `[${embeddings[i].join(",")}]`,
        ]
      );
      ids.push(result.rows[0].id);
    }
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  }

  return ids;
}

/**
 * Semantic similarity search using pgvector
 */
export async function searchSimilar(
  query: string,
  limit: number = 10
): Promise<SearchResult[]> {
  // Generate embedding for query
  const queryEmbedding = await generateEmbedding(query);

  const client = getPool();

  // Use cosine distance for similarity (<=>)
  // pgvector returns results ordered by distance (ascending = most similar first)
  const result = await client.query(
    `SELECT
       ve.id,
       ve.segment_type,
       ve.segment_index,
       ve.content,
       ve.job_id,
       vj.title as job_title,
       vj.video_url,
       1 - (ve.embedding <=> $1::vector) as similarity
     FROM video_embedding ve
     JOIN video_job vj ON ve.job_id = vj.id
     ORDER BY ve.embedding <=> $1::vector
     LIMIT $2`,
    [`[${queryEmbedding.join(",")}]`, limit]
  );

  return result.rows.map((row) => ({
    content: row.content,
    segmentType: row.segment_type,
    jobId: row.job_id,
    jobTitle: row.job_title || "Untitled",
    videoUrl: row.video_url,
    similarity: parseFloat(row.similarity),
  }));
}

// =============================================================================
// High-Level Operations
// =============================================================================

/**
 * Process a job and generate/store all embeddings
 */
export async function embedJobAnalysis(
  jobId: string,
  analysis: {
    summary: string;
    steps: string[];
    insights: string[];
    codeBlocks?: string[];
  }
): Promise<{ embeddingCount: number; embeddingIds: string[] }> {
  const requests: EmbeddingRequest[] = [];
  const texts: string[] = [];

  // Summary embedding
  if (analysis.summary) {
    requests.push({
      jobId,
      segmentType: "summary",
      segmentIndex: 0,
      content: analysis.summary,
    });
    texts.push(analysis.summary);
  }

  // Step embeddings
  analysis.steps.forEach((step, i) => {
    requests.push({
      jobId,
      segmentType: "step",
      segmentIndex: i,
      content: step,
    });
    texts.push(step);
  });

  // Insight embeddings
  analysis.insights.forEach((insight, i) => {
    requests.push({
      jobId,
      segmentType: "insight",
      segmentIndex: i,
      content: insight,
    });
    texts.push(insight);
  });

  // Code block embeddings
  analysis.codeBlocks?.forEach((code, i) => {
    requests.push({
      jobId,
      segmentType: "code",
      segmentIndex: i,
      content: code,
    });
    texts.push(code);
  });

  if (texts.length === 0) {
    return { embeddingCount: 0, embeddingIds: [] };
  }

  // Generate all embeddings in batch
  console.log(`[EMBED] Generating ${texts.length} embeddings for job ${jobId}`);
  const embeddings = await generateEmbeddings(texts);

  // Store all embeddings
  console.log(`[EMBED] Storing ${embeddings.length} embeddings in pgvector`);
  const embeddingIds = await storeEmbeddings(requests, embeddings);

  return { embeddingCount: embeddingIds.length, embeddingIds };
}

/**
 * Get all embeddings for a job via Firebase Data Connect SDK
 */
export async function getEmbeddingsForJob(jobId: string): Promise<EmbeddingRecord[]> {
  const result = await getJobEmbeddings({ jobId: jobId as `${string}-${string}-${string}-${string}-${string}` });
  return result.data.videoEmbeddings.map((e) => ({
    id: e.id,
    segmentType: e.segmentType,
    segmentIndex: e.segmentIndex,
    content: e.content,
    jobId,
  }));
}

/**
 * Delete all embeddings for a job
 */
export async function clearJobEmbeddings(jobId: string): Promise<void> {
  await deleteJobEmbeddings({ jobId: jobId as `${string}-${string}-${string}-${string}-${string}` });
}

/**
 * List recent embeddings
 */
export async function listRecentEmbeddings(limit: number = 100): Promise<EmbeddingRecord[]> {
  const result = await listEmbeddings({ limit });
  return result.data.videoEmbeddings.map((e) => ({
    id: e.id,
    segmentType: e.segmentType,
    segmentIndex: e.segmentIndex,
    content: e.content,
    jobId: e.job?.id || "",
    jobTitle: e.job?.title || undefined,
    videoUrl: e.job?.videoUrl,
  }));
}
