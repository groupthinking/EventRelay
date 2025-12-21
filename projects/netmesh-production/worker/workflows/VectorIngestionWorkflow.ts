import { WorkflowEntrypoint, WorkflowStep, WorkflowEvent } from 'cloudflare:workers';
import { Env } from '../../index';

type VectorIngestionParams = {
    text: string;
    id?: string;
    metadata?: Record<string, string>;
};

export class VectorIngestionWorkflow extends WorkflowEntrypoint<Env, VectorIngestionParams> {
    async run(event: WorkflowEvent<VectorIngestionParams>, step: WorkflowStep) {
        const { text, id, metadata } = event.payload;

        // Step 1: Generate Embeddings using Workers AI
        const embedding = await step.do('generate-embedding', async () => {
            const response = await this.env.AI.run('@cf/baai/bge-base-en-v1.5', { text: [text] });
            return response.data[0];
        });

        // Step 2: Insert into Vectorize
        await step.do('insert-vector', async () => {
            await this.env.VECTORIZE.upsert([
                {
                    id: id || crypto.randomUUID(),
                    values: embedding,
                    metadata: metadata
                }
            ]);
        });

        return { status: 'success', id };
    }
}
