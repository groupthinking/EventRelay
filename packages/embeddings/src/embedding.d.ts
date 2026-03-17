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
/**
 * Generate embedding for a single text using Vertex AI
 */
export declare function generateEmbedding(text: string): Promise<number[]>;
/**
 * Generate embeddings for multiple texts in batch
 */
export declare function generateEmbeddings(texts: string[]): Promise<number[][]>;
/**
 * Store embedding in pgvector via raw SQL
 */
export declare function storeEmbedding(request: EmbeddingRequest, embedding: number[]): Promise<string>;
/**
 * Store multiple embeddings in batch
 */
export declare function storeEmbeddings(requests: EmbeddingRequest[], embeddings: number[][]): Promise<string[]>;
/**
 * Semantic similarity search using pgvector
 */
export declare function searchSimilar(query: string, limit?: number): Promise<SearchResult[]>;
/**
 * Process a job and generate/store all embeddings
 */
export declare function embedJobAnalysis(jobId: string, analysis: {
    summary: string;
    steps: string[];
    insights: string[];
    codeBlocks?: string[];
}): Promise<{
    embeddingCount: number;
    embeddingIds: string[];
}>;
/**
 * Get all embeddings for a job via Firebase Data Connect SDK
 */
export declare function getEmbeddingsForJob(jobId: string): Promise<EmbeddingRecord[]>;
/**
 * Delete all embeddings for a job
 */
export declare function clearJobEmbeddings(jobId: string): Promise<void>;
/**
 * List recent embeddings
 */
export declare function listRecentEmbeddings(limit?: number): Promise<EmbeddingRecord[]>;
