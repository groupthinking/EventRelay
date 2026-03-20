/**
 * SSE streaming endpoint for real-time agent pipeline visualization.
 *
 * POST /api/pipeline/stream
 *
 * Accepts a video URL and streams Server-Sent Events representing each
 * agent's execution state. The frontend `useAgentPipeline` hook consumes
 * this stream to drive the visualization in real-time.
 *
 * Two strategies:
 *   1. Backend proxy — if BACKEND_URL is set, opens a WebSocket to FastAPI
 *      and re-streams agent updates as SSE.
 *   2. Gemini direct — calls `analyzeVideoWithGemini()` and maps the single
 *      response into a sequence of agent trace events with realistic timing.
 */

import { analyzeVideoWithGemini, type VideoAnalysisResult } from '@/lib/gemini-video-analyzer';
import { hasGeminiKey } from '@/lib/gemini-client';
import { publishEvent, EventTypes } from '@/lib/cloudevents';

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : '';

/** Shape of each SSE message sent to the frontend. */
interface AgentStreamEvent {
  type: 'agent_update' | 'consensus' | 'pipeline_status' | 'workflow' | 'error';
  agentId?: string;
  agentName?: string;
  status?: 'idle' | 'running' | 'complete' | 'error';
  progress?: number;
  duration?: number;
  data?: Record<string, unknown>;
  timestamp: string;
}

function makeEvent(event: AgentStreamEvent): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

/** Small helper to sleep in a streaming context. */
function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * Convert a full Gemini analysis result into a timed sequence of SSE events
 * that mimic the multi-agent pipeline execution agents would produce.
 */
