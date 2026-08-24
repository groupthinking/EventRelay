import { NextResponse } from 'next/server';
import { waitUntil } from '@vercel/functions';
import { publishEvent, EventTypes } from '@/lib/cloudevents';
import { saveTrainingExample } from '@/lib/training-store';
import {
  assessAnalysisEvidence,
  calculateDurationCoverageSeconds,
  normalizeTranscriptSegments,
  transcriptTextFromSegments,
  type AnalysisProvenance,
  type EvidenceAssessment,
  type TranscriptSegment,
} from '@/lib/analysis-evidence';
import {
  parseVerifiedBackendTranscript,
  type TranscriptionResult,
} from '@/lib/transcription-service';
import { backendHeaders, resolveLegacyBackend } from '@/lib/backend/capability';

// Resolved through the shared capability resolver so this also picks up
// NEXT_PUBLIC_BACKEND_URL (audit finding F1). Previously BACKEND_AVAILABLE was
// always false in production, so Strategy 1 (the full backend pipeline) was
// skipped on every request and this route silently ran frontend-only.
const { url: BACKEND_URL, available: BACKEND_AVAILABLE } = resolveLegacyBackend();

export const runtime = 'nodejs';
export const maxDuration = 120;

/**
 * Get the absolute base URL for the current request.
 * Uses the request's origin or falls back to environment variables.
 */
function getBaseUrl(request: Request): string {
  const url = new URL(request.url);
  return `${url.protocol}//${url.host}`;
}
function buildEvidenceEnvelope(
  result: TranscriptionResult,
  requestedUrl: string,
): {
  transcript: string;
  segments: TranscriptSegment[];
  provenance: AnalysisProvenance;
  quality: EvidenceAssessment;
} | null {
  const normalized = normalizeTranscriptSegments(result.segments);
  const transcript = result.transcript?.trim() || transcriptTextFromSegments(normalized);
  if (!result.success || result.verified !== true || transcript.length < 40) return null;

  const segments = normalized.length > 0
    ? normalized
    : [{ start: 0, duration: 0, text: transcript }];
  const sourceUrl = result.sourceUrl || requestedUrl;
  let sourceHost = '';
  try { sourceHost = new URL(sourceUrl).hostname; } catch { /* gate reports missing URL below */ }
  const timedSegmentCount = segments.filter((segment) => segment.duration > 0).length;
  const provenance: AnalysisProvenance = {
    sourceUrl,
    sourceHost,
    acquisitionMethod: result.acquisitionMethod || 'unknown',
    transcriptSource: result.source || 'unknown',
    transcriptVerified: true,
    acquiredAt: result.acquiredAt || new Date().toISOString(),
    segmentCount: segments.length,
    timedSegmentCount,
    durationCoverageSeconds: calculateDurationCoverageSeconds(segments),
    warnings: timedSegmentCount === segments.length
      ? []
      : ['Source timestamps were unavailable for part or all of the transcript.'],
  };
  const quality = assessAnalysisEvidence({ transcript, segments, provenance });
  return quality.passed ? { transcript, segments, provenance, quality } : null;
}


/**
 * POST /api/video
 *
 * Tries the full backend pipeline first (FastAPI transcript-action workflow).
 * If the backend is unreachable — common on Vercel where no Python server
 * runs — falls through to a frontend-only path that chains /api/transcribe
 * and /api/extract-events serverless functions directly.
 */
