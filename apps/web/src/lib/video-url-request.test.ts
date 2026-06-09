import { describe, expect, it } from 'vitest';
import { resolveVideoUrl } from './video-url-request';

describe('resolveVideoUrl', () => {
  it.each([
    ['url', { url: ' https://youtu.be/a ' }],
    ['youtubeUrl', { youtubeUrl: ' https://youtu.be/b ' }],
    ['videoUrl', { videoUrl: ' https://youtu.be/c ' }],
    ['video_url', { video_url: ' https://youtu.be/d ' }],
  ])('accepts %s as a video URL field', (_field, body) => {
    expect(resolveVideoUrl(body)).toMatch(/^https:\/\/youtu\.be\//);
  });

  it('returns an empty string when no supported field is provided', () => {
    expect(resolveVideoUrl({ youtube_url: 'https://youtu.be/misspelled' })).toBe('');
  });
});

