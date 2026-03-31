import { Client } from '@temporalio/client';
import { competitiveAnalysisWorkflow } from './workflows/competitiveAnalysisWorkflow';

async function run() {
  // Connect to the default localhost Temporal server
  const client = new Client();

  console.log('Starting competitiveAnalysisWorkflow...');
  
  const handle = await client.workflow.start(competitiveAnalysisWorkflow, {
    args: ['https://example-competitor.com', 'https://youtube.com/watch?v=example'],
    taskQueue: 'ai-agents-task-queue',
    workflowId: 'comp-analysis-' + Date.now(), // Generate a unique ID
  });

  console.log(`Started workflow with ID: ${handle.workflowId}`);

  // Wait for the workflow to complete
  const result = await handle.result();
  console.log('Workflow Result:', result);
}

run().catch((err) => {
  console.error('Failed to run workflow', err);
  process.exit(1);
});
