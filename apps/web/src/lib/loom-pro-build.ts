import 'server-only';

import { grokChatCompletion } from '@/lib/billing/grok-client';
import { acquireLoomAudio } from '@/lib/loom-audio';
import { transcribeWithXai } from '@/lib/xai-stt';

export class LoomBuildError extends Error {
  readonly code: 'xai_stt_failed' | 'xai_key_missing' | 'grok_failed';
  readonly status: number;

  constructor(message: string, code: LoomBuildError['code'], status: number) {
    super(message);
    this.name = 'LoomBuildError';
    this.code = code;
    this.status = status;
  }
}

export type LoomProBuild = {
  loomId: string;
  shareUrl: string;
  transcript: string;
  duration: number;
  answer: string;
  provider: 'xai';
  model: string;
  sttModel: string;
  audioSource: string;
};

const BUILD_SYSTEM_PROMPT = [
  'You are the UVAI Workflow Pro lead agent (Grok).',
  'The user pasted a public Loom recording. The transcript below is the only evidence.',
  'Produce shipable build rails: what to build, the architecture, and the first concrete actions.',
  'Stay grounded in the transcript. Do not invent a live deployment URL or claim the build is deployed.',
].join(' ');

/**
 * Pro-only Loom path: share URL → audio (file or direct URL) → xAI STT → in-session Grok build.
 * Does not touch the YouTube Video Pack / Gemini caption path.
 */
export async function buildFromLoomShare(shareUrl: string, model: string): Promise<LoomProBuild> {
  const audio = await acquireLoomAudio(shareUrl);
  let transcript: Awaited<ReturnType<typeof transcribeWithXai>>;
  try {
    transcript = await transcribeWithXai(
      audio.mode === 'file'
        ? {
            file: {
              bytes: audio.bytes,
              filename: audio.filename,
              contentType: audio.contentType,
            },
          }
        : { url: audio.mediaUrl },
    );
  } catch (err) {
    console.error('loom xai stt failed', err);
    const message = err instanceof Error ? err.message : 'xai_stt_failed';
    if (message.startsWith('XAI_API_KEY missing')) {
      throw new LoomBuildError(message, 'xai_key_missing', 503);
    }
    throw new LoomBuildError('xAI speech-to-text failed.', 'xai_stt_failed', 502);
  }
  const userPrompt = [
    `Loom share ${audio.share.shareUrl}`,
    `Audio duration: ${transcript.duration}s`,
    '',
    'Transcript:',
    transcript.text,
  ].join('\n');

  let grok: Awaited<ReturnType<typeof grokChatCompletion>>;
  try {
    grok = await grokChatCompletion(userPrompt, model, { systemPrompt: BUILD_SYSTEM_PROMPT });
  } catch (err) {
    console.error('loom pro grok build failed', err);
    const message = err instanceof Error ? err.message : 'grok_failed';
    throw new LoomBuildError(`Pro Grok unavailable: ${message}`, 'grok_failed', 503);
  }

  return {
    loomId: audio.share.videoId,
    shareUrl: audio.share.shareUrl,
    transcript: transcript.text,
    duration: transcript.duration,
    answer: grok.answer,
    provider: grok.provider,
    model: grok.model,
    sttModel: transcript.model,
    audioSource: audio.source,
  };
}
