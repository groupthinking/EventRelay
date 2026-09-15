import { afterEach, describe, expect, it } from 'vitest';
import jpeg from 'jpeg-js';
import {
  captureKeyframeFrame,
  captureYoutubeStillFrame,
  cropStoryboardTile,
  parseStoryboardSpec,
  resetKeyframeFrameCaptureForTests,
  selectStoryboardTile,
  selectYoutubeStillIndex,
  youtubeStillUrls,
} from '@/lib/keyframe-frame-capture';

function solidJpeg(width: number, height: number, rgb: [number, number, number]): Uint8Array {
  const data = Buffer.alloc(width * height * 4);
  for (let i = 0; i < width * height; i += 1) {
    data[i * 4] = rgb[0];
    data[i * 4 + 1] = rgb[1];
    data[i * 4 + 2] = rgb[2];
    data[i * 4 + 3] = 255;
  }
  return new Uint8Array(jpeg.encode({ data, width, height }, 90).data);
}

describe('storyboard tile selection', () => {
  const spec = parseStoryboardSpec(
    'https://i.ytimg.com/sb/QjZ5ohr7sGA/storyboard3_L$L/$N.jpg?sigh=test|80#45#20#5#4#2000',
  );

  it('parses a YouTube storyboard spec without inventing a second format', () => {
    expect(spec).not.toBeNull();
    expect(spec?.levels[0]).toMatchObject({
      width: 80,
      height: 45,
      count: 20,
      cols: 5,
      rows: 4,
      intervalMs: 2000,
    });
  });

  it('picks the tile whose interval covers t_s', () => {
    expect(spec).not.toBeNull();
    const tile = selectStoryboardTile(spec!, 8);
    expect(tile).toEqual({
      url: 'https://i.ytimg.com/sb/QjZ5ohr7sGA/storyboard3_L0/M0.jpg?sigh=test',
      col: 4,
      row: 0,
      width: 80,
      height: 45,
    });
  });
});

describe('storyboard tile crop', () => {
  it('crops a real JPEG sprite to the selected tile', () => {
    const red = solidJpeg(80, 45, [200, 10, 10]);
    const decoded = jpeg.decode(Buffer.from(red), { useTArray: true });
    expect(decoded.width).toBe(80);
    expect(decoded.height).toBe(45);
    const cropped = cropStoryboardTile(red, {
      url: 'https://example.invalid/sprite.jpg',
      col: 0,
      row: 0,
      width: 80,
      height: 45,
    });
    expect(cropped).not.toBeNull();
    expect(cropped![0]).toBe(0xff);
    expect(cropped![1]).toBe(0xd8);
    const again = jpeg.decode(Buffer.from(cropped!), { useTArray: true });
    expect(again.width).toBe(80);
    expect(again.height).toBe(45);
  });
});

describe('YouTube public stills fallback', () => {
  afterEach(() => {
    resetKeyframeFrameCaptureForTests();
  });

  it('maps t_s into numbered stills 1-3, never default thumbs', () => {
    expect(selectYoutubeStillIndex(0, 90)).toBe(1);
    expect(selectYoutubeStillIndex(29, 90)).toBe(1);
    expect(selectYoutubeStillIndex(30, 90)).toBe(2);
    expect(selectYoutubeStillIndex(60, 90)).toBe(3);
    expect(selectYoutubeStillIndex(89, 90)).toBe(3);
    const urls = youtubeStillUrls('QjZ5ohr7sGA', 2);
    expect(urls.every((url) => /\/vi\/QjZ5ohr7sGA\/(hq)?2\.jpg$/.test(url))).toBe(true);
    expect(urls.join(' ')).not.toMatch(/hqdefault|maxresdefault|\/0\.jpg/);
  });

  it('downloads still JPEG bytes and never returns a ytimg URL', async () => {
    const jpegBytes = solidJpeg(16, 9, [10, 20, 200]);
    const fetched: string[] = [];
    const bytes = await captureYoutubeStillFrame({
      videoId: 'QjZ5ohr7sGA',
      t_s: 8,
      spanS: 30,
      fetchBytes: async (url) => {
        fetched.push(url);
        expect(url).toMatch(/\/vi\/QjZ5ohr7sGA\/(hq)?1\.jpg$/);
        expect(url).not.toMatch(/hqdefault|maxresdefault/);
        return jpegBytes;
      },
    });
    expect(bytes).not.toBeNull();
    expect(bytes![0]).toBe(0xff);
    expect(bytes![1]).toBe(0xd8);
    expect(fetched[0]).toMatch(/img\.youtube\.com|i\.ytimg\.com/);
    expect(JSON.stringify(bytes)).not.toMatch(/i\.ytimg\.com|img\.youtube\.com/);
  });

  it('uses stills bytes after storyboard miss and persists an app-served path', async () => {
    const jpegBytes = solidJpeg(16, 9, [12, 24, 180]);
    const result = await captureKeyframeFrame({
      videoId: 'QjZ5ohr7sGA',
      t_s: 8,
      spanS: 30,
      fetchStoryboardSpec: async () => null,
      fetchBytes: async (url) => {
        expect(url).not.toMatch(/hqdefault|maxresdefault/);
        if (/\/(hq)?1\.jpg$/.test(url)) return jpegBytes;
        return null;
      },
    });
    expect(result).not.toBeNull();
    expect(result!.source).toBe('stills');
    expect(result!.imagePath).toBe('/api/video/pack/frames/QjZ5ohr7sGA/8');
    expect(result!.bytes[0]).toBe(0xff);
    expect(result!.bytes[1]).toBe(0xd8);
    expect(JSON.stringify(result)).not.toMatch(/i\.ytimg\.com|img\.youtube\.com|hqdefault|maxresdefault/);
  });

  it('stays null when storyboard and stills both miss', async () => {
    const result = await captureKeyframeFrame({
      videoId: 'QjZ5ohr7sGA',
      t_s: 8,
      fetchStoryboardSpec: async () => null,
      fetchBytes: async () => null,
    });
    expect(result).toBeNull();
  });
});
