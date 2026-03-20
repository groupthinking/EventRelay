"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.orchestrate = orchestrate;
const supabase_1 = require("../lib/supabase");
async function orchestrate(triggerSource = 'manual') {
    const startedAt = new Date().toISOString();
    const adapters = [
        { name: 'github', fn: async () => ({ records: 0, errors: [] }) },
        { name: 'drive', fn: async () => ({ records: 0, errors: [] }) },
        { name: 'abacus', fn: async () => ({ records: 0, errors: [] }) },
        { name: 'files', fn: async () => ({ records: 0, errors: [] }) },
    ];
    let totalRecords = 0;
    let totalErrors = 0;
    const adapterResults = [];
    for (const adapter of adapters) {
        try {
            const result = await adapter.fn();
            adapterResults.push({ name: adapter.name, records: result.records, errors: result.errors });
            totalRecords += result.records;
            totalErrors += result.errors.length;
        }
        catch (e) {
            adapterResults.push({ name: adapter.name, records: 0, errors: [e.message || String(e)] });
            totalErrors += 1;
        }
    }
    // Trigger embeddings (placeholder)
    let embeddingTriggered = false;
    try {
        // await triggerEmbeddings();
        embeddingTriggered = true;
    }
    catch (e) {
        embeddingTriggered = false;
    }
    const endedAt = new Date().toISOString();
    const summary = {
        startedAt,
        endedAt,
        adapters: adapterResults,
        embeddingTriggered,
        totalRecords,
        totalErrors,
    };
    // Log to Supabase mcp_logs table
    await supabase_1.supabase.from('mcp_logs').insert([
        {
            started_at: startedAt,
            ended_at: endedAt,
            trigger_source: triggerSource,
            summary: summary,
        },
    ]);
    return summary;
}
//# sourceMappingURL=orchestrator.js.map