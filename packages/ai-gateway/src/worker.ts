import { Worker } from '@temporalio/worker';
import * as activities from './activities/competitiveAnalysisActivities';

async function run() {
  // Step 1: Initialize the Temporal Worker
  // The worker connects to the Temporal server and polls the 'ai-agents-task-queue'
  const worker = await Worker.create({
    workflowsPath: require.resolve('./workflows/competitiveAnalysisWorkflow'),
    activities,
    taskQueue: 'ai-agents-task-queue',
  });

  // Step 2: Start accepting tasks
  console.log('Starting Temporal Worker for AI Agents (Gemini Computer Use)...');
  await worker.run();
}

run().catch((err) => {
  console.error('Worker failed to start:', err);
  process.exit(1);
});
