import 'server-only';

import OpenAI from 'openai';
import { fetchYouTubeMetadata, formatMetadataAsContext } from '@/lib/youtube-metadata';
import { getGeminiClient, hasGeminiKey } from '@/lib/gemini-client';
import { GEMINI_SEARCH_MODEL } from '@/lib/gemini-models';
import { gatewayChat, hasAiGatewayKey, toGatewayModelId } from '@/lib/vercel-ai-gateway';
import { assertPublicHttpUrl } from '@/lib/ssrf-guard';

let _openai: OpenAI | null = null;
function getOpenAI() {
  if (!_openai) _openai = new OpenAI();
  return _openai;
}

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

// Resolve with the first non-null candidate, or null once every candidate has
// settled (resolved null or rejected). Unlike Promise.race() over null-swapped
// promises, this always settles — it cannot hang when every candidate fails.
export function firstNonNull<T>(candidates: Promise<T | null>[]): Promise<T | null> {
  return new Promise(resolve => {
    let remaining = candidates.length;
    if (remaining === 0) {
      resolve(null);
      return;
    }
    const settle = (value: T | null) => {
      // Null check, not a truthy check: a falsy-but-valid result (e.g. an empty
      // string or 0 for other T) must count as a real result, not a failed
      // candidate. null is the only "no result" sentinel here.
      if (value !== null) {
        resolve(value);
      } else if (--remaining === 0) {
        resolve(null);
      }
    };
    for (const p of candidates) {
      p.then(settle, () => settle(null));
    }
  });
}

export interface TranscriptionOptions {
  url?: string;
  audioUrl?: string;
  language?: string;
}

export interface TranscriptionResult {
  success: boolean;
  transcript: string;
  segments?: any[];
  source?: string;
  wordCount?: number;
  metadata?: any;
  error?: string;
}

/**
 * Fetches transcript using multi-strategy fallback:
 * 1. Python backend (YouTube captions API)
 * 2. Gemini + Google Search Grounding
 * 3. OpenAI + Web Search
 * 4. Direct audio STT via OpenAI Whisper
 */
