import { Pinecone, Index, RecordMetadata } from '@pinecone-database/pinecone';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import OpenAI from 'openai';

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

export class VectorStore {
  private config: VectorStoreConfig;
  private pinecone?: Pinecone;
  private pineconeIndex?: Index<RecordMetadata>;
  private supabase?: SupabaseClient;
  private openai: OpenAI;
  private embeddingModel: string;

  constructor(config: VectorStoreConfig) {
    this.config = config;
    this.openai = new OpenAI({ apiKey: config.openai.apiKey });
    this.embeddingModel = config.openai.embeddingModel || 'text-embedding-3-small';
  }

  async initialize(): Promise<void> {
    if (this.config.provider === 'pinecone' && this.config.pinecone) {
      this.pinecone = new Pinecone({ apiKey: this.config.pinecone.apiKey });
      this.pineconeIndex = this.pinecone.index(this.config.pinecone.indexName);
    } else if (this.config.provider === 'supabase' && this.config.supabase) {
      this.supabase = createClient(
        this.config.supabase.url,
        this.config.supabase.anonKey
      );
    }
  }

  async generateEmbedding(text: string): Promise<number[]> {
    const response = await this.openai.embeddings.create({
      model: this.embeddingModel,
      input: text,
    });
    const firstData = response.data[0];
    if (!firstData) {
      throw new Error('No embedding data returned');
    }
    return firstData.embedding;
  }

  async upsert(documents: VectorDocument[]): Promise<void> {
    const docsWithEmbeddings = await Promise.all(
      documents.map(async (doc) => ({
        ...doc,
        embedding: doc.embedding || (await this.generateEmbedding(doc.content)),
      }))
    );

    if (this.config.provider === 'pinecone' && this.pineconeIndex) {
      await this.pineconeIndex.upsert(
        docsWithEmbeddings.map((doc) => ({
          id: doc.id,
          values: doc.embedding!,
          metadata: { content: doc.content, ...doc.metadata },
        }))
      );
    } else if (this.config.provider === 'supabase' && this.supabase) {
      const tableName = this.config.supabase!.tableName;
      for (const doc of docsWithEmbeddings) {
        await this.supabase.from(tableName).upsert({
          id: doc.id,
          content: doc.content,
          embedding: doc.embedding,
          metadata: doc.metadata,
        });
      }
    }
  }

  async search(query: string, topK: number = 10): Promise<VectorSearchResult[]> {
    const queryEmbedding = await this.generateEmbedding(query);

    if (this.config.provider === 'pinecone' && this.pineconeIndex) {
      const results = await this.pineconeIndex.query({
        vector: queryEmbedding,
        topK,
        includeMetadata: true,
      });

      return (results.matches || []).map((match) => ({
        id: match.id,
        score: match.score || 0,
        content: (match.metadata?.content as string) || '',
        metadata: match.metadata as Record<string, unknown>,
      }));
    } else if (this.config.provider === 'supabase' && this.supabase) {
      const { data, error } = await this.supabase.rpc('match_documents', {
        query_embedding: queryEmbedding,
        match_threshold: 0.5,
        match_count: topK,
      });

      if (error) throw error;

      return (data || []).map((row: { id: string; similarity: number; content: string; metadata: Record<string, unknown> }) => ({
        id: row.id,
        score: row.similarity,
        content: row.content,
        metadata: row.metadata,
      }));
    }

    return [];
  }

  async delete(ids: string[]): Promise<void> {
    if (this.config.provider === 'pinecone' && this.pineconeIndex) {
      await this.pineconeIndex.deleteMany(ids);
    } else if (this.config.provider === 'supabase' && this.supabase) {
      const tableName = this.config.supabase!.tableName;
      await this.supabase.from(tableName).delete().in('id', ids);
    }
  }
}

export default VectorStore;
