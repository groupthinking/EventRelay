/**
 * YouTube metadata fetcher — extracts title, description, chapters,
 * and channel info from YouTube videos without requiring an API key.
 *
 * Scrapes the YouTube page for `og:` meta tags and the embedded
 * `shortDescription` JSON field, then parses chapter timestamps
 * from the description text.
 */

export interface YouTubeMetadata {
  videoId: string;
  title: string;
  channel: string;
  description: string;
  chapters: { time: string; title: string }[];
}

/**
 * Extract YouTube video ID from various URL formats.
 */
export function extractVideoId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})/,
    /(?:youtu\.be\/)([a-zA-Z0-9_-]{11})/,
    /(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
    /(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/,
  ];
  for (const p of patterns) {
    const m = url.match(p);
    if (m) return m[1];
  }
  return null;
}

/**
 * Parse chapter timestamps from a YouTube description.
 * Chapters appear as lines like "0:00 Introduction" or "1:23:45 Deep Dive".
 */
function parseChapters(description: string): { time: string; title: string }[] {
  const lines = description.split('\n');
  const chapters: { time: string; title: string }[] = [];
  const chapterPattern = /^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$/;

  for (const line of lines) {
    const m = line.trim().match(chapterPattern);
    if (m) {
      chapters.push({ time: m[1], title: m[2].trim() });
    }
  }
  return chapters;
}

/**
 * Fetch YouTube video metadata by scraping the watch page.
 * No API key required.
 */
export async function fetchYouTubeMetadata(url: string): Promise<YouTubeMetadata | null> {
  const videoId = extractVideoId(url);
  if (!videoId) return null;

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10_000);

    const response = await fetch(`https://www.youtube.com/watch?v=${videoId}`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; EventRelay/2.0)',
        'Accept-Language': 'en-US,en;q=0.9',
      },
      signal: controller.signal,
    }).finally(() => clearTimeout(timeout));

    if (!response.ok) return null;

    const html = await response.text();

    // Extract title from og:title
    const titleMatch = html.match(/<meta property="og:title" content="([^"]+)"/);
    const title = titleMatch?.[1] || '';

    // Extract shortDescription from embedded JSON (contains full description)
    let description = '';
    const descMatch = html.match(/"shortDescription":"((?:[^"\\]|\\.)*)"/);
    if (descMatch) {
      try {
        description = JSON.parse(`"${descMatch[1]}"`);
      } catch {
        description = descMatch[1].replace(/\\n/g, '\n').replace(/\\"/g, '"');
      }
    } else {
      // Fallback to og:description (truncated)
      const ogDesc = html.match(/<meta property="og:description" content="([^"]+)"/);
      description = ogDesc?.[1] || '';
    }

    // Extract channel name
    const channelMatch = html.match(/"ownerChannelName":"([^"]+)"/);
    const channel = channelMatch?.[1] || '';

    const chapters = parseChapters(description);

    return { videoId, title, channel, description, chapters };
  } catch (e) {
    console.warn('[YouTube] Metadata fetch failed:', e);
    return null;
  }
}

/**
 * Format metadata into a rich text block suitable for AI analysis.
 */
export function formatMetadataAsContext(meta: YouTubeMetadata): string {
  let context = `VIDEO TITLE: ${meta.title}\n`;
  context += `CHANNEL: ${meta.channel}\n\n`;
  context += `DESCRIPTION:\n${meta.description}\n`;

  if (meta.chapters.length > 0) {
    context += `\nCHAPTERS:\n`;
    for (const ch of meta.chapters) {
      context += `  ${ch.time} — ${ch.title}\n`;
    }
  }

  return context;
}