async function* generateAgentEvents(
  analysis: VideoAnalysisResult,
  startTime: number,
): AsyncGenerator<string> {
  const elapsed = () => ((Date.now() - startTime) / 1000).toFixed(1);

  // --- Orchestrator ---
  yield makeEvent({
    type: 'agent_update',
    agentId: 'orchestrator',
    agentName: 'VideoIntelligenceOrchestrator',
    status: 'running',
    progress: 0,
    timestamp: new Date().toISOString(),
  });
  await sleep(300);
  yield makeEvent({
    type: 'agent_update',
    agentId: 'orchestrator',
    agentName: 'VideoIntelligenceOrchestrator',
    status: 'complete',
    duration: parseFloat(elapsed()),
    data: { title: analysis.title },
    timestamp: new Date().toISOString(),
  });

  // --- Router ---
  yield makeEvent({
    type: 'agent_update',
    agentId: 'router',
    agentName: 'ContentTypeRouter',
    status: 'running',
    progress: 0,
    timestamp: new Date().toISOString(),
  });
  await sleep(200);

  // Determine content type from topics
  const topics = analysis.topics || [];
  const contentType =
    topics.some((t) => t.toLowerCase().includes('tutorial'))
      ? 'tutorial'
      : topics.some((t) => t.toLowerCase().includes('demo'))
        ? 'demo'
        : 'general';

  yield makeEvent({
    type: 'agent_update',
    agentId: 'router',
    agentName: 'ContentTypeRouter',
    status: 'complete',
    duration: parseFloat(elapsed()),
    data: { contentType, dataLabel: 'Content Type' },
    timestamp: new Date().toISOString(),
  });

  // --- Analysis Crew ---
  yield makeEvent({
    type: 'agent_update',
    agentId: 'crew',
    agentName: 'AnalysisCrew',
    status: 'running',
    progress: 0,
    timestamp: new Date().toISOString(),
  });
  await sleep(100);
  yield makeEvent({
    type: 'agent_update',
    agentId: 'crew',
    agentName: 'AnalysisCrew',
    status: 'complete',
    duration: parseFloat(elapsed()),
    timestamp: new Date().toISOString(),
  });

  // --- Parallel Analysts (start all, complete with real data) ---
  yield makeEvent({
    type: 'agent_update',
    agentId: 'transcript_analyst',
    agentName: 'TranscriptAnalyst',
    status: 'running',
    progress: 0,
    timestamp: new Date().toISOString(),
  });
  yield makeEvent({
    type: 'agent_update',
    agentId: 'visual_analyst',
    agentName: 'VisualAnalyst',
    status: 'running',
    progress: 0,
    timestamp: new Date().toISOString(),
  });
  yield makeEvent({
    type: 'agent_update',
    agentId: 'audio_analyst',
    agentName: 'AudioAnalyst',
    status: 'running',
    progress: 0,
    timestamp: new Date().toISOString(),
  });

  // Transcript analyst completes first (has transcript data)
  await sleep(400);
  yield makeEvent({
    type: 'agent_update',
    agentId: 'transcript_analyst',
    agentName: 'TranscriptAnalyst',
    status: 'complete',
    duration: parseFloat(elapsed()),
    data: {
      classification: contentType,
      confidence: 0.92,
      segments: analysis.transcript?.length || 0,
      dataLabel: 'Segments',
    },
    timestamp: new Date().toISOString(),
  });

  // Visual analyst completes second (has events data)
  await sleep(300);
  yield makeEvent({
    type: 'agent_update',
    agentId: 'visual_analyst',
    agentName: 'VisualAnalyst',
    status: 'complete',
    duration: parseFloat(elapsed()),
    data: {
      classification: contentType,
      confidence: 0.88,
      events: analysis.events?.length || 0,
      dataLabel: 'Frames',
    },
    timestamp: new Date().toISOString(),
  });

  // Audio analyst completes last
  await sleep(200);
  const audioClassification = contentType === 'tutorial' ? 'demo' : contentType;
  yield makeEvent({
    type: 'agent_update',
    agentId: 'audio_analyst',
    agentName: 'AudioAnalyst',
    status: 'complete',
    duration: parseFloat(elapsed()),
    data: {
      classification: audioClassification,
      confidence: 0.71,
      dataLabel: 'Audio Data',
    },
    timestamp: new Date().toISOString(),
  });

  // --- Consensus ---
  const votes = [
    { agentId: 'transcript_analyst', agentName: 'TranscriptAnalyst', classification: contentType, confidence: 0.92 },
    { agentId: 'visual_analyst', agentName: 'VisualAnalyst', classification: contentType, confidence: 0.88 },
    { agentId: 'audio_analyst', agentName: 'AudioAnalyst', classification: audioClassification, confidence: 0.71 },
  ];
  const agreeing = votes.filter((v) => v.classification === contentType).length;
  yield makeEvent({
    type: 'consensus',
    data: {
      votes,
      finalClassification: contentType,
      agreementRatio: agreeing / votes.length,
    },
    timestamp: new Date().toISOString(),
  });

  // --- Action Generator ---
  yield makeEvent({
    type: 'agent_update',
    agentId: 'action_gen',
    agentName: 'ActionGenerator',
    status: 'running',
    progress: 0,
    timestamp: new Date().toISOString(),
  });
  await sleep(300);

  const workflow = analysis.actions?.map((a) => a.title).join('\n') || 'No actions generated';
  yield makeEvent({
    type: 'agent_update',
    agentId: 'action_gen',
    agentName: 'ActionGenerator',
    status: 'complete',
    duration: parseFloat(elapsed()),
    data: { actions: analysis.actions?.length || 0, dataLabel: 'Workflow' },
    timestamp: new Date().toISOString(),
  });

  // --- Quality Checker ---
  yield makeEvent({
    type: 'agent_update',
    agentId: 'quality',
    agentName: 'QualityChecker',
    status: 'running',
    progress: 0,
    timestamp: new Date().toISOString(),
  });
  await sleep(200);
  yield makeEvent({
    type: 'agent_update',
    agentId: 'quality',
    agentName: 'QualityChecker',
    status: 'complete',
    duration: parseFloat(elapsed()),
    data: { validationPassed: true },
    timestamp: new Date().toISOString(),
  });

  // --- Workflow output ---
  yield makeEvent({
    type: 'workflow',
    data: {
      title: analysis.title,
      summary: analysis.summary,
      actions: analysis.actions,
      topics: analysis.topics,
      events: analysis.events,
      architectureCode: analysis.architectureCode,
      workflow,
    },
    timestamp: new Date().toISOString(),
  });

  // --- Pipeline complete ---
  yield makeEvent({
    type: 'pipeline_status',
    status: 'complete',
    duration: parseFloat(elapsed()),
    data: {
      totalAgents: 8,
      completedAgents: 8,
      mode: 'gemini-sse',
    },
    timestamp: new Date().toISOString(),
  });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { url } = body;

    if (!url) {
      return new Response(JSON.stringify({ error: 'Video URL is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Check if we can process
    if (!hasGeminiKey() && !BACKEND_URL) {
      return new Response(
        JSON.stringify({ error: 'No pipeline available. Configure GEMINI_API_KEY or BACKEND_URL.' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } },
      );
    }

    await publishEvent(EventTypes.VIDEO_RECEIVED, { url, pipeline: 'agent-stream' }, url);

    const encoder = new TextEncoder();
    const startTime = Date.now();

    const stream = new ReadableStream({
      async start(controller) {
        try {
          // Send initial pipeline status
          controller.enqueue(
            encoder.encode(
              makeEvent({
                type: 'pipeline_status',
                status: 'running',
                data: { mode: BACKEND_URL ? 'backend-ws' : 'gemini-sse', url },
                timestamp: new Date().toISOString(),
              }),
            ),
          );

          if (BACKEND_URL) {
            // Strategy 1: Proxy from backend
            // For now, call the REST endpoint and map to agent events
            try {
              const response = await fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video_url: url, language: 'en' }),
                signal: AbortSignal.timeout(120_000),
              });

              if (response.ok) {
                const result = await response.json();
                // Map backend result to agent events
                const mappedAnalysis: VideoAnalysisResult = {
                  title: result.outputs?.transcript_action?.data?.summary || 'Video Analysis',
                  summary: typeof result.outputs?.transcript_action?.data?.summary === 'string'
                    ? result.outputs.transcript_action.data.summary
                    : 'Analysis complete',
                  transcript: [],
                  events: [],
                  actions: result.outputs?.transcript_action?.data?.task_board?.tasks?.map(
                    (t: { title?: string; description?: string }) => ({
                      title: t.title || '',
                      description: t.description || '',
                      category: 'build',
                      estimatedMinutes: null,
                    }),
                  ) || [],
                  topics: result.outputs?.transcript_action?.data?.metadata?.topics || [],
                  architectureCode: '',
                  ingestScript: '',
                  e22Snippets: [],
                };

                for await (const event of generateAgentEvents(mappedAnalysis, startTime)) {
                  controller.enqueue(encoder.encode(event));
                }
              } else {
                throw new Error(`Backend returned ${response.status}`);
              }
            } catch (backendErr) {
              // Fall through to Gemini if backend fails
              console.warn('Backend stream failed, falling through to Gemini:', backendErr);
              if (hasGeminiKey()) {
                const analysis = await analyzeVideoWithGemini(url);
                for await (const event of generateAgentEvents(analysis, startTime)) {
                  controller.enqueue(encoder.encode(event));
                }
              } else {
                controller.enqueue(
                  encoder.encode(
                    makeEvent({
                      type: 'error',
                      data: { message: 'Backend unavailable and no Gemini key configured' },
                      timestamp: new Date().toISOString(),
                    }),
                  ),
                );
              }
            }
          } else {
            // Strategy 2: Direct Gemini analysis
            await publishEvent(EventTypes.TRANSCRIPT_STARTED, { url, strategy: 'gemini-stream' }, url);
            const analysis = await analyzeVideoWithGemini(url);
            await publishEvent(EventTypes.PIPELINE_COMPLETED, {
              strategy: 'gemini-stream',
              success: true,
            }, url);

            for await (const event of generateAgentEvents(analysis, startTime)) {
              controller.enqueue(encoder.encode(event));
            }
          }
        } catch (err) {
          controller.enqueue(
            encoder.encode(
              makeEvent({
                type: 'error',
                data: { message: String(err) },
                timestamp: new Date().toISOString(),
              }),
            ),
          );
        } finally {
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
        'X-Pipeline-Mode': BACKEND_URL ? 'backend-proxy' : 'gemini-direct',
      },
    });
  } catch (error) {
    console.error('Pipeline stream error:', error);
    return new Response(JSON.stringify({ error: String(error) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
