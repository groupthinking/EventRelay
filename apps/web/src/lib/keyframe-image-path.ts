/** Honest-green: every keyframe has a durable captured image, not a Gemini/thumb invent. */
export const KEYFRAME_IMAGES_OK = 'ok' as const;
export const KEYFRAME_IMAGES_OK_NOTE =
  'Keyframe images OK: captured frames persisted (not Gemini/YouTube-thumb invented).';
export const KEYFRAME_IMAGES_OK_STORYBOARD_NOTE =
  'Keyframe images OK: storyboard tiles captured and persisted (not Gemini/YouTube-thumb invented).';
export const KEYFRAME_IMAGES_OK_STILLS_NOTE =
  'Keyframe images OK: YouTube public stills captured as JPEG bytes after storyboard miss (ytimg URLs not stored).';
export const KEYFRAME_IMAGES_OK_MIXED_NOTE =
  'Keyframe images OK: mix of storyboard tiles and YouTube public stills captured as JPEG bytes (ytimg URLs not stored).';

/** Honest gap when at least one keyframe still lacks a captured asset. */
export const KEYFRAME_IMAGES_PARTIAL = 'partial' as const;
export const KEYFRAME_IMAGES_PARTIAL_NOTE =
  'Keyframe images PARTIAL: storyboard and stills capture missed; image_path left null (not invented).';
/** Pre-#1908 B2 note — strip on re-seal so GET hydrate does not stack both texts. */
export const KEYFRAME_IMAGES_PARTIAL_NOTE_LEGACY =
  'Keyframe images PARTIAL: no frame-capture/upload path; image_path left null (not invented).';

export type KeyframeImageCaptureSource = 'storyboard' | 'stills';
export type KeyframeImagesSourceMetric = KeyframeImageCaptureSource | 'mixed';

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
  if (
    /i\.ytimg\.com|img\.youtube\.com|hqdefault|maxresdefault|\/tmp\/|example\.com/i.test(
      path,
    )
  ) {
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

const HONESTY_NOTES = [
  KEYFRAME_IMAGES_OK_NOTE,
  KEYFRAME_IMAGES_OK_STORYBOARD_NOTE,
  KEYFRAME_IMAGES_OK_STILLS_NOTE,
  KEYFRAME_IMAGES_OK_MIXED_NOTE,
  KEYFRAME_IMAGES_PARTIAL_NOTE,
  KEYFRAME_IMAGES_PARTIAL_NOTE_LEGACY,
] as const;

function stripHonestyNotes(notes: string): string {
  return HONESTY_NOTES.reduce((acc, note) => withoutNote(acc, note), notes);
}

function preservedOkNote(notes: string): string {
  if (notes.includes(KEYFRAME_IMAGES_OK_MIXED_NOTE)) return KEYFRAME_IMAGES_OK_MIXED_NOTE;
  if (notes.includes(KEYFRAME_IMAGES_OK_STILLS_NOTE)) return KEYFRAME_IMAGES_OK_STILLS_NOTE;
  if (notes.includes(KEYFRAME_IMAGES_OK_STORYBOARD_NOTE)) return KEYFRAME_IMAGES_OK_STORYBOARD_NOTE;
  return KEYFRAME_IMAGES_OK_NOTE;
}

function sourceMetricFromSet(
  sources: ReadonlySet<KeyframeImageCaptureSource>,
): KeyframeImagesSourceMetric {
  if (sources.size > 1) return 'mixed';
  const only = [...sources][0];
  switch (only) {
    case 'storyboard':
      return 'storyboard';
    case 'stills':
      return 'stills';
    case undefined:
      return 'storyboard';
    default: {
      const _exhaustive: never = only;
      return _exhaustive;
    }
  }
}

export function keyframeImagesOkNote(
  sources: ReadonlySet<KeyframeImageCaptureSource>,
): string {
  const hasStoryboard = sources.has('storyboard');
  const hasStills = sources.has('stills');
  if (hasStoryboard && hasStills) return KEYFRAME_IMAGES_OK_MIXED_NOTE;
  if (hasStills) return KEYFRAME_IMAGES_OK_STILLS_NOTE;
  if (hasStoryboard) return KEYFRAME_IMAGES_OK_STORYBOARD_NOTE;
  return KEYFRAME_IMAGES_OK_NOTE;
}

export function applyKeyframeImageSourceNotes<T extends KeyframeImageHonestyPack>(
  pack: T,
  sources: Iterable<KeyframeImageCaptureSource>,
): T {
  const captured = new Set<KeyframeImageCaptureSource>(sources);
  const missingImages = pack.keyframes.some(
    (frame) => !sanitizeKeyframeImagePath(frame.image_path),
  );
  if (pack.keyframes.length === 0 || missingImages || captured.size === 0) {
    return pack;
  }
  const note = keyframeImagesOkNote(captured);
  const source = sourceMetricFromSet(captured);
  return {
    ...pack,
    metrics: {
      ...pack.metrics,
      keyframes_images: KEYFRAME_IMAGES_OK,
      keyframes_images_source: source,
    },
    provenance: {
      ...pack.provenance,
      notes: withNote(stripHonestyNotes(pack.provenance.notes), note),
    },
  };
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
    const okNote = preservedOkNote(pack.provenance.notes);
    return {
      ...pack,
      keyframes,
      metrics: {
        ...pack.metrics,
        keyframes_images: KEYFRAME_IMAGES_OK,
      },
      provenance: {
        ...pack.provenance,
        notes: withNote(stripHonestyNotes(pack.provenance.notes), okNote),
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
      notes: withNote(stripHonestyNotes(pack.provenance.notes), KEYFRAME_IMAGES_PARTIAL_NOTE),
    },
  };
}
