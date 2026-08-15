/**
 * Durable video → actions pipeline (Workflow DevKit) — Product v1.
 *
 * Orchestrates existing EventRelay capabilities as retryable steps so a long
 * analysis does not die with a single serverless request timeout.
 *
 * Trigger: POST /api/workflows/video-to-actions
 *          { url, videoTitle?, transcript?, events? }
 * Status:  GET  /api/workflows/video-to-actions/:runId
 * Inspect: npx workflow web  (from apps/web)
 *
 * When Analyze already produced a transcript, pass it through so Act stays on
 * the same run instead of re-fetching YouTube. Steps call server libs directly
 * (no self-HTTP loopback) so Vercel production does not depend on NEXTAUTH_URL
 * / internal tokens for step execution.
 */

import { FatalError } from 'workflow';

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
}

export async function videoToActionsWorkflow(
  input: VideoToActionsInput,
): Promise<VideoToActionsResult> {
  'use workflow';

  const url = (input.url || '').trim();
  if (!url || !/^https?:\/\//i.test(url)) {
    throw new FatalError('url must be an http(s) URL');
  }

  const provided = (input.transcript || '').trim();
  const usedProvidedTranscript = provided.length >= 40;
  console.log('[video-to-actions] start', { url, usedProvidedTranscript });

  const transcript = usedProvidedTranscript ? provided : await transcribeStep(url);
  if (!transcript || transcript.trim().length < 40) {
    throw new FatalError('Transcript too short or unavailable for action extraction');
  }

  const eventLines = (input.events || [])
    .slice(0, 40)
    .map((event) => {
      const kind = event.type || 'event';
      return `- [${kind}] ${event.title}${event.description ? `: ${event.description}` : ''}`;
    })
    .join('\n');
  const agentSource = eventLines
    ? `${transcript.slice(0, 12_000)}\n\nEVENTS FROM ANALYZE:\n${eventLines}`
    : transcript;
  const agent = await runActionsStep(agentSource, input.videoTitle);

  console.log('[video-to-actions] complete', {
    chars: transcript.length,
    actions: agent.actions.length,
    usedProvidedTranscript,
  });

  return {
    url,
    transcriptChars: transcript.length,
    actionCount: agent.actions.length,
    provider: agent.provider,
    usedProvidedTranscript,
    actions: agent.actions.map((a) => ({
      tool: a.tool,
      status: a.status,
      result: a.result,
    })),
  };
}

async function transcribeStep(url: string): Promise<string> {
  'use step';

  console.log('[video-to-actions] step:transcribe', url);

  const { fetchTranscript } = await import('@/lib/transcription-service');
  const result = await fetchTranscript({ url });

  if (result?.success && result.transcript && typeof result.transcript === 'string') {
    return result.transcript;
  }

  // Retryable when the service is flaky; Fatal when clearly unusable input/config.
  const errMsg =
    (result && typeof result.error === 'string' && result.error) ||
    'Transcription returned no transcript';
  if (
    /invalid|required|rejected|too short|billing|not configured|No AI API/i.test(errMsg)
  ) {
    throw new FatalError(errMsg);
  }
  throw new Error(errMsg);
}

async function runActionsStep(
  transcript: string,
  videoTitle?: string,
): Promise<{
  provider?: string;
  actions: Array<{ tool: string; status: string; result?: string }>;
}> {
  'use step';

  console.log('[video-to-actions] step:actions', { chars: transcript.length });

  try {
    const { runActionAgent } = await import('@/lib/action-agent');
    const result = await runActionAgent({ transcript, videoTitle });
    return {
      provider: result.provider,
      actions: (result.actions || []).map((a) => ({
        tool: a.tool,
        status: a.status,
        result: a.result,
      })),
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (
      msg.includes('No AI API key') ||
      msg.includes('too short') ||
      /billing|not configured/i.test(msg)
    ) {
      throw new FatalError(msg);
    }
    throw err;
  }
}
