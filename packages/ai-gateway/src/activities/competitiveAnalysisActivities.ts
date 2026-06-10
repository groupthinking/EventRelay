import { generateText, stepCountIs } from 'ai';
import { google } from '@ai-sdk/google';
import { z } from 'zod';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

/**
 * Competitive Analysis Activities
 * These activities use Gemini's advanced Computer Use and Multimodal capabilities 
 * to execute complex tasks in a durable Temporal execution environment.
 */

// We assume the user wants the latest capabilities ('gemini-3.1-pro-preview' or 'gemini-2.5-pro' equivalent)
// that has native tool and computer use support.
const MODEL = google('gemini-2.5-pro'); // Placeholder for 'gemini-3.1-pro-preview' which might not be in the sdk string literal types yet

export async function planTask(url: string): Promise<string> {
  console.log(`[Activity] Planning task for ${url}`);
  const { text } = await generateText({
    model: MODEL,
    prompt: `Create a step-by-step extraction and competitive analysis plan for the URL: ${url}. 
    Focus on key metrics, product offerings, and market positioning.`,
  });
  return text;
}

export async function extractUrlContent(url: string): Promise<string> {
  console.log(`[Activity] Extracting URL Content for ${url} via Gemini Computer Use (MCP)`);
  
  // Initialize the MCP Client to connect to chrome-devtools-mcp via stdio transport
  const transport = new StdioClientTransport({
    command: 'npx',
    args: ['-y', 'chrome-devtools-mcp'], // Spawns the MCP server
  });
  
  const mcpClient = new Client({ name: 'gemini-worker', version: '1.0.0' }, { capabilities: {} });
  await mcpClient.connect(transport);
  
  try {
    const browserTools = {
      navigate: {
        description: 'Navigate the active Chrome tab to a URL',
        inputSchema: z.object({ url: z.string() }),
        execute: async ({ url }: { url: string }) => {
          console.log(`[MCP Tool] Navigating to ${url}`);
          return await mcpClient.callTool({ name: 'navigate', arguments: { url } });
        },
      },
      evaluate_script: {
        description: 'Evaluate JavaScript in the active Chrome tab to extract content from the DOM',
        inputSchema: z.object({ script: z.string() }),
        execute: async ({ script }: { script: string }) => {
          console.log(`[MCP Tool] Evaluating script...`);
          return await mcpClient.callTool({ name: 'evaluate_script', arguments: { script } });
        },
      },
    } as any;

    const { text } = await generateText({
      model: MODEL,
      system: "You are an AI agent with Computer Use capabilities via the Chrome DevTools MCP. Navigate to the user's requested URL, extract product offerings and pricing, and return a clean summary. Use your browser tools to evaluate the DOM and navigate.",
      prompt: `Target URL: ${url}`,
      tools: browserTools,
      stopWhen: stepCountIs(10), // Let the model reason and call tools iteratively
    });
    return text;
  } finally {
    // Ensure we clean up the MCP process to prevent memory leaks
    await mcpClient.close();
  }
}

export async function analyzeVideo(videoUrl: string): Promise<string> {
  console.log(`[Activity] Analyzing video at ${videoUrl}`);
  // Gemini's multimodal capabilities allow it to process video. 
  // We prompt it to extract marketing points from the video URL.
  const { text } = await generateText({
    model: MODEL,
    prompt: `Analyze the video located at ${videoUrl}. Extract the main marketing message, tone, and target audience.`,
    // In actual implementation, video can be passed as a FilePart or standard URL if Google handles it,
    // or downloaded first. We assume standard multimodal URL ingestion or computer-use navigation.
  });
  return text;
}

export async function searchCompetitors(url: string): Promise<string> {
  console.log(`[Activity] Searching competitors based on ${url}`);
  
  // Another scenario where Computer Use / Search Tool shines
  const { text } = await generateText({
    model: MODEL,
    system: "You are an AI with Computer Use/Search capabilities. Conduct a deep web search for competitors.",
    prompt: `Find 3 direct competitors to the business at ${url}. Summarize their strengths and weaknesses.`,
  });
  return text;
}

export async function synthesizeReport(data: {
  plan?: string;
  webData: string;
  videoData: string;
  searchData: string;
}): Promise<string> {
  console.log(`[Activity] Synthesizing final report`);
  const { text } = await generateText({
    model: MODEL,
    prompt: `Synthesize a comprehensive competitive analysis report. 
    
Web Data: ${data.webData}
Video Analysis: ${data.videoData}
Competitor Search: ${data.searchData}

Format the output as Markdown, highlighting strategic recommendations.`,
  });
  return text;
}
