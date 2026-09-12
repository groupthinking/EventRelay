import { describe, expect, it } from 'vitest';
import jpeg from 'jpeg-js';
import {
  cropStoryboardTile,
  parseStoryboardSpec,
  selectStoryboardTile,
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
