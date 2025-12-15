import { Ai } from '@cloudflare/ai';
import { VectorizeIndex, VectorizeVector, VectorizeMatches } from '@cloudflare/workers-types';

export class VectorService {
    constructor(private env: Env) {}

    /**
     * Generates embeddings for the given text using the BGE base model.
     * @param text Single string or array of strings to embed
     * @returns Array of vectors
     */
    async generateEmbeddings(text: string | string[]): Promise<number[][]> {
        const response = await this.env.AI.run('@cf/baai/bge-base-en-v1.5', {
            text: text
        });

        // Response format is { shape: [BatchSize, Dimensions], data: number[][] }
        // or just number[][] depending on version/wrapping. 
        // Based on docs: { shape: number[], data: number[][] }
        if ('data' in response && Array.isArray(response.data)) {
            return response.data;
        }
        
        // Fallback or if types behave differently than expected
        return response as unknown as number[][];
    }

    /**
     * Inserts vectors into the index.
     * @param vectors Array of vectors to insert
     */
    async insertVectors(vectors: VectorizeVector[]): Promise<void> {
        // Upsert allows overwriting if ID exists
        await this.env.VECTORIZE.upsert(vectors);
    }

    /**
     * Searches for similar vectors.
     * @param query The search query text
     * @param topK Number of results to return
     * @returns Matches found
     */
    async search(query: string, topK: number = 5): Promise<VectorizeMatches> {
        const queryEmbeddings = await this.generateEmbeddings(query);
        
        // We assume single query string, so first vector
        const queryVector = queryEmbeddings[0];

        if (!queryVector) {
            throw new Error('Failed to generate embedding for query');
        }

        return await this.env.VECTORIZE.query(queryVector, {
            topK,
            returnMetadata: true
        });
    }

    /**
     * Helper to embed and insert a document in one go.
     * @param id Unique ID for the document
     * @param text Text content
     * @param metadata Optional metadata
     */
    async embedAndInsert(id: string, text: string, metadata?: Record<string, any>): Promise<void> {
        const embeddings = await this.generateEmbeddings(text);
        const vector: VectorizeVector = {
            id,
            values: embeddings[0],
            metadata
        };
        await this.insertVectors([vector]);
    }
}
