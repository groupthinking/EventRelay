// Workflow implementation using durable execution pattern
// Compatible with Vercel Workflow SDK

interface WorkflowContext {
  input: {
    dataUrl: string;
    storageUrl: string;
  };
}

interface StepResult {
  rawData?: unknown[];
  timestamp?: number;
  transformed?: unknown[];
  count?: number;
  success?: boolean;
  itemsProcessed?: number;
  completedAt?: string;
}

/**
 * Durable data processing workflow
 * Survives deployments, crashes, and long-running operations
 */
export async function dataProcessingWorkflow(context: WorkflowContext): Promise<StepResult> {
  // Step 1: Fetch data
  const fetchResult = await fetchDataStep(context);
  
  // Step 2: Transform data
  const transformResult = await transformDataStep(context, fetchResult);
  
  // Step 3: Store results
  const storeResult = await storeResultsStep(context, transformResult);
  
  return storeResult;
}

async function fetchDataStep(context: WorkflowContext): Promise<StepResult> {
  'use step';
  const response = await fetch(context.input.dataUrl);
  const rawData = await response.json();
  return { rawData, timestamp: Date.now() };
}

async function transformDataStep(_context: WorkflowContext, prevResult: StepResult): Promise<StepResult> {
  'use step';
  const transformed = (prevResult.rawData || []).map((item: unknown) => {
    const typedItem = item as { id: string; value: number };
    return {
      id: typedItem.id,
      value: typedItem.value * 2,
      processed: true
    };
  });
  return { transformed, count: transformed.length };
}

async function storeResultsStep(context: WorkflowContext, prevResult: StepResult): Promise<StepResult> {
  'use step';
  await fetch(context.input.storageUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(prevResult.transformed)
  });
  return {
    success: true,
    itemsProcessed: prevResult.count,
    completedAt: new Date().toISOString()
  };
}

/**
 * Execute the workflow
 */
export async function runDataProcessing(dataUrl: string, storageUrl: string): Promise<StepResult> {
  return await dataProcessingWorkflow({
    input: { dataUrl, storageUrl }
  });
}
