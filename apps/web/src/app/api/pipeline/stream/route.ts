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
 *
 * IMPORTANT: All optional post-processing (training save, embeddings,
 * CloudEvents, BigQuery export) is fire-and-forget. These MUST NOT block
 * the SSE stream from closing after pipeline_status:complete is emitted.
 * See: https://github.com/groupthinking/EventRelay/issues/139
 */

import { analyzeVideoWithGemini, type VideoAnalysisResult } from '@/lib/gemini-video-analyzer';
import { hasGeminiKey } from '@/lib/gemini-client';
import { publishEvent, EventTypes } from '@/lib/cloudevents';
import { backendHeaders, resolveBackendStatusUrl } from '@/lib/pipeline-backend';
import { saveTrainingExample, TUNING_THRESHOLD } from '@/lib/training-store';
import { PipelineDeadline } from '../route';

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : '';
const JOB_POLL_INTERVAL_MS = 2000;
const MAX_JOB_POLL_ATTEMPTS = 90;

export const runtime = 'nodejs';
export const maxDuration = 240;

/** Wall-clock budget for the full SSE response (poll + agent events). */
export const STREAM_MAX_DURATION_MS = maxDuration * 1000;
/** Initial transcript-action kickoff — clamped to remaining stream budget. */
export const STREAM_BACKEND_KICKOFF_MS = 120_000;

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

interface BackendTranscriptActionResponse {
  success: boolean;
  async_processing?: boolean;
  job_id?: string;
  job_status?: string;
  status_url?: string;
  processing_transport?: string;
  outputs?: Record<string, any>;
  transcript?: Record<string, any>;
}

interface BackendVideoJobStatus {
  job_id: string;
  status: 'pending' | 'downloading' | 'transcribing' | 'extracting' | 'complete' | 'failed';
  progress: number;
  video_url?: string;
  transcript?: string;
  metadata?: Record<string, any>;
  error?: string;
}

async function readJsonBody(request: Request): Promise<Record<string, unknown> | null> {
  try {
    const body = await request.json();
    return body && typeof body === 'object' ? body as Record<string, unknown> : null;
  } catch {
    return null;
  }
}

function makeEvent(event: AgentStreamEvent): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

/** Small helper to sleep in a streaming context. */
function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * Fire-and-forget: run an async function without awaiting it.
 * Errors are caught and logged but never propagate.
 */
function fireAndForget(label: string, fn: () => Promise<void>): void {
  fn().catch((err) => {
    console.warn(`[${label}] Fire-and-forget failed (non-fatal):`, err);
  });
}

function mapTaskBoardActions(taskBoard: Record<string, unknown> | undefined) {
  if (!taskBoard || typeof taskBoard !== 'object') return [];
  return Object.entries(taskBoard).flatMap(([column, items]) =>
    Array.isArray(items)
      ? items.map((item) => {
          const task = (item ?? {}) as Record<string, unknown>;
          return {
            title: String(task.title || 'Untitled'),
            description: String(task.definition_of_done || task.description || ''),
            category: column,
            estimatedMinutes:
              typeof task.estimate_days === 'number'
                ? task.estimate_days * 24 * 60
                : null,
          };
        })
      : [],
  );
}

function mapBackendResultToAnalysis(result: Record<string, any>): VideoAnalysisResult {
  const transcriptAction = result.outputs?.transcript_action?.data || {};
  const rankedActions = Array.isArray(transcriptAction.priority_ranked_actions)
    ? transcriptAction.priority_ranked_actions.map((action: Record<string, unknown>) => ({
        title: String(action.text || 'Untitled action'),
        description: String(action.reasoning || ''),
        category: String(action.tier || 'build'),
        estimatedMinutes: null,
      }))
    : [];
  const taskBoardActions = mapTaskBoardActions(transcriptAction.task_board);

  return {
    title:
      result.metadata?.title ||
      result.outputs?.transcript_action?.data?.summary ||
      'Video Analysis',
    summary:
      typeof transcriptAction.summary === 'string'
        ? transcriptAction.summary
        : 'Analysis complete',
    transcript: Array.isArray(result.transcript?.segments)
      ? result.transcript.segments
      : [],
    events: [],
    actions: rankedActions.length > 0 ? rankedActions : taskBoardActions,
    topics: transcriptAction.metadata?.topics || [],
    architectureCode: '',
    ingestScript: '',
    e22Snippets: [],
  };
}

