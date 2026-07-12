export function resolveVideoUrl(body: Record<string, unknown> | null | undefined): string {
  if (!body) return '';

  const value =
    body.url ??
    body.youtubeUrl ??
    body.videoUrl ??
    body.video_url;

  return typeof value === 'string' ? value.trim() : '';
}

