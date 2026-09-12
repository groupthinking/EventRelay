import { put as putVercelBlob } from '@vercel/blob';
import jpeg from 'jpeg-js';
import {
  applyKeyframeImageHonesty,
  isDurableCapturedImagePath,
  sanitizeKeyframeImagePath,
  type KeyframeImageHonestyPack,
} from '@/lib/keyframe-image-path';

export const KEYFRAME_JPEG_CONTENT_TYPE = 'image/jpeg' as const;
export const KEYFRAME_FRAME_CACHE_PREFIX = 'er:videopack:frame:v0:';

export type KeyframeFrameCaptureResult = {
  bytes: Uint8Array;
  contentType: typeof KEYFRAME_JPEG_CONTENT_TYPE;
  imagePath: string;
};

export type KeyframeFrameCapture = (input: {
  videoId: string;
  t_s: number;
}) => Promise<KeyframeFrameCaptureResult | null>;

export type StoryboardLevel = {
  urlTemplate: string;
  width: number;
  height: number;
  count: number;
  cols: number;
  rows: number;
  intervalMs: number;
};

export type StoryboardSpec = {
  levels: StoryboardLevel[];
};

export type StoryboardTile = {
  url: string;
  col: number;
  row: number;
  width: number;
  height: number;
};

type HydratePack = KeyframeImageHonestyPack & { video_id: string };

let captureForTests: KeyframeFrameCapture | null = null;
const memoryFrameCache = new Map<string, Uint8Array>();

export function setKeyframeFrameCaptureForTests(capture: KeyframeFrameCapture | null): void {
  captureForTests = capture;
}

export function resetKeyframeFrameCaptureForTests(): void {
  captureForTests = null;
  memoryFrameCache.clear();
}

export { isDurableCapturedImagePath, sanitizeKeyframeImagePath };

export function frameCacheKey(videoId: string, t_s: number): string {
  return `${KEYFRAME_FRAME_CACHE_PREFIX}${videoId}:${formatFrameT(t_s)}`;
}

export function formatFrameT(t_s: number): string {
  if (!Number.isFinite(t_s) || t_s < 0) return '0';
  return String(t_s);
}

export function appServedFramePath(videoId: string, t_s: number): string {
  return `/api/video/pack/frames/${videoId}/${formatFrameT(t_s)}`;
}

export function parseStoryboardSpec(spec: string): StoryboardSpec | null {
  const parts = spec.split('|').map((part) => part.trim()).filter((part) => part.length > 0);
  const template = parts[0];
  if (!template || !template.includes('$L') || !template.includes('$N')) {
    return null;
  }
  const levels: StoryboardLevel[] = [];
  for (const raw of parts.slice(1)) {
    const fields = raw.split('#');
    const width = Number(fields[0]);
    const height = Number(fields[1]);
    const count = Number(fields[2]);
    const cols = Number(fields[3]);
    const rows = Number(fields[4]);
    const intervalMs = Number(fields[5]);
    if (
      !(width > 0) ||
      !(height > 0) ||
      !(count > 0) ||
      !(cols > 0) ||
      !(rows > 0)
    ) {
      continue;
    }
    levels.push({
      urlTemplate: template,
      width,
      height,
      count,
      cols,
      rows,
      intervalMs: intervalMs > 0 ? intervalMs : 0,
    });
  }
  return levels.length > 0 ? { levels } : null;
}

export function selectStoryboardTile(
  spec: StoryboardSpec,
  t_s: number,
  durationS?: number,
): StoryboardTile | null {
  const level = spec.levels.reduce<StoryboardLevel | null>((best, current) => {
    if (!best) return current;
    return current.width * current.height > best.width * best.height ? current : best;
  }, null);
  if (!level) return null;
  const intervalMs =
    level.intervalMs > 0
      ? level.intervalMs
      : durationS && durationS > 0
        ? (durationS * 1000) / level.count
        : 5000;
  const frameIndex = Math.min(level.count - 1, Math.max(0, Math.floor((t_s * 1000) / intervalMs)));
  const framesPerSheet = level.cols * level.rows;
  const sheetIndex = Math.floor(frameIndex / framesPerSheet);
  const tileIndex = frameIndex % framesPerSheet;
  const row = Math.floor(tileIndex / level.cols);
  const col = tileIndex % level.cols;
  const url = level.urlTemplate.replace('$L', String(spec.levels.indexOf(level))).replace('$N', `M${sheetIndex}`);
  return {
    url,
    col,
    row,
    width: level.width,
    height: level.height,
  };
}

