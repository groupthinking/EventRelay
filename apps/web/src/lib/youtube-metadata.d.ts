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
    chapters: {
        time: string;
        title: string;
    }[];
}
/**
 * Extract YouTube video ID from various URL formats.
 */
export declare function extractVideoId(url: string): string | null;
/**
 * Fetch YouTube video metadata by scraping the watch page.
 * No API key required.
 */
export declare function fetchYouTubeMetadata(url: string): Promise<YouTubeMetadata | null>;
/**
 * Format metadata into a rich text block suitable for AI analysis.
 */
export declare function formatMetadataAsContext(meta: YouTubeMetadata): string;
