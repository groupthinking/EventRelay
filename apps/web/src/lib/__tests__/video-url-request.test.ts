import { describe, it, expect } from 'vitest';
import {
  isAllowedYoutubeUrl,
  resolveVideoUrl,
  resolveAllowedVideoUrl,
} from '@/lib/video-url-request';

describe('isAllowedYoutubeUrl', () => {
  it('accepts standard watch URLs', () => {
    expect(isAllowedYoutubeUrl('https://www.youtube.com/watch?v=jNQXAC9IVRw')).toBe(true);
    expect(isAllowedYoutubeUrl('https://youtube.com/watch?v=jNQXAC9IVRw')).toBe(true);
  });

  it('accepts youtu.be and shorts', () => {
    expect(isAllowedYoutubeUrl('https://youtu.be/jNQXAC9IVRw')).toBe(true);
    expect(isAllowedYoutubeUrl('https://www.youtube.com/shorts/jNQXAC9IVRw')).toBe(true);
  });

  it('rejects SSRF-style hosts with 11-char token', () => {
    expect(isAllowedYoutubeUrl('http://169.254.169.254/aaaaaaaaaaa')).toBe(false);
    expect(isAllowedYoutubeUrl('http://127.0.0.1/aaaaaaaaaaa')).toBe(false);
    expect(isAllowedYoutubeUrl('https://evil.example/watch?v=aaaaaaaaaaa')).toBe(false);
  });

  it('rejects leading-dash yt-dlp injection tokens', () => {
    expect(isAllowedYoutubeUrl('--config-locations=/aaaaaaaaaaa')).toBe(false);
    expect(isAllowedYoutubeUrl('-o')).toBe(false);
  });

  it('rejects empty and non-youtube', () => {
    expect(isAllowedYoutubeUrl('')).toBe(false);
    expect(isAllowedYoutubeUrl('https://vimeo.com/12345678901')).toBe(false);
  });
});

describe('resolveAllowedVideoUrl', () => {
  it('returns empty for disallowed', () => {
    expect(resolveAllowedVideoUrl({ url: 'http://169.254.169.254/aaaaaaaaaaa' })).toBe('');
  });

  it('returns url for allowed', () => {
    const u = 'https://www.youtube.com/watch?v=jNQXAC9IVRw';
    expect(resolveAllowedVideoUrl({ url: u })).toBe(u);
  });

  it('resolveVideoUrl still extracts raw string', () => {
    expect(resolveVideoUrl({ video_url: '  x  ' })).toBe('x');
  });
});
