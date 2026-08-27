/**
 * Durable, evidence-gated video ETL workflow.
 *
 * Extract: acquire captions, speech-to-text, or usable derived speech.
 * Transform: analyze that transcript through AI Gateway/Gemini.
 * Load: persist the typed return value in Workflow DevKit under its runId.
 *
 * Verified captions are preferred. Usable derived speech (quality.passed with
 * state=degraded) is still a completed run — Vercel IPs often cannot fetch
 * YouTube timedtext.
 */

import { FatalError } from 'workflow';
import {
  fatalQualityFailure,
  type AnalysisProvenance,
  type EvidenceAssessment,
  type TranscriptSegment,
} from '@/lib/analysis-evidence';
import type { VideoAnalysisResult, VerifiedVideoEvidence } from '@/lib/gemini-video-analyzer';

export interface VideoToActionsEvent {
  type?: string;
  title: string;
  description?: string;
}

export interface VideoToActionsInput {
  url: string;
  videoTitle?: string;
  transcript?: string;
  events?: VideoToActionsEvent[];
}

export interface VideoToActionsResult {
  url: string;
  transcriptChars: number;
  actionCount: number;
  provider?: string;
  usedProvidedTranscript?: boolean;
  actions: Array<{ tool: string; status: string; result?: string }>;
  analysis: VideoAnalysisResult;
  provenance: AnalysisProvenance;
  quality: EvidenceAssessment;
}

export async function videoToActionsWorkflow(
  input: VideoToActionsInput,
): Promise<VideoToActionsResult> {
  'use workflow';

  const url = (input.url || '').trim();
  if (!url || !/^https?:\/\//i.test(url)) {
    throw new FatalError('url must be an http(s) URL');
  }

  const evidence = await transcribeStep(url);
  const analysis = await analyzeStep(url, evidence);
  const quality = analysis.quality;
  const provenance = analysis.provenance;

  const fatal = fatalQualityFailure(quality);
  if (fatal) {
    throw new FatalError(fatal);
  }
  if (!provenance) {
    throw new FatalError('Analysis quality gate failed: missing provenance');
  }

  const provider = await providerLabelStep();
  const actions = (analysis.actions || []).map((action) => ({
    tool: 'review_action',
    status: 'proposed',
    result: action.title,
  }));

  return {
    url,
    transcriptChars: evidence.transcript.length,
    actionCount: analysis.actions?.length || 0,
    provider,
    actions,
    analysis,
    provenance,
    quality,
  };
}

async function transcribeStep(url: string): Promise<VerifiedVideoEvidence> {
  'use step';

  const { fetchTranscript } = await import('@/lib/transcription-service');
  const {
    assessAnalysisEvidence,
    calculateDurationCoverageSeconds,
    normalizeTranscriptSegments,
    transcriptTextFromSegments,
  } = await import('@/lib/analysis-evidence');
  const result = await fetchTranscript({ url });
  const segments = normalizeTranscriptSegments(result.segments);
  const transcript = (
    result.transcript?.trim() ||
    result.derivedContent?.trim() ||
    transcriptTextFromSegments(segments)
  );

  if (transcript.length < 40) {
    throw new FatalError(
      result.error || 'Verified captions or speech-to-text were unavailable.',
    );
  }

  const authoritativeSegments: TranscriptSegment[] = segments.length > 0
    ? segments
    : [{ start: 0, duration: 0, text: transcript }];
  const timedSegmentCount = authoritativeSegments.filter(
    (segment) => segment.duration > 0,
  ).length;
  const sourceUrl = result.sourceUrl || url;
  let sourceHost = '';
  try { sourceHost = new URL(sourceUrl).hostname; } catch { /* invalid source is caught by the gate */ }

  const digest = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(transcript),
  );
  const contentSha256 = Array.from(new Uint8Array(digest))
    .map((value) => value.toString(16).padStart(2, '0'))
    .join('');

  const provenance: AnalysisProvenance = {
    sourceUrl,
    sourceHost,
    acquisitionMethod: result.acquisitionMethod || 'unknown',
    transcriptSource: result.source || 'unknown',
    transcriptVerified: result.verified === true,
    acquiredAt: result.acquiredAt || new Date().toISOString(),
    segmentCount: authoritativeSegments.length,
    timedSegmentCount,
    durationCoverageSeconds: calculateDurationCoverageSeconds(authoritativeSegments),
    contentSha256,
    warnings: timedSegmentCount === authoritativeSegments.length
      ? []
      : ['Source timestamps were unavailable for part or all of the transcript.'],
  };
  const assessment = assessAnalysisEvidence({
    transcript,
    segments: authoritativeSegments,
    provenance,
  });
  if (!assessment.passed) {
    throw new FatalError(`Transcript evidence failed validation: ${assessment.issues.join(' ')}`);
  }

  return { transcript, segments: authoritativeSegments, provenance };
}

async function analyzeStep(
  url: string,
  evidence: VerifiedVideoEvidence,
): Promise<VideoAnalysisResult> {
  'use step';

  const { analyzeVideoWithGemini } = await import('@/lib/gemini-video-analyzer');
  return analyzeVideoWithGemini(url, evidence);
}

async function providerLabelStep(): Promise<string> {
  'use step';

  const { getGeminiRoutingLabel } = await import('@/lib/gemini-client');
  return getGeminiRoutingLabel();
}
