import 'server-only';

import OpenAI from 'openai';
import { fetchYouTubeMetadata, formatMetadataAsContext } from '@/lib/youtube-metadata';
import { getGeminiClient, hasGeminiKey } from '@/lib/gemini-client';
import { assertPublicHttpUrl } from '@/lib/ssrf-guard';

let _openai: OpenAI | null = null;
function getOpenAI() {
  if (!_openai) _openai = new OpenAI();
  return _openai;
}

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

// A never-resolving promise used to skip null candidates in Promise.race():
// when a candidate resolves to null we swap it for this so the race ignores it
// and waits for a real result from another candidate.
// eslint-disable-next-line @typescript-eslint/no-empty-function
const PENDING_FOREVER = new Promise<never>(() => {});

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

  // Strategy 1: Try YouTube transcript API via backend (fast + free)
  if (url && !audioUrl && BACKEND_AVAILABLE) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8_000);

      const ytResponse = await fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(process.env.EVENTRELAY_API_KEY ? { 'X-API-Key': process.env.EVENTRELAY_API_KEY } : {}) },
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
            };
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
          };
        }
      }
    } catch {
      console.log('YouTube transcript unavailable, falling back to AI providers');
    }
  }

  // Fetch YouTube metadata (description, chapters, title) — shared by both fallback strategies
  let metadata: Awaited<ReturnType<typeof fetchYouTubeMetadata>> = null;
  if (url) {
    try {
      metadata = await fetchYouTubeMetadata(url);
    } catch {
      console.log('YouTube metadata fetch failed, continuing without');
    }
  }

  // Strategies 2 & 3: Run Gemini and OpenAI in parallel — first successful result wins.
  // This eliminates the worst-case sequential 30s+30s wait when both providers
  // are available, cutting latency to the faster of the two.
  if (url && !audioUrl) {
    const candidates: Promise<TranscriptionResult | null>[] = [];

    // Strategy 2: Gemini with Google Search grounding
    if (hasGeminiKey()) {
      const metadataContext = metadata ? formatMetadataAsContext(metadata) : '';
      const geminiPromise: Promise<TranscriptionResult | null> = (async () => {
        try {
          const ai = getGeminiClient();
          const result = await ai.models.generateContent({
            model: 'gemini-3.1-pro-preview',
            contents: `You are a video transcription assistant with access to Google Search.

For the following YouTube video, use your googleSearch tool to find the ACTUAL transcript,
description, and chapter content. The video creator often provides detailed descriptions
with chapter breakdowns — USE that metadata as high-quality structured content.

${metadataContext ? `KNOWN VIDEO METADATA:\n${metadataContext}\n` : ''}
Video URL: ${url}

INSTRUCTIONS:
1. Search for the video's transcript using Google Search.
2. If a spoken transcript is available, return it verbatim.
3. If not, reconstruct detailed content from the description, chapters, comments,
   and related articles found via search.
4. Be thorough — capture ALL key points, technical details, quotes, and actionable insights.
5. Include timestamps in [MM:SS] format where possible.
6. Do NOT return generic advice like "click Show Transcript" — return actual content.`,
            config: {
              temperature: 0.2,
              tools: [{ googleSearch: {} }],
            },
          });
          const text = result.text ?? '';
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
      const metadataContext = metadata ? formatMetadataAsContext(metadata) : '';
      const openaiPromise: Promise<TranscriptionResult | null> = (async () => {
        try {
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
      // When a candidate resolves to null (no usable transcript found), we
      // replace it with PENDING_FOREVER so Promise.race() skips it and waits
      // for a successful result from another candidate.
      const winner = await Promise.race(
        candidates.map(p => p.then(r => r ?? PENDING_FOREVER))
      ).catch(() => null);
      if (winner) return winner;
      // If the race produced no winner (all candidates resolved to null),
      // wait for all results and return the first usable one.
      const results = await Promise.allSettled(candidates);
      for (const r of results) {
        if (r.status === 'fulfilled' && r.value) return r.value;
      }
    }
  }

  // Strategy 4: Direct audio file transcription via OpenAI Whisper
  if (audioUrl && process.env.OPENAI_API_KEY) {
    try {
      // SSRF guard: reject non-public/internal URLs before any server-side fetch.
      try {
        await assertPublicHttpUrl(audioUrl);
      } catch (guardErr) {
        return {
          success: false,
          error: `Rejected audioUrl: ${guardErr instanceof Error ? guardErr.message : 'blocked'}`,
          transcript: '',
        };
      }

      const audioResponse = await fetch(audioUrl, { signal: AbortSignal.timeout(30_000) });
      if (!audioResponse.ok) {
        return {
          success: false,
          error: `Failed to fetch audio: ${audioResponse.status}`,
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

  // No strategy succeeded
  const hasKeys = !!(process.env.OPENAI_API_KEY || hasGeminiKey());
  return {
    success: false,
    error: hasKeys
      ? 'Could not transcribe video — all strategies failed'
      : 'No AI API key configured. Set OPENAI_API_KEY or GEMINI_API_KEY in Vercel environment variables.',
    transcript: '',
  };
}
