"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.VectorStore = void 0;
const pinecone_1 = require("@pinecone-database/pinecone");
const supabase_js_1 = require("@supabase/supabase-js");
const openai_1 = __importDefault(require("openai"));
class VectorStore {
    config;
    pinecone;
    pineconeIndex;
    supabase;
    openai;
    embeddingModel;
    constructor(config) {
        this.config = config;
        this.openai = new openai_1.default({ apiKey: config.openai.apiKey });
        this.embeddingModel = config.openai.embeddingModel || 'text-embedding-3-small';
    }
    async initialize() {
        if (this.config.provider === 'pinecone' && this.config.pinecone) {
            this.pinecone = new pinecone_1.Pinecone({ apiKey: this.config.pinecone.apiKey });
            this.pineconeIndex = this.pinecone.index(this.config.pinecone.indexName);
        }
        else if (this.config.provider === 'supabase' && this.config.supabase) {
            this.supabase = (0, supabase_js_1.createClient)(this.config.supabase.url, this.config.supabase.anonKey);
        }
    }
    async generateEmbedding(text) {
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
    async upsert(documents) {
        const docsWithEmbeddings = await Promise.all(documents.map(async (doc) => ({
            ...doc,
            embedding: doc.embedding || (await this.generateEmbedding(doc.content)),
        })));
        if (this.config.provider === 'pinecone' && this.pineconeIndex) {
            await this.pineconeIndex.upsert(docsWithEmbeddings.map((doc) => ({
                id: doc.id,
                values: doc.embedding,
                metadata: { content: doc.content, ...doc.metadata },
            })));
        }
        else if (this.config.provider === 'supabase' && this.supabase) {
            const tableName = this.config.supabase.tableName;
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
    async search(query, topK = 10) {
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
                content: match.metadata?.content || '',
                metadata: match.metadata,
            }));
        }
        else if (this.config.provider === 'supabase' && this.supabase) {
            const { data, error } = await this.supabase.rpc('match_documents', {
                query_embedding: queryEmbedding,
                match_threshold: 0.5,
                match_count: topK,
            });
            if (error)
                throw error;
            return (data || []).map((row) => ({
                id: row.id,
                score: row.similarity,
                content: row.content,
                metadata: row.metadata,
            }));
        }
        return [];
    }
    async delete(ids) {
        if (this.config.provider === 'pinecone' && this.pineconeIndex) {
            await this.pineconeIndex.deleteMany(ids);
        }
        else if (this.config.provider === 'supabase' && this.supabase) {
            const tableName = this.config.supabase.tableName;
            await this.supabase.from(tableName).delete().in('id', ids);
        }
    }
}
exports.VectorStore = VectorStore;
exports.default = VectorStore;
//# sourceMappingURL=index.js.map