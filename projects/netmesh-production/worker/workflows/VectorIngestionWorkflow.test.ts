import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the module before import
vi.mock('cloudflare:workers', () => {
    return {
        WorkflowEntrypoint: class {
            env: any;
            constructor(ctx: any, env: any) {
                this.env = env;
            }
        },
        WorkflowStep: class { },
        WorkflowEvent: class { },
    };
});

import { VectorIngestionWorkflow } from './VectorIngestionWorkflow';


describe('VectorIngestionWorkflow', () => {
    let mockEnv: any;
    let workflow: VectorIngestionWorkflow;

    beforeEach(() => {
        mockEnv = {
            AI: {
                run: vi.fn(),
            },
            VECTORIZE: {
                upsert: vi.fn(),
            },
        };
        const mockCtx = {
            waitUntil: vi.fn(),
            passThroughOnException: vi.fn(),
            abort: vi.fn(),
        } as any;

        // Mock the WorkflowEntrypoint structure
        workflow = new VectorIngestionWorkflow(mockCtx, mockEnv);
    });

    it('should generate embedding and upsert vector', async () => {
        // Mock AI response
        const mockEmbedding = [[0.1, 0.2, 0.3]];
        mockEnv.AI.run.mockResolvedValue({ data: mockEmbedding });

        // Mock step.do to execute the callback immediately
        const mockStep: any = {
            do: vi.fn().mockImplementation(async (name, callback) => {
                return await callback();
            })
        };

        const payload = { text: 'test text', id: '123' };

        await workflow.run({ payload } as any, mockStep);

        // Verify AI call
        expect(mockEnv.AI.run).toHaveBeenCalledWith('@cf/baai/bge-base-en-v1.5', { text: ['test text'] });

        // Verify Vectorize call
        expect(mockEnv.VECTORIZE.upsert).toHaveBeenCalledWith([
            {
                id: '123',
                values: [0.1, 0.2, 0.3],
                metadata: undefined,
            },
        ]);
    });
});
