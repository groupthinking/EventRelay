import { join } from 'node:path';
import { z } from 'zod';
import { canonicalJson, sha256, type Manifest } from './contract.ts';
import { readLocalFile } from './local-files.ts';

export const viewports = [
  { width: 720, height: 900 },
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
] as const;
export const themes = ['light', 'dark'] as const;
export const dimensions = (width: number, height: number) => `${width}x${height}`;
export const recordingPath = (theme: string, size: string) => `recordings/${theme}-${size}.webm`;
export const screenshotPath = (view: string, theme: string, size: string) => `screenshots/${view}-${theme}-${size}.png`;

export function supportedViews(manifest: Manifest): Array<'video' | 'spatial'> {
  const checks = manifest.requiredCheckIds;
  const views: Array<'video' | 'spatial'> = [];
  if (checks.includes('youtube-attachment') || checks.includes('summary-renderer')) views.push('video');
  if (checks.includes('box-renderer')) views.push('spatial');
  return views;
}

export function captureInventory(directory: string, manifest: Manifest) {
  const files = viewports.flatMap(({ width, height }) => themes.flatMap((theme) => {
    const size = dimensions(width, height);
    return [...supportedViews(manifest).map((view) => screenshotPath(view, theme, size)), recordingPath(theme, size)];
  })).map((path) => {
    const data = readLocalFile(join(directory, path), 64 * 1024 * 1024);
    const signature = path.endsWith('.png') ? '89504e470d0a1a0a' : '1a45dfa3';
    if (!data.subarray(0, signature.length / 2).equals(Buffer.from(signature, 'hex'))) {
      throw new Error(`Invalid browser capture format: ${path}`);
    }
    return { path, bytes: data.byteLength, sha256: sha256(data) };
  });
  return { version: 'video-reconstruction.captures.v1', files };
}

export function captureCheckDetails(inventory: ReturnType<typeof captureInventory>, profileFileSha256: string): string {
  return `Inspected all supported views at 720×900, 1440×900 and 1920×1080 in light and dark. Capture inventory SHA-256: ${sha256(canonicalJson(inventory))}. Profile file SHA-256: ${profileFileSha256}`;
}

export function verifyCaptures(directory: string, inventory: unknown, manifest: Manifest, details: string | undefined, profileFileSha256: string): void {
  const saved = z.object({ version: z.literal('video-reconstruction.captures.v1'), files: z.array(z.unknown()) })
    .strict().parse(inventory);
  const actual = captureInventory(directory, manifest);
  if (canonicalJson(saved) !== canonicalJson(actual) || details !== captureCheckDetails(actual, profileFileSha256)) {
    throw new Error('Browser capture inventory binding mismatch');
  }
}
