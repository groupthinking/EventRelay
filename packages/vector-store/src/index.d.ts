export interface VectorDocument {
    id: string;
    content: string;
    metadata?: Record<string, unknown>;
    embedding?: number[];
}
export interface VectorSearchResult {
    id: string;
    score: number;
    content: string;
    metadata?: Record<string, unknown>;
}
export interface VectorStoreConfig {
    provider: 'pinecone' | 'supabase';
    pinecone?: {
        apiKey: string;
        indexName: string;
    };
    supabase?: {
        url: string;
        anonKey: string;
        tableName: string;
    };
    openai: {
        apiKey: string;
        embeddingModel?: string;
    };
}
export declare class VectorStore {
    private config;
    private pinecone?;
    private pineconeIndex?;
    private supabase?;
    private openai;
    private embeddingModel;
    constructor(config: VectorStoreConfig);
    initialize(): Promise<void>;
    generateEmbedding(text: string): Promise<number[]>;
    upsert(documents: VectorDocument[]): Promise<void>;
    search(query: string, topK?: number): Promise<VectorSearchResult[]>;
    delete(ids: string[]): Promise<void>;
}
export default VectorStore;
