/**
 * Durable video → actions pipeline (Workflow DevKit).
 *
 * Orchestrates existing EventRelay capabilities as retryable steps so a long
 * analysis does not die with a single serverless request timeout.
 *
 * Trigger: POST /api/workflows/video-to-actions  { url, videoTitle? }
 * Inspect: npx workflow web  (from apps/web)
 */

import { FatalError } from 'workflow';

export interface VideoToActionsInput {
  url: string;
  videoTitle?: string;
}

export interface VideoToActionsResult {
  url: string;
  transcriptChars: number;
  actionCount: number;
  provider?: string;
  actions: Array<{ tool: string; status: string; result?: string }>;
}

export async function videoToActionsWorkflow(
  input: VideoToActionsInput,
): Promise<VideoToActionsResult> {
  'use workflow';

  console.log('[video-to-actions] start', { url: input.url });

  const transcript = await transcribeStep(input.url);
  if (!transcript || transcript.trim().length < 40) {
    throw new FatalError('Transcript too short or unavailable for action extraction');
  }

  const agent = await runActionsStep(transcript, input.videoTitle);

  console.log('[video-to-actions] complete', {
    chars: transcript.length,
    actions: agent.actions.length,
  });

  return {
    url: input.url,
    transcriptChars: transcript.length,
    actionCount: agent.actions.length,
    provider: agent.provider,
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

  // Prefer server-side transcription helper when available; fall back to local API.
  try {
    const { fetchTranscript } = await import('@/lib/transcription-service');
    const result = await fetchTranscript({ url });
    if (result?.transcript && typeof result.transcript === 'string') {
      return result.transcript;
    }
  } catch (err) {
    console.warn('[video-to-actions] transcription-service failed', err);
  }

  const base =
    process.env.NEXTAUTH_URL ||
    process.env.VERCEL_URL?.replace(/^/, 'https://') ||
    'http://127.0.0.1:3000';
  const res = await fetch(`${base.replace(/\/$/, '')}/api/transcribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  const body = (await res.json().catch(() => ({}))) as {
    success?: boolean;
    transcript?: string;
    error?: string;
  };
  if (!res.ok || !body.transcript) {
    throw new Error(body.error || `Transcribe failed (${res.status})`);
  }
  return body.transcript;
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
    // Surface as retryable unless it's clearly a config/client error.
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes('No AI API key') || msg.includes('too short')) {
      throw new FatalError(msg);
    }
    throw err;
  }
}
