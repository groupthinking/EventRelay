import 'server-only';

import { promises as fs } from 'fs';
import path from 'path';

/** Where embedding data lives */
const EMBEDDING_DIR = path.join(process.cwd(), 'data', 'embeddings');

export interface ChunkEmbedding {
  start: number;
  duration: number;
  text: string;
  embedding: number[];
}

export interface VideoEmbeddings {
  videoId: string;
  chunks: ChunkEmbedding[];
  lastUpdated: string;
}

/** Ensure the embedding directory exists. */
async function ensureDir(): Promise<void> {
  await fs.mkdir(EMBEDDING_DIR, { recursive: true });
}

/** Build the local file path for a video's embeddings. */
function getFilePath(videoId: string): string {
  // Sanitize the video ID for file system naming
  const safeId = videoId.replace(/[^a-zA-Z0-9_-]/g, '_');
  return path.join(EMBEDDING_DIR, `${safeId}.json`);
}

/**
 * Save embedding chunks for a specific video to disk.
 */
export async function saveEmbeddings(videoId: string, chunks: ChunkEmbedding[]): Promise<void> {
  await ensureDir();
  const filePath = getFilePath(videoId);

  const data: VideoEmbeddings = {
    videoId,
    chunks,
    lastUpdated: new Date().toISOString(),
  };

  await fs.writeFile(filePath, JSON.stringify(data, null, 2), 'utf-8');
  console.log(`[Embedding Store] Successfully saved ${chunks.length} embeddings for video: ${videoId}`);
}

/**
 * Load embedding chunks for a specific video from disk.
 * Returns null if the embeddings do not exist yet.
 */
export async function loadEmbeddings(videoId: string): Promise<VideoEmbeddings | null> {
  try {
    const filePath = getFilePath(videoId);
    const raw = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(raw) as VideoEmbeddings;
  } catch {
    return null;
  }
}