export async function POST(request: Request) {
  let videoUrl: string | undefined;
  try {
    const body = await request.json();
    if (!body || typeof body !== 'object') {
      return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
    }
    const { url } = body;
    videoUrl = url;

    if (!url) {
      return NextResponse.json({ error: 'Video URL is required' }, { status: 400 });
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
            // Shared builder trims EVENTRELAY_API_KEY (Secret Manager values
            // commonly carry a trailing newline, which yields a silent 401).
            headers: backendHeaders(),
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

          const backendTranscript = parseVerifiedBackendTranscript(result, url);
          const evidence = backendTranscript
            ? buildEvidenceEnvelope(backendTranscript, url)
            : null;
          if (!evidence) {
            throw new Error('Backend did not return trusted caption or speech-to-text evidence.');
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

        // Direct waitUntil on publishEvent (CloudEvent) for completion — ancillary, does not block response
        waitUntil(
          publishEvent(EventTypes.PIPELINE_COMPLETED, { strategy: 'backend', success: result.success, agents: result.orchestration_meta?.agents_used || [] }, url).catch(() => {}),
        );

        // Direct waitUntil on saveTrainingExample for Vertex AI fine-tuning (ancillary post-response)
        if (result.success) {
          waitUntil(
            saveTrainingExample(url, result).catch((e) =>
              console.warn('[Training] Failed to save example:', e),
            ),
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
            provenance: evidence.provenance,
            quality: evidence.quality,
          },
        });
      }
        console.warn(`Backend returned ${response.status}, falling back to frontend-only pipeline`);
      } catch {
        console.log('Backend unavailable — using frontend-only pipeline');
      }
    }

    // ── Strategy 2: verified transcript acquisition → extraction ──
    let transcript = '';
    let transcriptSource = 'none';
    let frontendEvidence: ReturnType<typeof buildEvidenceEnvelope> = null;
    try {
      await publishEvent(EventTypes.TRANSCRIPT_STARTED, { url, strategy: 'frontend-chain' }, url);
      const baseUrl = getBaseUrl(request);
      const transcribeRes = await fetch(`${baseUrl}/api/transcribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
        signal: AbortSignal.timeout(15000),
      });
      const transcribeResult = await transcribeRes.json();
      frontendEvidence = buildEvidenceEnvelope(transcribeResult, url);
      if (frontendEvidence) {
        transcript = frontendEvidence.transcript;
        transcriptSource = frontendEvidence.provenance.transcriptSource;
        await publishEvent(EventTypes.TRANSCRIPT_COMPLETED, { source: transcriptSource, wordCount: transcript.split(/\s+/).length }, url);
      }
    } catch (e) {
      console.error('Transcript extraction failed:', e);
    }

    let extraction: { events?: Array<{ type: string; title: string; description?: string; timestamp?: string; priority?: string }>; actions?: Array<{ title: string; description?: string; category?: string; estimatedMinutes?: number }>; summary?: string; topics?: string[] } = {};
    if (transcript) {
      try {
        await publishEvent(EventTypes.EXTRACTION_STARTED, { transcriptLength: transcript.length }, url);
        const baseUrl = getBaseUrl(request);
        const extractRes = await fetch(`${baseUrl}/api/extract-events`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transcript, videoUrl: url }),
          signal: AbortSignal.timeout(15000),
        });
        const extractResult = await extractRes.json();
        if (extractResult.success && extractResult.data) {
          extraction = extractResult.data;
          await publishEvent(EventTypes.EXTRACTION_COMPLETED, { events: extraction.events?.length || 0, actions: extraction.actions?.length || 0 }, url);
        }
      } catch (e) {
        console.error('Event extraction failed:', e);
      }
    }

    const hasResults = transcript.length > 0 && frontendEvidence?.quality.passed === true;

    // Direct waitUntil on publishEvent for terminal pipeline event (CloudEvent) — ancillary, response should not wait
    waitUntil(
      publishEvent(
        hasResults ? EventTypes.PIPELINE_COMPLETED : EventTypes.PIPELINE_FAILED,
        { strategy: 'frontend-chain', success: hasResults, transcriptSource },
        url,
      ).catch(() => {}),
    );

    return NextResponse.json({
      id: `vid_${Date.now().toString(36)}`,
      status: hasResults ? 'complete' : 'failed',
      processing_time_ms: 0,
      result: {
        success: hasResults,
        insights: {
          summary: extraction.summary || (hasResults ? 'Verified transcript extracted successfully' : 'Verified captions or speech-to-text were unavailable.'),
          actions: extraction.actions || [],
          topics: extraction.topics || [],
          sentiment: 'Neutral',
        },
        transcript_segments: 0,
        transcript_source: transcriptSource,
        agents_used: ['frontend-pipeline'],
        errors: hasResults ? [] : ['Verified captions or speech-to-text were unavailable.'],
        raw_response: {
          transcript: { text: transcript },
          extraction,
        },
        provenance: frontendEvidence?.provenance,
        quality: frontendEvidence?.quality,
      },
    });
  } catch (error) {
    console.error('Video analysis error:', error);
    // Direct waitUntil on publishEvent (ancillary CloudEvent) so it does not block error response
    waitUntil(
      publishEvent(EventTypes.PIPELINE_FAILED, { error: String(error) }, videoUrl).catch(() => {}),
    );
    return NextResponse.json(
      { error: 'Failed to analyze video' },
      { status: 500 },
    );
  }
}

export async function GET() {
  // If backend URL is configured and valid, check its health
  if (BACKEND_AVAILABLE) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/health`, {
        signal: AbortSignal.timeout(5000),
      });
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