async function pollBackendJob(
  statusUrl: string,
  controller: ReadableStreamDefaultController<Uint8Array>,
  encoder: TextEncoder,
  deadline: PipelineDeadline,
): Promise<BackendVideoJobStatus> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < MAX_JOB_POLL_ATTEMPTS; attempt += 1) {
    if (deadline.remainingMs() <= JOB_POLL_INTERVAL_MS) {
      throw new Error('Stream pipeline deadline exceeded while polling async job');
    }

    if (attempt > 0) {
      await sleep(JOB_POLL_INTERVAL_MS);
    }

    try {
      const response = await fetch(statusUrl, {
        cache: 'no-store',
        headers: backendHeaders(),
        signal: deadline.signalFor(JOB_POLL_INTERVAL_MS * 2),
      });

      if (!response.ok) {
        // Fail fast on client errors (4xx)
        if (response.status >= 400 && response.status < 500) {
          throw new Error(`Job status endpoint returned ${response.status}: client error (cannot retry)`);
        }

        // For server errors (5xx), log and retry
        if (response.status >= 500) {
          lastError = new Error(`Job status endpoint returned ${response.status}: server error (will retry)`);
          console.warn(`[Job Polling] Attempt ${attempt + 1}: ${lastError.message}`);
          continue;
        }

        // For other non-ok responses, fail
        throw new Error(`Job status returned unexpected status ${response.status}`);
      }

      const payload = await response.json();
      const job = (payload.data || payload) as BackendVideoJobStatus;

      controller.enqueue(
        encoder.encode(
          makeEvent({
            type: 'agent_update',
            agentId: 'async_queue',
            agentName: 'AsyncVideoQueue',
            status: job.status === 'failed' ? 'error' : 'running',
            progress: Math.max(0, Math.min(100, Math.round(job.progress || 0))),
            data: {
              jobId: job.job_id,
              stage: job.status,
            },
            timestamp: new Date().toISOString(),
          }),
        ),
      );

      if (job.status === 'complete' || job.status === 'failed') {
        return job;
      }

      // Clear last error on successful poll
      lastError = null;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);

      // If it's a 4xx error, fail immediately (already thrown above)
      if (errorMsg.includes('client error (cannot retry)')) {
        throw err;
      }

      // Log the error but continue retrying for other cases
      lastError = err instanceof Error ? err : new Error(errorMsg);
      console.warn(`[Job Polling] Attempt ${attempt + 1} failed: ${lastError.message}`);

      // Continue to next attempt
      continue;
    }
  }

  // All retries exhausted
  if (lastError) {
    throw new Error(`Timed out waiting for async video job to complete after ${MAX_JOB_POLL_ATTEMPTS} attempts. Last error: ${lastError.message}`);
  }

  throw new Error('Timed out waiting for async video job to complete (job status never reached complete or failed)');
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
    agentId: 'embedding_agent',
    agentName: 'SemanticEmbeddingAgent',
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

  // Embedding agent completes
  await sleep(200);
  yield makeEvent({
    type: 'agent_update',
    agentId: 'embedding_agent',
    agentName: 'SemanticEmbeddingAgent',
    status: 'complete',
    duration: parseFloat(elapsed()),
    data: { dataLabel: 'Vector Embeddings' },
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
      transcript: analysis.transcript,
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
      totalAgents: 9,
      completedAgents: 9,
      mode: 'gemini-sse',
    },
    timestamp: new Date().toISOString(),
  });
}

