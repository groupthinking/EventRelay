import { NextResponse } from 'next/server';
import { publishEvent, EventTypes } from '@/lib/cloudevents';
import { analyzeVideoWithGemini } from '@/lib/gemini-video-analyzer';
import { hasGeminiKey } from '@/lib/gemini-client';
import { saveTrainingExample } from '@/lib/training-store';
import { fetchTranscript } from '@/lib/transcription-service';
import { extractEvents, type ExtractionData } from '@/lib/event-extraction-service';
import { resolveVideoUrl } from '@/lib/video-url-request';

// Backend URL with validation - skip if not a valid URL
const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

async function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
  let timeout: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<T>((_, reject) => {
        timeout = setTimeout(() => reject(new Error(`${label} timed out`)), ms);
      }),
    ]);
  } finally {
    if (timeout) clearTimeout(timeout);
  }
}


/**
 * POST /api/video
 *
 * Tries the full backend pipeline first (FastAPI transcript-action workflow).
 * If the backend is unreachable — common on Vercel where no Python server
 * runs — falls through to Strategy 2 (Gemini agentic) then Strategy 3
 * (fetchTranscript + extractEvents called directly, no internal HTTP loopback).
 */
export async function POST(request: Request) {
  let videoUrl: string | undefined;
  try {
    const body = await request.json() as Record<string, unknown>;
    const url = resolveVideoUrl(body);
    videoUrl = url;

    if (!url) {
      return NextResponse.json(
        {
          error: 'Video URL is required',
          accepted_fields: ['url', 'youtubeUrl', 'videoUrl', 'video_url'],
        },
        { status: 400 },
      );
    }

    await publishEvent(EventTypes.VIDEO_RECEIVED, { url }, url);

    // ── Strategy 1: Full backend pipeline (skip if no backend configured) ──
    // Calls /api/v1/transcript-action for analysis. For full end-to-end
    // pipeline (analysis → code gen → deploy), use POST /api/pipeline instead.
    if (BACKEND_AVAILABLE) {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 4_000);

        let response: Response;
        try {
          response = await fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...(process.env.EVENTRELAY_API_KEY ? { 'X-API-Key': process.env.EVENTRELAY_API_KEY } : {}) },
            body: JSON.stringify({ video_url: url, language: 'en' }),
            signal: controller.signal,
          });
        } finally {
          clearTimeout(timeout);
        }

        if (response.ok) {
          const result = await response.json();

          if (result.async_processing && result.job_id) {
            await publishEvent(
              EventTypes.PIPELINE_QUEUED,
              { strategy: 'backend-async', queued: true, jobId: result.job_id },
              url,
            );

            return NextResponse.json({
              id: result.job_id,
              status: 'queued',
              processing_time_ms: 0,
              result: {
                success: true,
                async: true,
                poll_url: result.status_url,
                transcript_segments: 0,
                agents_used: [],
                errors: [],
                raw_response: result,
              },
            });
          }

          const transcriptAction = result.outputs?.transcript_action?.data || {};
          const personalityAgent = result.outputs?.personality_agent?.data || {};
          const strategyAgent = result.outputs?.strategy_agent?.data || {};
          const rankedActions = Array.isArray(transcriptAction.priority_ranked_actions)
            ? transcriptAction.priority_ranked_actions.map((action: any) => ({
                title: action.text || 'Untitled',
                description: action.reasoning || '',
                category: action.tier || 'General',
                estimatedMinutes: null,
              }))
            : [];

          let summaryText = 'Video analyzed successfully';
        const rawSummary = transcriptAction.summary;
        if (typeof rawSummary === 'string') {
          summaryText = rawSummary;
        } else if (rawSummary && typeof rawSummary === 'object') {
          summaryText =
            rawSummary.content ||
            rawSummary.executive_summary ||
            (typeof rawSummary.raw === 'string'
              ? (() => {
                  try {
                    const parsed = JSON.parse(rawSummary.raw.replace(/```json\n?|```/g, ''));
                    return parsed.executive_summary || parsed.summary || rawSummary.raw.slice(0, 200);
                  } catch {
                    return rawSummary.raw.slice(0, 200);
                  }
                })()
              : JSON.stringify(rawSummary).slice(0, 200));
        }

        const insights = {
          summary: summaryText,
          actions: rankedActions.length > 0
            ? rankedActions
            : Object.values(transcriptAction.task_board || {}).flatMap((col: any) =>
                Array.isArray(col) ? col.map((t: any) => ({
                  title: t.title || 'Untitled',
                  description: t.definition_of_done || t.description || '',
                  category: t.owner_role || 'General',
                  estimatedMinutes: t.estimate_days ? parseFloat(t.estimate_days) * 24 * 60 : null
                })) : []
              ),
          topics: transcriptAction.metadata?.topics || [],
          sentiment: personalityAgent.personality_map?.video_intent?.primary || 'Neutral',
          strategy: strategyAgent.strategic_analysis || null,
          project_scaffold: transcriptAction.project_scaffold || null,
        };

        await publishEvent(EventTypes.PIPELINE_COMPLETED, { strategy: 'backend', success: result.success, agents: result.orchestration_meta?.agents_used || [] }, url);

        // Save as training example for Vertex AI fine-tuning
        if (result.success) {
          saveTrainingExample(url, result).catch((e) =>
            console.warn('[Training] Failed to save example:', e),
          );
        }

        return NextResponse.json({
          id: `vid_${Date.now().toString(36)}`,
          status: result.success ? 'complete' : 'failed',
          processing_time_ms: Math.round((result.orchestration_meta?.processing_time || 0) * 1000),
          result: {
            success: result.success,
            insights,
            transcript_segments: (Array.isArray(result.transcript) ? result.transcript.length : result.transcript?.segments?.length) || 0,
            agents_used: result.orchestration_meta?.agents_used || [],
            errors: result.errors || [],
            raw_response: result,
          },
        });
      }
        console.warn(`Backend returned ${response.status}, falling back to frontend-only pipeline`);
      } catch {
        console.log('Backend unavailable — using frontend-only pipeline');
      }
    }

    // ── Strategy 2: Gemini Agentic Analysis (primary frontend strategy) ──
    // Uses Google Search grounding to retrieve transcripts, descriptions,
    // and chapter data directly — no separate transcribe/extract steps needed.
    if (hasGeminiKey()) {
      try {
        await publishEvent(EventTypes.TRANSCRIPT_STARTED, { url, strategy: 'gemini-agentic' }, url);
        const startTime = Date.now();
        const analysis = await withTimeout(
          analyzeVideoWithGemini(url),
          5_000,
          'Gemini agentic analysis',
        );
        const elapsed = Date.now() - startTime;

        await publishEvent(EventTypes.PIPELINE_COMPLETED, {
          strategy: 'gemini-agentic',
          success: true,
          transcriptSegments: analysis.transcript?.length || 0,
          events: analysis.events?.length || 0,
        }, url);

        // Save as training example for Vertex AI fine-tuning
        saveTrainingExample(url, analysis as unknown as Record<string, unknown>).catch((e) =>
          console.warn('[Training] Failed to save example:', e),
        );

        return NextResponse.json({
          id: `vid_${Date.now().toString(36)}`,
          status: 'complete',
          processing_time_ms: elapsed,
          result: {
            success: true,
            insights: {
              summary: analysis.summary,
              actions: analysis.actions || [],
              topics: analysis.topics || [],
              sentiment: 'Neutral',
            },
            transcript_segments: analysis.transcript?.length || 0,
            transcript_source: 'gemini-agentic',
            agents_used: ['gemini-agentic-engine'],
            errors: [],
            raw_response: {
              title: analysis.title,
              transcript: analysis.transcript,
              events: analysis.events,
              actions: analysis.actions,
              architectureCode: analysis.architectureCode,
              ingestScript: analysis.ingestScript,
            },
          },
        });
      } catch (e) {
        console.warn('Gemini agentic analysis failed, falling back to transcribe chain:', e);
      }
    }

    // ── Strategy 3: Frontend-only transcribe → extract chain (fallback) ──
    // Calls service functions directly — no internal HTTP loopback that breaks on Vercel.
    let transcript = '';
    let transcriptSource = 'none';
    try {
      await publishEvent(EventTypes.TRANSCRIPT_STARTED, { url, strategy: 'frontend-chain' }, url);
      const transcribeResult = await withTimeout(
        fetchTranscript({ url }),
        8_000,
        'Transcript fallback',
      );
      if (transcribeResult.success && transcribeResult.transcript) {
        transcript = transcribeResult.transcript;
        transcriptSource = transcribeResult.source || 'frontend';
        await publishEvent(EventTypes.TRANSCRIPT_COMPLETED, { source: transcriptSource, wordCount: transcript.split(/\s+/).length }, url);
      }
    } catch (e) {
      console.error('Transcript extraction failed:', e);
    }

    let extraction: ExtractionData = { events: [], actions: [], summary: '', topics: [] };
    if (transcript) {
      try {
        await publishEvent(EventTypes.EXTRACTION_STARTED, { transcriptLength: transcript.length }, url);
        const extractResult = await extractEvents({ transcript, videoUrl: url });
        if (extractResult.success && extractResult.data) {
          extraction = extractResult.data;
          await publishEvent(EventTypes.EXTRACTION_COMPLETED, { events: extraction.events?.length || 0, actions: extraction.actions?.length || 0 }, url);
        }
      } catch (e) {
        console.error('Event extraction failed:', e);
      }
    }

    const hasResults = transcript.length > 0;

    await publishEvent(
      hasResults ? EventTypes.PIPELINE_COMPLETED : EventTypes.PIPELINE_FAILED,
      { strategy: 'frontend-chain', success: hasResults, transcriptSource },
      url,
    );

    return NextResponse.json({
      id: `vid_${Date.now().toString(36)}`,
      status: hasResults ? 'complete' : 'failed',
      processing_time_ms: 0,
      result: {
        success: hasResults,
        insights: {
          summary: extraction.summary || (hasResults ? 'Transcript extracted successfully' : 'Could not extract transcript — ensure GEMINI_API_KEY or OPENAI_API_KEY is set in Vercel environment variables'),
          actions: extraction.actions || [],
          topics: extraction.topics || [],
          sentiment: 'Neutral',
        },
        transcript_segments: 0,
        transcript_source: transcriptSource,
        agents_used: ['frontend-pipeline'],
        errors: hasResults ? [] : ['All strategies failed — ensure GEMINI_API_KEY or OPENAI_API_KEY is set in Vercel environment variables'],
        raw_response: {
          transcript: { text: transcript },
          extraction,
        },
      },
    });
  } catch (error) {
    console.error('Video analysis error:', error);
    await publishEvent(EventTypes.PIPELINE_FAILED, { error: String(error) }, videoUrl).catch(() => {});
    return NextResponse.json(
      { error: 'Failed to analyze video', details: String(error) },
      { status: 500 },
    );
  }
}

export async function GET() {
  // If backend URL is configured and valid, check its health
  if (BACKEND_AVAILABLE) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/health`);
      const health = await response.json();

      return NextResponse.json({
        name: 'UVAI Video Analysis API',
        version: '2.0.0',
        backend_status: health.status,
        backend_components: health.components,
        endpoints: {
          analyze: 'POST /api/video - Analyze a video URL',
          health: 'GET /api/video - Check API status',
        },
      });
    } catch {
      // Backend configured but unreachable
    }
  }

  // Frontend-only mode
  return NextResponse.json({
    name: 'UVAI Video Analysis API',
    version: '2.0.0',
    backend_status: 'not-configured',
    frontend_pipeline: 'active',
    endpoints: {
      analyze: 'POST /api/video - Analyze a video URL',
      pipeline: 'POST /api/pipeline - Full end-to-end pipeline (YouTube URL → deployed software)',
    },
  });
}