export function cropStoryboardTile(jpegBytes: Uint8Array, tile: StoryboardTile): Uint8Array | null {
  try {
    const decoded = jpeg.decode(Buffer.from(jpegBytes), { useTArray: true });
    const x = tile.col * tile.width;
    const y = tile.row * tile.height;
    if (x + tile.width > decoded.width || y + tile.height > decoded.height) {
      return null;
    }
    const pixels = new Uint8Array(tile.width * tile.height * 4);
    for (let row = 0; row < tile.height; row += 1) {
      const src = ((y + row) * decoded.width + x) * 4;
      const dest = row * tile.width * 4;
      pixels.set(decoded.data.subarray(src, src + tile.width * 4), dest);
    }
    const encoded = jpeg.encode(
      { data: pixels, width: tile.width, height: tile.height },
      80,
    );
    return new Uint8Array(encoded.data);
  } catch (error) {
    console.error('[keyframe-frame-capture] JPEG tile crop failed:', error);
    return null;
  }
}

export function rememberCapturedFrame(videoId: string, t_s: number, bytes: Uint8Array): void {
  memoryFrameCache.set(frameCacheKey(videoId, t_s), bytes);
}

export function recallCapturedFrame(videoId: string, t_s: number): Uint8Array | null {
  return memoryFrameCache.get(frameCacheKey(videoId, t_s)) ?? null;
}

async function persistCapturedJpeg(input: {
  videoId: string;
  t_s: number;
  bytes: Uint8Array;
}): Promise<string | null> {
  const token = process.env.BLOB_READ_WRITE_TOKEN?.trim();
  if (token) {
    try {
      const stored = await putVercelBlob(
        `videopack/${input.videoId}/keyframes/${formatFrameT(input.t_s)}.jpg`,
        Buffer.from(input.bytes),
        {
          access: 'public',
          token,
          contentType: KEYFRAME_JPEG_CONTENT_TYPE,
        },
      );
      if (isDurableCapturedImagePath(stored.url)) {
        rememberCapturedFrame(input.videoId, input.t_s, input.bytes);
        return stored.url;
      }
    } catch (error) {
      console.error('[keyframe-frame-capture] Blob persist failed:', error);
    }
  }
  rememberCapturedFrame(input.videoId, input.t_s, input.bytes);
  return appServedFramePath(input.videoId, input.t_s);
}

function extractStoryboardSpec(payload: unknown): { spec: string; durationS?: number } | null {
  if (payload === null || typeof payload !== 'object') return null;
  const root = payload as Record<string, unknown>;
  const boards = root.storyboards;
  if (boards !== null && typeof boards === 'object') {
    const renderer = (boards as Record<string, unknown>).playerStoryboardSpecRenderer;
    if (renderer !== null && typeof renderer === 'object') {
      const spec = (renderer as Record<string, unknown>).spec;
      if (typeof spec === 'string' && spec.includes('$L')) {
        const details = root.videoDetails;
        const durationRaw =
          details !== null && typeof details === 'object'
            ? (details as Record<string, unknown>).lengthSeconds
            : undefined;
        const durationS = typeof durationRaw === 'string' ? Number(durationRaw) : undefined;
        return { spec, durationS: Number.isFinite(durationS) ? durationS : undefined };
      }
    }
  }
  return null;
}

