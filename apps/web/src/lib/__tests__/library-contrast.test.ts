import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const webSrc = join(dirname(fileURLToPath(import.meta.url)), '../..');

function readSource(relativePath: string) {
  return readFileSync(join(webSrc, relativePath), 'utf8');
}

function srgbToLinear(channel: number) {
  return channel <= 0.03928
    ? channel / 12.92
    : ((channel + 0.055) / 1.055) ** 2.4;
}

function relativeLuminance([r, g, b]: [number, number, number]) {
  const red = srgbToLinear(r);
  const green = srgbToLinear(g);
  const blue = srgbToLinear(b);
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrastRatio(first: [number, number, number], second: [number, number, number]) {
  const one = relativeLuminance(first);
  const two = relativeLuminance(second);
  const lighter = Math.max(one, two);
  const darker = Math.min(one, two);
  return (lighter + 0.05) / (darker + 0.05);
}

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '');
  return [
    Number.parseInt(clean.slice(0, 2), 16) / 255,
    Number.parseInt(clean.slice(2, 4), 16) / 255,
    Number.parseInt(clean.slice(4, 6), 16) / 255,
  ];
}

function rgbaToHexBlend(rgba: string, background: [number, number, number]): [number, number, number] {
  const parsed = rgba.match(/^rgba\((\d+),\s*(\d+),\s*(\d+),\s*([0-9.]+)\)$/);
  if (!parsed) throw new Error(`Unexpected rgba format: ${rgba}`);
  const [, r, g, b, alpha] = parsed;
  const fg: [number, number, number] = [
    Number.parseInt(r, 10) / 255,
    Number.parseInt(g, 10) / 255,
    Number.parseInt(b, 10) / 255,
  ];
  const a = Number.parseFloat(alpha);
  return [
    fg[0] * a + background[0] * (1 - a),
    fg[1] * a + background[1] * (1 - a),
    fg[2] * a + background[2] * (1 - a),
  ];
}

describe('library page text contrast', () => {
  const source = readSource('components/dashboard/DashboardCanvasView.tsx');
  const darkSurface = hexToRgb('#0f1419');

  it('keeps dim tab labels at WCAG AA contrast on dark surfaces', () => {
    const match = source.match(/color:\s*active\s*\?\s*accent\s*:\s*'([^']+)'/);
    expect(match).toBeTruthy();
    const dimColor = match?.[1] ?? '';
    const dimBlend = rgbaToHexBlend(dimColor, darkSurface);
    expect(contrastRatio(dimBlend, darkSurface)).toBeGreaterThanOrEqual(4.5);
  });

  it('keeps accent tab labels at WCAG AA contrast on dark surfaces', () => {
    const accents = [...source.matchAll(/accent:\s*'(#[0-9a-fA-F]{6})'/g)].map((entry) => entry[1]);
    expect(accents.length).toBeGreaterThan(0);
    for (const accent of accents) {
      expect(contrastRatio(hexToRgb(accent), darkSurface)).toBeGreaterThanOrEqual(4.5);
    }
  });
});
