import { supabase } from '../lib/supabase';

// Placeholder adapter imports (to be implemented)
// import { runGithubAdapter } from './adapters/github';
// import { runDriveAdapter } from './adapters/drive';
// import { runAbacusAdapter } from './adapters/abacus';
// import { runFileParsers } from './adapters/files';

export type OrchestrationSummary = {
  startedAt: string;
  endedAt: string;
  adapters: { name: string; records: number; errors: string[] }[];
  embeddingTriggered: boolean;
  totalRecords: number;
  totalErrors: number;
};

export async function orchestrate(triggerSource: string = 'manual'): Promise<OrchestrationSummary> {
  const startedAt = new Date().toISOString();
  const adapters = [
    { name: 'github', fn: async () => ({ records: 0, errors: [] }) },
    { name: 'drive', fn: async () => ({ records: 0, errors: [] }) },
    { name: 'abacus', fn: async () => ({ records: 0, errors: [] }) },
    { name: 'files', fn: async () => ({ records: 0, errors: [] }) },
  ];
  let totalRecords = 0;
  let totalErrors = 0;
  const adapterResults: { name: string; records: number; errors: string[] }[] = [];

  for (const adapter of adapters) {
    try {
      const result = await adapter.fn();
      adapterResults.push({ name: adapter.name, records: result.records, errors: result.errors });
      totalRecords += result.records;
      totalErrors += result.errors.length;
    } catch (e: any) {
      adapterResults.push({ name: adapter.name, records: 0, errors: [e.message || String(e)] });
      totalErrors += 1;
    }
  }

  // Trigger embeddings (placeholder)
  let embeddingTriggered = false;
  try {
    // await triggerEmbeddings();
    embeddingTriggered = true;
  } catch (e) {
    embeddingTriggered = false;
  }

  const endedAt = new Date().toISOString();
  const summary: OrchestrationSummary = {
    startedAt,
    endedAt,
    adapters: adapterResults,
    embeddingTriggered,
    totalRecords,
    totalErrors,
  };

  // Log to Supabase mcp_logs table
  await supabase.from('mcp_logs').insert([
    {
      started_at: startedAt,
      ended_at: endedAt,
      trigger_source: triggerSource,
      summary: summary,
    },
  ]);

  return summary;
} 