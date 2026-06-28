import 'server-only';

import { getGeminiClient } from './gemini-client';

export interface TranscriptSegment {
  start: number;
  duration: number;
  text: string;
}

// Model to use for embeddings
const EMBEDDING_MODEL = 'text-embedding-004';

/**
 * Conceptually chunks the transcript into larger blocks (approx 30-60 seconds)
 * to provide sufficient context for the embedding model.
 */
export function chunkTranscript(segments: TranscriptSegment[], targetDurationSec = 45): TranscriptSegment[] {
  if (!segments || segments.length === 0) return [];

  const chunks: TranscriptSegment[] = [];
  let currentChunk: TranscriptSegment = {
    start: segments[0].start,
    duration: 0,
    text: '',
  };

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    
    // Add space if needed
    if (currentChunk.text.length > 0 && !currentChunk.text.endsWith(' ')) {
      currentChunk.text += ' ';
    }
    
    currentChunk.text += seg.text;
    currentChunk.duration = (seg.start + seg.duration) - currentChunk.start;

    // If we've reached the target duration or it's the last segment, finalize the chunk
    if (currentChunk.duration >= targetDurationSec || i === segments.length - 1) {
      chunks.push({ ...currentChunk });
      
      // Start next chunk if not at end
      if (i < segments.length - 1) {
        currentChunk = {
          start: segments[i + 1].start,
          duration: 0,
          text: '',
        };
      }
    }
  }

  return chunks;
}

/**
 * Generates an embedding for a single text string.
 */
export async function generateEmbedding(text: string): Promise<number[]> {
  const ai = getGeminiClient();
  const response = await ai.models.embedContent({
    model: EMBEDDING_MODEL,
    contents: text,
  });
  
  if (!response.embeddings || response.embeddings.length === 0 || !response.embeddings[0].values) {
    throw new Error('Failed to generate embedding: Empty response from Gemini API.');
  }

  return response.embeddings[0].values;
}

/**
 * Generates embeddings for an array of transcript chunks in batch.
 * Note: Uses sequential requests or batched promises.
 */
export async function generateEmbeddingsForChunks(chunks: TranscriptSegment[]): Promise<Array<TranscriptSegment & { embedding: number[] }>> {
  const ai = getGeminiClient();
  
  // Create an array of requests for batch embedding
  // The SDK allows passing an array of strings directly to generate batch embeddings
  const texts = chunks.map(c => c.text);
  
  try {
    const response = await ai.models.embedContent({
      model: EMBEDDING_MODEL,
      contents: texts,
    });
    
    if (!response.embeddings || response.embeddings.length !== chunks.length) {
      throw new Error(`Embedding count mismatch. Expected ${chunks.length}, got ${response.embeddings?.length || 0}`);
    }

    return chunks.map((chunk, index) => ({
      ...chunk,
      embedding: response.embeddings![index].values!,
    }));
  } catch (error) {
    console.error('Batch embedding generation failed, falling back to sequential:', error);
    
    // Fallback: Sequential generation (in case batch hits limits)
    const results = [];
    for (const chunk of chunks) {
      const emb = await generateEmbedding(chunk.text);
      results.push({ ...chunk, embedding: emb });
      // Minor delay to avoid strict rate limits on fallback
      await new Promise(r => setTimeout(r, 200));
    }
    return results;
  }
}

/**
 * Computes the cosine similarity between two numeric vectors.
 * Returns a value between -1 and 1, where 1 means identical direction.
 */
export function cosineSimilarity(vecA: number[], vecB: number[]): number {
  if (vecA.length !== vecB.length) {
    throw new Error(`Vector length mismatch: ${vecA.length} vs ${vecB.length}`);
  }

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < vecA.length; i++) {
    dotProduct += vecA[i] * vecB[i];
    normA += vecA[i] * vecA[i];
    normB += vecB[i] * vecB[i];
  }

  if (normA === 0 || normB === 0) return 0;
  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}
