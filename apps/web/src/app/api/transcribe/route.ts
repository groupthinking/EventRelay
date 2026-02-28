import OpenAI from 'openai';
import { NextResponse } from 'next/server';
import { fetchYouTubeMetadata, formatMetadataAsContext } from '@/lib/youtube-metadata';
import { getGeminiClient, hasGeminiKey } from '@/lib/gemini-client';

let _openai: OpenAI | null = null;
function getOpenAI() {
  if (!_openai) _openai = new OpenAI();
  return _openai;
}

// Backend URL with validation - skip if not a valid URL
const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

/**
 * POST /api/transcribe
 *
 * Multi-strategy transcript extraction:
 *   1. YouTube captions via backend (fast + free)
 *   2. OpenAI Responses API with web_search (finds transcripts online)
 *   3. Gemini fallback (if OpenAI unavailable)
 *   4. Direct audio STT via OpenAI Whisper
 */
export async function POST(request: Request) {
  try {
    const { url, audioUrl, language = 'en' } = await request.json();

    if (!url && !audioUrl) {
      return NextResponse.json(
        { error: 'url or audioUrl is required' },
        { status: 400 },
      );
    }

    // Strategy 1: Try YouTube transcript API via backend (fast + free)
    if (url && !audioUrl && BACKEND_AVAILABLE) {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 8_000);

        const ytResponse = await fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
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
              return NextResponse.json({
                success: true,
                transcript: fullText,
                segments,
                source: 'youtube',
                wordCount: fullText.split(/\s+/).length,
              });
            }
          }

          // Handle transcript as { text: string }
          const transcriptText =
            typeof result.transcript === 'string'
              ? result.transcript
              : result.transcript?.text;
          if (typeof transcriptText === 'string' && transcriptText.length > 50) {
            return NextResponse.json({
              success: true,
              transcript: transcriptText,
              source: 'youtube',
              wordCount: transcriptText.split(/\s+/).length,
            });
          }
        }
      } catch {
        console.log('YouTube transcript unavailable, falling back to AI providers');
      }
    }

    // Fetch YouTube metadata (description, chapters, title) — used by strategies below
    let metadata: Awaited<ReturnType<typeof fetchYouTubeMetadata>> = null;
    if (url) {
      try {
        metadata = await fetchYouTubeMetadata(url);
      } catch {
        console.log('YouTube metadata fetch failed, continuing without');
      }
    }

    // Strategy 2: Gemini with Google Search grounding (PRIMARY for YouTube)
    // Uses Google Search to find actual transcript content, descriptions, and chapters
    if (url && !audioUrl && hasGeminiKey()) {
      try {
        const ai = getGeminiClient();
        const metadataContext = metadata ? formatMetadataAsContext(metadata) : '';

        const result = await ai.models.generateContent({
          model: 'gemini-2.5-flash',
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
          return NextResponse.json({
            success: true,
            transcript: text,
            source: 'gemini-search',
            wordCount: text.split(/\s+/).length,
            metadata: metadata ? {
              title: metadata.title,
              channel: metadata.channel,
              chapters: metadata.chapters,
            } : undefined,
          });
        }
      } catch (e) {
        console.warn('Gemini Google Search transcript failed:', e);
      }
    }

    // Strategy 3: OpenAI Responses API with web_search (fallback)
    if (url && !audioUrl && process.env.OPENAI_API_KEY) {
      try {
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
        const isGarbage = text.toLowerCase().includes('click show transcript') ||
          text.toLowerCase().includes('click on the three dots') ||
          text.toLowerCase().includes('steps to find') ||
          (text.length < 300 && text.includes('transcript'));

        if (text.length > 100 && !isGarbage) {
          return NextResponse.json({
            success: true,
            transcript: text,
            source: 'openai-web-search',
            wordCount: text.split(/\s+/).length,
          });
        }
      } catch (e) {
        console.warn('OpenAI web_search transcript failed:', e);
      }
    }

    // Strategy 4: Direct audio file transcription via OpenAI Whisper
    if (audioUrl && process.env.OPENAI_API_KEY) {
      const audioResponse = await fetch(audioUrl);
      if (!audioResponse.ok) {
        return NextResponse.json(
          { error: `Failed to fetch audio: ${audioResponse.status}` },
          { status: 400 },
        );
      }

      const audioBlob = await audioResponse.blob();
      const audioFile = new File([audioBlob], 'audio.mp3', { type: 'audio/mpeg' });

      const transcription = await getOpenAI().audio.transcriptions.create({
        model: 'gpt-4o-mini-transcribe',
        file: audioFile,
        language,
      });

      return NextResponse.json({
        success: true,
        transcript: transcription.text,
        source: 'openai-stt',
        wordCount: transcription.text.split(/\s+/).length,
      });
    }

    // No strategy succeeded
    const hasKeys = !!(process.env.OPENAI_API_KEY || hasGeminiKey());
    return NextResponse.json({
      success: false,
      error: hasKeys
        ? 'Could not transcribe video — all strategies failed'
        : 'No AI API key configured. Set OPENAI_API_KEY or GEMINI_API_KEY in Vercel environment variables.',
      transcript: '',
    });
  } catch (error) {
    console.error('Transcription error:', error);
    const message = error instanceof Error ? error.message : String(error);

    return NextResponse.json({
      success: false,
      error: message.includes('API key')
        ? 'AI API key not configured. Set OPENAI_API_KEY or GEMINI_API_KEY.'
        : message,
      transcript: '',
    });
  }
}
