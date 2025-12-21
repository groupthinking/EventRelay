import { describe, it, expect, vi, beforeEach } from 'vitest';
import { VectorService } from './VectorService';

describe('VectorService', () => {
    let mockEnv: any;
    let service: VectorService;

    beforeEach(() => {
        mockEnv = {
            AI: {
                run: vi.fn()
            },
            VECTORIZE: {
                upsert: vi.fn(),
                query: vi.fn()
            }
        };
        service = new VectorService(mockEnv);
    });

    it('generateEmbeddings should return vectors', async () => {
        const mockEmbedding = [[0.1, 0.2, 0.3]];
        mockEnv.AI.run.mockResolvedValue({ data: mockEmbedding });

        const result = await service.generateEmbeddings('test');
        expect(result).toEqual(mockEmbedding);
        expect(mockEnv.AI.run).toHaveBeenCalledWith('@cf/baai/bge-base-en-v1.5', { text: 'test' });
    });

    it('insertVectors should call upsert', async () => {
        const vectors = [{ id: '1', values: [0.1] }];
        await service.insertVectors(vectors);
        expect(mockEnv.VECTORIZE.upsert).toHaveBeenCalledWith(vectors);
    });

    it('search should generate embedding and query', async () => {
        const mockEmbedding = [[0.1]];
        mockEnv.AI.run.mockResolvedValue({ data: mockEmbedding });
        mockEnv.VECTORIZE.query.mockResolvedValue({ matches: [] });

        await service.search('query', 3);

        expect(mockEnv.AI.run).toHaveBeenCalledWith('@cf/baai/bge-base-en-v1.5', { text: 'query' });
        expect(mockEnv.VECTORIZE.query).toHaveBeenCalledWith([0.1], { topK: 3, returnMetadata: true });
    });
});