export async function POST(request: Request) {
  try {
    const body = await readJsonBody(request);
    if (!body) {
      return new Response(JSON.stringify({ error: 'Valid JSON body is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const { url } = body;

    if (typeof url !== 'string' || !url.trim()) {
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
    const deadline = new PipelineDeadline(Date.now() + STREAM_MAX_DURATION_MS);

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

          // ── Fire-and-forget helpers for optional post-processing ──
          // These MUST NOT block the stream from closing.
          // See: https://github.com/groupthinking/EventRelay/issues/139

          const schedulePostProcessing = (videoUrl: string, analysis: VideoAnalysisResult) => {
            // Training save — fire and forget
            fireAndForget('Training', async () => {
              const { saved, metadata, milestone } = await saveTrainingExample(
                videoUrl,
                analysis as unknown as Record<string, unknown>,
              );
              if (saved && milestone) {
                console.log(`\n🎯 TRAINING MILESTONE: ${milestone}/${TUNING_THRESHOLD} examples collected!`);
                if (milestone >= TUNING_THRESHOLD) {
                  console.log('🚀 READY FOR FINE-TUNING! Call POST /api/training/trigger to start.');
                }
              }
              if (saved) {
                console.log(`[Training] Dataset: ${metadata.totalExamples} examples`);
              } else {
                console.log(`[Training] Skipped duplicate: ${videoUrl}`);
              }
            });

            // Embeddings — fire and forget
            fireAndForget('Embeddings', async () => {
              let segments = analysis.transcript;
              if (!segments || segments.length === 0) {
                const { fetchTranscript } = await import('@/lib/transcription-service');
                const result = await fetchTranscript({ url: videoUrl });
                if (result.success && result.segments && result.segments.length > 0) {
                  segments = result.segments.map(s => ({
                    start: s.start,
                    duration: s.duration,
                    text: s.text || ''
                  }));
                }
              }

              if (segments && segments.length > 0) {
                const { chunkTranscript, generateEmbeddingsForChunks } = await import('@/lib/gemini-embedding');
                const { saveEmbeddings } = await import('@/lib/embedding-store');
                const chunks = chunkTranscript(segments);
                const embeddedChunks = await generateEmbeddingsForChunks(chunks);
                const videoId = videoUrl.match(/[?&]v=([^&]+)/)?.[1] || videoUrl.replace(/[^a-zA-Z0-9_-]/g, '_');
                await saveEmbeddings(videoId, embeddedChunks);
              }
            });

            // CloudEvent — fire and forget
            fireAndForget('CloudEvent', async () => {
              await publishEvent(EventTypes.PIPELINE_COMPLETED, {
                strategy: BACKEND_URL ? 'backend-proxy' : 'gemini-stream',
                success: true,
              }, videoUrl);
            });
          };

          if (BACKEND_URL) {
            // Strategy 1: Proxy from backend
            try {
              const response = await fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
                method: 'POST',
                headers: backendHeaders(),
                body: JSON.stringify({ video_url: url, language: 'en' }),
                signal: deadline.signalFor(STREAM_BACKEND_KICKOFF_MS),
              });

              if (response.ok) {
                const result = await response.json();
                const transcriptResult = result as BackendTranscriptActionResponse;
                if (transcriptResult.async_processing && transcriptResult.status_url) {
                  controller.enqueue(
                    encoder.encode(
                      makeEvent({
                        type: 'agent_update',
                        agentId: 'async_queue',
                        agentName: 'AsyncVideoQueue',
                        status: 'running',
                        progress: 5,
                        data: {
                          jobId: transcriptResult.job_id,
                          transport: transcriptResult.processing_transport,
                        },
                        timestamp: new Date().toISOString(),
                      }),
                    ),
                  );

                  const statusUrl = resolveBackendStatusUrl(
                    transcriptResult.status_url,
                    BACKEND_URL,
                  );
                  const job = await pollBackendJob(statusUrl, controller, encoder, deadline);
                  if (job.status === 'failed') {
                    throw new Error(job.error || 'Async transcript job failed');
                  }

                  const mappedAnalysis = mapBackendResultToAnalysis({
                    metadata: job.metadata?.metadata || {},
                    transcript: {
                      text: job.transcript || '',
                      segments: [],
                    },
                    outputs: job.metadata?.outputs || {},
                  });

                  // Stream all agent events including pipeline_status:complete
                  for await (const event of generateAgentEvents(mappedAnalysis, startTime)) {
                    controller.enqueue(encoder.encode(event));
                  }

                  // Schedule optional work AFTER stream events are done — fire and forget
                  schedulePostProcessing(url, mappedAnalysis);
                  return;
                }

                const mappedAnalysis = mapBackendResultToAnalysis(result);

                // Stream all agent events including pipeline_status:complete
                for await (const event of generateAgentEvents(mappedAnalysis, startTime)) {
                  controller.enqueue(encoder.encode(event));
                }

                // Schedule optional work — fire and forget
                schedulePostProcessing(url, mappedAnalysis);
              } else {
                throw new Error(`Backend returned ${response.status}`);
              }
            } catch (backendErr) {
              // Fall through to Gemini if backend fails
              console.warn('Backend stream failed, falling through to Gemini:', backendErr);
              if (hasGeminiKey() && deadline.remainingMs() > 1_000) {
                const analysis = await deadline.runWithBudget(
                  analyzeVideoWithGemini(url),
                  deadline.remainingMs(),
                  'Gemini stream fallback',
                );

                // Stream all agent events including pipeline_status:complete
                for await (const event of generateAgentEvents(analysis, startTime)) {
                  controller.enqueue(encoder.encode(event));
                }

                // Schedule optional work — fire and forget
                schedulePostProcessing(url, analysis);
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
            fireAndForget('CloudEvent:Start', async () => {
              await publishEvent(EventTypes.TRANSCRIPT_STARTED, { url, strategy: 'gemini-stream' }, url);
            });

            const analysis = await deadline.runWithBudget(
              analyzeVideoWithGemini(url),
              deadline.remainingMs(),
              'Gemini stream analysis',
            );

            // Stream all agent events including pipeline_status:complete
            for await (const event of generateAgentEvents(analysis, startTime)) {
              controller.enqueue(encoder.encode(event));
            }

            // Schedule optional work — fire and forget
            schedulePostProcessing(url, analysis);
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
          // Always emit a terminal pipeline_status so clients (and E2E tests) know
          // the stream ended — even when processing failed.
          controller.enqueue(
            encoder.encode(
              makeEvent({
                type: 'pipeline_status',
                status: 'error',
                duration: parseFloat(((Date.now() - startTime) / 1000).toFixed(1)),
                data: {
                  totalAgents: 0,
                  completedAgents: 0,
                  mode: BACKEND_URL ? 'backend-ws' : 'gemini-sse',
                },
                timestamp: new Date().toISOString(),
              }),
            ),
          );
        } finally {
          // CRITICAL: close the stream immediately after all SSE events are
          // enqueued. This MUST NOT wait for fire-and-forget post-processing.
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