async function fetchJson(url: string, init: RequestInit): Promise<unknown> {
  const response = await fetch(url, { ...init, signal: init.signal ?? AbortSignal.timeout(12_000) });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function fetchStoryboardFromPlayer(videoId: string): Promise<{ spec: string; durationS?: number } | null> {
  const embed = await fetch(`https://www.youtube.com/embed/${videoId}`, {
    headers: {
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    },
    signal: AbortSignal.timeout(12_000),
  });
  if (!embed.ok) return null;
  const html = await embed.text();
  const cfgMatch = html.match(/ytcfg\.set\((\{.*?\})\);/);
  if (!cfgMatch?.[1]) return null;
  const cfg = JSON.parse(cfgMatch[1]) as {
    INNERTUBE_API_KEY?: string;
    INNERTUBE_CONTEXT?: { client?: Record<string, unknown> };
  };
  const key = cfg.INNERTUBE_API_KEY;
  const client = cfg.INNERTUBE_CONTEXT?.client;
  if (!key || !client) return null;
  const player = await fetchJson(`https://www.youtube.com/youtubei/v1/player?key=${key}&prettyPrint=false`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
      Origin: 'https://www.youtube.com',
      Referer: `https://www.youtube.com/embed/${videoId}`,
    },
    body: JSON.stringify({
      context: { client },
      videoId,
      contentCheckOk: true,
      racyCheckOk: true,
    }),
  });
  return extractStoryboardSpec(player);
}

export async function captureStoryboardFrame(input: {
  videoId: string;
  t_s: number;
  fetchSpec?: () => Promise<{ spec: string; durationS?: number } | null>;
  fetchBytes?: (url: string) => Promise<Uint8Array | null>;
}): Promise<Uint8Array | null> {
  const specPayload = input.fetchSpec
    ? await input.fetchSpec()
    : await fetchStoryboardFromPlayer(input.videoId).catch((error) => {
        console.error('[keyframe-frame-capture] storyboard spec fetch failed:', error);
        return null;
      });
  if (!specPayload) return null;
  const parsed = parseStoryboardSpec(specPayload.spec);
  if (!parsed) return null;
  const tile = selectStoryboardTile(parsed, input.t_s, specPayload.durationS);
  if (!tile) return null;
  const fetchBytes =
    input.fetchBytes ??
    (async (url: string) => {
      const response = await fetch(url, { signal: AbortSignal.timeout(12_000) });
      if (!response.ok) return null;
      return new Uint8Array(await response.arrayBuffer());
    });
  const sheet = await fetchBytes(tile.url);
  if (!sheet || sheet.length < 4 || sheet[0] !== 0xff || sheet[1] !== 0xd8) {
    return null;
  }
  return cropStoryboardTile(sheet, tile);
}

async function defaultCapture(input: { videoId: string; t_s: number }): Promise<KeyframeFrameCaptureResult | null> {
  if (process.env.VITEST && !captureForTests) {
    return null;
  }
  const bytes = await captureStoryboardFrame(input);
  if (!bytes) return null;
  const imagePath = await persistCapturedJpeg({ videoId: input.videoId, t_s: input.t_s, bytes });
  if (!imagePath || !isDurableCapturedImagePath(imagePath)) return null;
  return { bytes, contentType: KEYFRAME_JPEG_CONTENT_TYPE, imagePath };
}

export async function hydrateKeyframeImages<T extends HydratePack>(pack: T): Promise<T> {
  const capture = captureForTests ?? defaultCapture;
  const keyframes = [];
  for (const frame of pack.keyframes) {
    const existing = sanitizeKeyframeImagePath(frame.image_path);
    if (existing) {
      keyframes.push({ ...frame, image_path: existing });
      continue;
    }
    try {
      const captured = await capture({ videoId: pack.video_id, t_s: frame.t_s });
      if (captured?.bytes?.length && isDurableCapturedImagePath(captured.imagePath)) {
        rememberCapturedFrame(pack.video_id, frame.t_s, captured.bytes);
        keyframes.push({ ...frame, image_path: captured.imagePath });
      } else {
        keyframes.push({ ...frame, image_path: null });
      }
    } catch (error) {
      console.error('[keyframe-frame-capture] hydrate capture failed:', error);
      keyframes.push({ ...frame, image_path: null });
    }
  }
  return applyKeyframeImageHonesty({ ...pack, keyframes });
}

export async function loadCapturedFrameJpeg(videoId: string, t_s: number): Promise<Uint8Array | null> {
  const cached = recallCapturedFrame(videoId, t_s);
  if (cached) return cached;
  const captured = await (captureForTests ?? defaultCapture)({ videoId, t_s });
  if (!captured?.bytes?.length) return null;
  rememberCapturedFrame(videoId, t_s, captured.bytes);
  return captured.bytes;
}
