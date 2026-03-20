import { proxyActivities } from '@temporalio/workflow';
import type * as activities from '../activities/competitiveAnalysisActivities';

// Set up proxy activities with retry policies and timeouts
const proxyOptions = {
  startToCloseTimeout: '10 minutes', // Computer use can take time
  retry: {
    maximumAttempts: 3,
  },
};

const proxyActs = proxyActivities<typeof activities>(proxyOptions);

/**
 * Temporal Workflow: Durable & Reliable Competitive Analysis
 * Uses Gemini Computer Use for executing agentic web tasks.
 */
export async function competitiveAnalysisWorkflow(url: string, videoUrl: string) {
  // 1. Planning (Deterministic)
  // Gemini analyzes the goal and formulates an extraction plan
  const plan = await proxyActs.planTask(url);

  // 2. Durable Async Execution
  // Temporal automatically checkpoints progress here.
  // If the server crashes, it resumes from these exact results.
  const [webData, videoData, searchData] = await Promise.all([
    // Uses Gemini Computer Use to navigate the web and extract content
    proxyActs.extractUrlContent(url),
    // Uses Gemini to process and analyze the video
    proxyActs.analyzeVideo(videoUrl),
    // Uses Gemini Computer Use to search for competitors
    proxyActs.searchCompetitors(url)
  ]);

  // 3. Final Synthesis
  // Gemini synthesizes the structured data into a final report
  return await proxyActs.synthesizeReport({
    plan,
    webData,
    videoData,
    searchData
  });
}
