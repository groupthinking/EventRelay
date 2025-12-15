import { Hono } from 'hono';
import { AppEnv } from '../../types/appenv';
import { VectorService } from '../../services/ai/VectorService';
import { z } from 'zod';

const vectorRoutes = new Hono<AppEnv>();

// Schema for embedding request
const embedSchema = z.object({
    text: z.string().min(1),
    id: z.string().optional(), // If provided, will store in index
    metadata: z.record(z.any()).optional()
});

// Schema for search request
const searchSchema = z.object({
    query: z.string().min(1),
    topK: z.number().min(1).max(20).default(5)
});

vectorRoutes.post('/embed', async (c) => {
    const body = await c.req.json();
    const result = embedSchema.safeParse(body);

    if (!result.success) {
        return c.json({ error: 'Invalid request', details: result.error }, 400);
    }

    const { text, id, metadata } = result.data;
    const vectorService = new VectorService(c.env);

    try {
        if (id) {
            // Store mode
            await vectorService.embedAndInsert(id, text, metadata);
            return c.json({ success: true, message: `Embedded and stored document ${id}` });
        } else {
            // Generate only mode
            const embeddings = await vectorService.generateEmbeddings(text);
            return c.json({ success: true, embeddings });
        }
    } catch (error: any) {
        console.error('Vector embed error:', error);
        return c.json({ error: error.message }, 500);
    }
});

vectorRoutes.post('/search', async (c) => {
    const body = await c.req.json();
    const result = searchSchema.safeParse(body);

    if (!result.success) {
        return c.json({ error: 'Invalid request', details: result.error }, 400);
    }

    const { query, topK } = result.data;
    const vectorService = new VectorService(c.env);

    try {
        const matches = await vectorService.search(query, topK);
        return c.json({ success: true, matches });
    } catch (error: any) {
        console.error('Vector search error:', error);
        return c.json({ error: error.message }, 500);
    }
});

export { vectorRoutes };
