import 'server-only';

/**
 * Internal RAG helpers adapted from vercel-labs/ai-gateway-embeddings-demo.
 * Used by pipeline background embedding + /api/video/search — not surfaced in UI.
 */

import { cosineSimilarity } from '@/lib/gemini-embedding';
import {
  chunkTextForEmbedding,
  gatewayEmbed,
  gatewayEmbedOne,
  hasAiGatewayKey,
} from '@/lib/vercel-ai-gateway';

export interface RagChunk {
  content: string;
  embedding: number[];
}

export interface RagSearchHit {
  content: string;
  score: number;
}

export async function generateGatewayEmbeddings(value: string): Promise<RagChunk[]> {
  if (!hasAiGatewayKey()) {
    throw new Error('AI Gateway is required for internal RAG embeddings');
  }

  const chunks = chunkTextForEmbedding(value);
  if (chunks.length === 0) return [];

  const { embeddings } = await gatewayEmbed({ input: chunks });
  return chunks.map((content, index) => ({
    content,
    embedding: embeddings[index],
  }));
}

export async function findRelevantGatewayContent(
  userQuery: string,
  corpus: RagChunk[],
  limit = 4,
  minScore = 0.5,
): Promise<RagSearchHit[]> {
  if (!hasAiGatewayKey() || corpus.length === 0) return [];

  const queryEmbedding = await gatewayEmbedOne(userQuery);
  const scored = corpus
    .map((chunk) => ({
      content: chunk.content,
      score: cosineSimilarity(queryEmbedding, chunk.embedding),
    }))
    .filter((row) => row.score >= minScore)
    .sort((a, b) => b.score - a.score);

  return scored.slice(0, limit);
}