export async function fetchTranscript({
  url,
  audioUrl,
  language = 'en',
}: TranscriptionOptions): Promise<TranscriptionResult> {
  if (!url && !audioUrl) {
    return { success: false, error: 'url or audioUrl is required', transcript: '' };
  }

  // Fetch YouTube metadata (description, chapters, title) — shared by all strategies
  const metadataPromise = url ? fetchYouTubeMetadata(url).catch((err) => {
    console.log('YouTube metadata fetch failed:', err);
    return null;
  }) : Promise.resolve(null);

  // Strategy 1: Try YouTube transcript API via backend (fast + free).
  // Run this FIRST and return early on success so the paid AI providers
  // (Gemini/OpenAI) are only invoked as a fallback. Racing them in parallel
  // would run — and bill — the paid providers on every request even when the
  // free backend transcript is available (denial-of-wallet / cost regression).
  if (url && !audioUrl && BACKEND_AVAILABLE) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8_000);

      const ytResponse = await fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(process.env.EVENTRELAY_API_KEY ? { 'X-API-Key': process.env.EVENTRELAY_API_KEY } : {}),
        },
        body: JSON.stringify({ video_url: url, language }),
        signal: controller.signal,
      }).finally(() => clearTimeout(timeout));

      if (ytResponse.ok) {
        const result = await ytResponse.json();

        // Handle transcript as segments array
        const segments = Array.isArray(result.transcript) ? result.transcript : [];
        if (segments.length > 0) {
          const fullText = segments
            .map((s: { text?: string }) => s.text || '')
            .join(' ')
            .trim();

          if (fullText.length > 50) {
            return {
              success: true,
              transcript: fullText,
              segments,
              source: 'youtube',
              wordCount: fullText.split(/\s+/).length,
            } satisfies TranscriptionResult;
          }
        }

        // Handle transcript as { text: string }
        const transcriptText =
          typeof result.transcript === 'string'
            ? result.transcript
            : result.transcript?.text;
        if (typeof transcriptText === 'string' && transcriptText.length > 50) {
          return {
            success: true,
            transcript: transcriptText,
            source: 'youtube',
            wordCount: transcriptText.split(/\s+/).length,
          } satisfies TranscriptionResult;
        }
      }
    } catch (e) {
      console.log('YouTube backend transcript unavailable:', e);
    }
  }

  // Strategies 2 & 3: Run Gemini and OpenAI in parallel — first successful result wins.
  // This eliminates the worst-case sequential 30s + 30s wait when both providers
  // are available, cutting latency to the faster of the two.
  if (url && !audioUrl) {
    const candidates: Promise<TranscriptionResult | null>[] = [];

    // Strategy 2: Gemini with Google Search grounding
    if (hasGeminiKey()) {
      const geminiPromise: Promise<TranscriptionResult | null> = (async () => {
        try {
          const metadata = await metadataPromise;
          const metadataContext = metadata ? formatMetadataAsContext(metadata) : '';
          const geminiPrompt = `You are a video transcription assistant.

For the following YouTube video, find the ACTUAL transcript, description, and chapter content.
The video creator often provides detailed descriptions with chapter breakdowns — USE that
metadata as high-quality structured content.

${metadataContext ? `KNOWN VIDEO METADATA:\n${metadataContext}\n` : ''}
Video URL: ${url}

INSTRUCTIONS:
1. Return the video's spoken transcript if available.
2. If not, reconstruct detailed content from description, chapters, and related material.
3. Be thorough — capture ALL key points, technical details, quotes, and actionable insights.
4. Include timestamps in [MM:SS] format where possible.
5. Do NOT return generic advice like "click Show Transcript" — return actual content.`;

          const text = hasAiGatewayKey()
            ? (
                await gatewayChat({
                  model: toGatewayModelId(GEMINI_SEARCH_MODEL),
                  messages: [{ role: 'user', content: geminiPrompt }],
                  max_tokens: 4096,
                  temperature: 0.2,
                })
              ).content
            : (
                await getGeminiClient().models.generateContent({
                  model: GEMINI_SEARCH_MODEL,
                  contents: geminiPrompt,
                  config: {
                    temperature: 0.2,
                    tools: [{ googleSearch: {} }],
                  },
                })
              ).text ?? '';
          if (text.length > 100) {
            return {
              success: true,
              transcript: text,
              source: 'gemini-search',
              wordCount: text.split(/\s+/).length,
              metadata: metadata
                ? {
                    title: metadata.title,
                    channel: metadata.channel,
                    chapters: metadata.chapters,
                  }
                : undefined,
            } satisfies TranscriptionResult;
          }
          return null;
        } catch (e) {
          console.warn('Gemini Google Search transcript failed:', e);
          return null;
        }
      })();
      candidates.push(geminiPromise);
    }

    // Strategy 3: OpenAI Responses API with web_search
    if (process.env.OPENAI_API_KEY) {
      const openaiPromise: Promise<TranscriptionResult | null> = (async () => {
        try {
          const metadata = await metadataPromise;
          const metadataContext = metadata ? formatMetadataAsContext(metadata) : '';
          const response = await getOpenAI().responses.create({
            model: 'gpt-4o-mini',
            instructions: `You are a video content transcription assistant.
Given a YouTube URL, use web search to find the video's ACTUAL transcript or detailed content.
Return the full transcript text if available. If not, provide a comprehensive content summary
based on the video's description, chapters, and any available reviews or summaries.
Do NOT return instructions on how to find a transcript — return the actual content.
Be thorough — capture all key points, quotes, technical details, and chapter breakdowns.`,
            tools: [{ type: 'web_search' as const }],
            input: `Find and return the full transcript or detailed content of this video: ${url}
${metadataContext ? `\nKNOWN METADATA:\n${metadataContext}` : ''}`,
          });
          const text = response.output_text || '';
          // Reject results that are just instructions rather than actual content
          const isGarbage =
            text.toLowerCase().includes('click show transcript') ||
            text.toLowerCase().includes('click on the three dots') ||
            text.toLowerCase().includes('steps to find') ||
            (text.length < 300 && text.includes('transcript'));
          if (text.length > 100 && !isGarbage) {
            return {
              success: true,
              transcript: text,
              source: 'openai-web-search',
              wordCount: text.split(/\s+/).length,
            } satisfies TranscriptionResult;
          }
          return null;
        } catch (e) {
          console.warn('OpenAI web_search transcript failed:', e);
          return null;
        }
      })();
      candidates.push(openaiPromise);
    }

    if (candidates.length > 0) {
      // Run all candidates concurrently and return the first non-null result.
      // firstNonNull resolves as soon as any candidate yields a usable result,
      // and resolves null once every candidate has failed — so this never hangs
      // when all providers return null (a Promise.race() over null-swapped
      // promises would hang forever in that case).
      const winner = await firstNonNull(candidates);
      if (winner) return winner;
    }
  }

  // Strategy 4: Direct audio file transcription via OpenAI Whisper
  if (audioUrl && process.env.OPENAI_API_KEY) {
    try {
      // SSRF guard: reject non-public/internal URLs before any server-side fetch.
      try {
        await assertPublicHttpUrl(audioUrl);
      } catch (guardErr) {
        // Forwarding the guard's cause told the caller WHICH rule fired —
        // `Blocked host` confirms a hostname-blocklist match, while a
        // resolution failure confirms only that DNS gave nothing public. That
        // difference is a policy oracle, and it sharpens as BLOCKED_HOSTNAMES
        // grows. The guard now reports one uniform message for every rejection
        // (see SSRF_REJECTION_MESSAGE), so the cause cannot leak through here
        // even by accident; the specific reason names the host, its resolved
        // address, or the resolver errno, and belongs only in the log.
        // Logged as the error object, not `guardErr.reason`: an `instanceof`
        // check against the imported class silently degrades wherever the
        // module identity differs (test mocks, dual-package/ESM-CJS interop),
        // and `SsrfGuardError` carries `reason` as an own enumerable property,
        // so the object form reaches operators either way.
        console.error('[transcription] audioUrl rejected by SSRF guard:', guardErr);
        return {
          success: false,
          // Constant, and pinned by transcription-error-disclosure.test.ts.
          error: 'Rejected audioUrl',
          transcript: '',
        };
      }

      const audioResponse = await fetch(audioUrl, { signal: AbortSignal.timeout(30_000) });
      if (!audioResponse.ok) {
        // The status belongs to a caller-supplied `audioUrl`. Echoing it turns
        // this route into a probe: the caller learns 401 vs 403 vs 404 vs 500
        // for any host the SSRF guard admits, which is a cross-origin read the
        // browser same-origin policy would otherwise deny them. Log it, and
        // report only that the fetch failed.
        console.error(
          `[transcription] audioUrl fetch failed with status ${audioResponse.status}`,
        );
        return {
          success: false,
          error: 'Could not retrieve the audio file',
          transcript: '',
        };
      }

      // Denial-of-wallet guard: cap audio size (OpenAI STT limit is 25 MB).
      const MAX_AUDIO_BYTES = 25 * 1024 * 1024;
      const declaredLen = Number(audioResponse.headers.get('content-length') ?? '0');
      if (declaredLen > MAX_AUDIO_BYTES) {
        return { success: false, error: 'Audio file exceeds 25 MB limit', transcript: '' };
      }

      // Stream with an incremental byte counter so a missing or spoofed
      // Content-Length cannot stream unbounded data into memory (OOM/DoS).
      const reader = audioResponse.body?.getReader();
      if (!reader) {
        return { success: false, error: 'Audio response has no readable body', transcript: '' };
      }
      const chunks: Uint8Array[] = [];
      let received = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value) {
          received += value.byteLength;
          if (received > MAX_AUDIO_BYTES) {
            await reader.cancel();
            return { success: false, error: 'Audio file exceeds 25 MB limit', transcript: '' };
          }
          chunks.push(value);
        }
      }
      // Derive filename + MIME from the response (Whisper rejects mismatched types).
      const contentType = (audioResponse.headers.get('content-type') || '')
        .split(';')[0]
        .trim()
        .toLowerCase();
      const extByMime: Record<string, string> = {
        'audio/mpeg': 'mp3', 'audio/mp3': 'mp3', 'audio/mp4': 'm4a', 'audio/x-m4a': 'm4a',
        'audio/wav': 'wav', 'audio/x-wav': 'wav', 'audio/webm': 'webm', 'audio/ogg': 'ogg',
        'audio/flac': 'flac',
      };
      let urlExt = '';
      try {
        urlExt = new URL(audioUrl).pathname.split('.').pop()?.toLowerCase() ?? '';
      } catch {
        urlExt = '';
      }
      const ext =
        extByMime[contentType] ||
        (['mp3', 'm4a', 'wav', 'webm', 'ogg', 'flac', 'mp4', 'mpga'].includes(urlExt) ? urlExt : 'mp3');
      const audioFile = new File(chunks as BlobPart[], `audio.${ext}`, {
        type: contentType || 'audio/mpeg',
      });

      const transcription = await getOpenAI().audio.transcriptions.create({
        model: 'gpt-4o-mini-transcribe',
        file: audioFile,
        language,
      });

      return {
        success: true,
        transcript: transcription.text,
        source: 'openai-stt',
        wordCount: transcription.text.split(/\s+/).length,
      };
    } catch (e) {
      console.warn('OpenAI Whisper STT failed:', e);
    }
  }

  // No strategy succeeded.
  //
  // Which provider keys this deployment holds is server configuration, not
  // caller-facing detail: branching the client message on `hasKeys` told any
  // caller whether OPENAI_API_KEY/GEMINI_API_KEY were set, and named the
  // variables and the hosting platform. Both outcomes now report the same
  // string; the distinction survives in the operator log, which is the only
  // place it was ever actionable.
  const hasKeys = !!(process.env.OPENAI_API_KEY || hasGeminiKey());
  console.error(
    hasKeys
      ? '[transcription] all strategies failed with provider keys configured'
      : '[transcription] all strategies failed: no OPENAI_API_KEY or GEMINI_API_KEY configured',
  );
  return {
    success: false,
    error: 'Could not transcribe video — all strategies failed',
    transcript: '',
  };
}
