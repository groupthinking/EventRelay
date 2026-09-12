/** Honest-green: every keyframe has a durable captured image, not a Gemini/thumb invent. */
export const KEYFRAME_IMAGES_OK = 'ok' as const;
export const KEYFRAME_IMAGES_OK_NOTE =
  'Keyframe images OK: captured frames persisted (not Gemini/YouTube-thumb invented).';

/** Honest gap when at least one keyframe still lacks a captured asset. */
export const KEYFRAME_IMAGES_PARTIAL = 'partial' as const;
export const KEYFRAME_IMAGES_PARTIAL_NOTE =
  'Keyframe images PARTIAL: no frame-capture/upload path; image_path left null (not invented).';

const YOUTUBE_ID = /^[A-Za-z0-9_-]{11}$/;
const FRAME_T = /^(?:0|[1-9]\d*)(?:\.\d+)?$/;
const APP_SERVED_FRAME =
  /^\/api\/video\/pack\/frames\/([A-Za-z0-9_-]{11})\/((?:0|[1-9]\d*)(?:\.\d+)?)$/;
const APP_SERVED_FRAME_ABS =
  /^https:\/\/(?:uvai\.io|www\.uvai\.io)\/api\/video\/pack\/frames\/([A-Za-z0-9_-]{11})\/((?:0|[1-9]\d*)(?:\.\d+)?)$/;
const VERCEL_BLOB =
  /^https:\/\/[a-z0-9.-]+\.(?:public\.)?blob\.vercel-storage\.com\/.+/i;

export type KeyframeImageHonestyPack = {
  keyframes: Array<{ t_s: number; image_path?: string | null; desc?: string | null }>;
  metrics: Record<string, number | string>;
  provenance: {
    notes: string;
    source_hash: string;
    created_at: string;
    tool_versions: Record<string, string>;
  };
};

export function isDurableCapturedImagePath(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  const path = value.trim();
  if (!path) return false;
  if (/i\.ytimg\.com|hqdefault|maxresdefault|\/tmp\/|example\.com/i.test(path)) {
    return false;
  }
  if (VERCEL_BLOB.test(path)) {
    return true;
  }
  const app = APP_SERVED_FRAME.exec(path) ?? APP_SERVED_FRAME_ABS.exec(path);
  if (!app) return false;
  return YOUTUBE_ID.test(app[1] ?? '') && FRAME_T.test(app[2] ?? '');
}

export function sanitizeKeyframeImagePath(value: unknown): string | null {
  if (!isDurableCapturedImagePath(value)) return null;
  return value.trim();
}

function withoutNote(notes: string, note: string): string {
  return notes.split(note).join('').replace(/\s+/g, ' ').trim();
}

function withNote(notes: string, note: string): string {
  if (notes.includes(note)) return notes;
  return `${notes} ${note}`.trim();
}

export function applyKeyframeImageHonesty<T extends KeyframeImageHonestyPack>(
  pack: T,
): T & { metrics: Record<string, number | string> } {
  const keyframes = pack.keyframes.map((frame) => ({
    ...frame,
    image_path: sanitizeKeyframeImagePath(frame.image_path),
  }));
  if (keyframes.length === 0) {
    return { ...pack, keyframes };
  }
  const missingImages = keyframes.some((frame) => !frame.image_path);
  if (!missingImages) {
    return {
      ...pack,
      keyframes,
      metrics: {
        ...pack.metrics,
        keyframes_images: KEYFRAME_IMAGES_OK,
      },
      provenance: {
        ...pack.provenance,
        notes: withNote(withoutNote(pack.provenance.notes, KEYFRAME_IMAGES_PARTIAL_NOTE), KEYFRAME_IMAGES_OK_NOTE),
      },
    };
  }
  return {
    ...pack,
    keyframes,
    metrics: {
      ...pack.metrics,
      keyframes_images: KEYFRAME_IMAGES_PARTIAL,
    },
    provenance: {
      ...pack.provenance,
      notes: withNote(withoutNote(pack.provenance.notes, KEYFRAME_IMAGES_OK_NOTE), KEYFRAME_IMAGES_PARTIAL_NOTE),
    },
  };
}
