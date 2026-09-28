import { selectXaiApiKey } from '@/lib/billing/grok-client';

/** Batch speech-to-text. Model is explicit so a silent default flip cannot change this path. */
export const XAI_STT_ENDPOINT = 'https://api.x.ai/v1/stt';
export const XAI_STT_MODEL = 'grok-voice-transcribe-2.0';

export type XaiSttResult = {
  text: string;
  duration: number;
  language?: string;
  model: typeof XAI_STT_MODEL;
};

export type XaiSttInput = {
  url?: string;
  file?: {
    bytes: Uint8Array;
    filename: string;
    contentType: string;
  };
};

type SttDeps = {
  fetch?: typeof fetch;
};

function redact(detail: string, apiKey: string): string {
  const redacted = apiKey ? detail.split(apiKey).join('[redacted]') : detail;
  return redacted.slice(0, 200);
}

function isSttPayload(value: unknown): value is { text: string; duration: number; language?: string } {
  if (!value || typeof value !== 'object') return false;
  const record = value as { text?: unknown; duration?: unknown; language?: unknown };
  if (typeof record.text !== 'string' || record.text.trim().length === 0) return false;
  if (typeof record.duration !== 'number' || !Number.isFinite(record.duration) || record.duration <= 0) {
    return false;
  }
  if (record.language !== undefined && typeof record.language !== 'string') return false;
  return true;
}

/**
 * POST multipart to xAI STT. `file` is appended last. `url` is a direct media URL,
 * never a Loom watch page.
 */
export async function transcribeWithXai(input: XaiSttInput, deps: SttDeps = {}): Promise<XaiSttResult> {
  const selected = selectXaiApiKey();
  if (!selected) {
    throw new Error('XAI_API_KEY missing fromEnv:none');
  }
  if (!input.file && !input.url) {
    throw new Error('xai_stt_input_missing');
  }
  const { apiKey, fromEnv } = selected;
  const form = new FormData();
  form.append('model', XAI_STT_MODEL);
  if (input.file) {
    const copy = new Uint8Array(input.file.bytes.byteLength);
    copy.set(input.file.bytes);
    form.append(
      'file',
      new Blob([copy], { type: input.file.contentType }),
      input.file.filename,
    );
  } else if (input.url) {
    form.append('url', input.url);
  }

  const fetchImpl = deps.fetch ?? fetch;
  const response = await fetchImpl(XAI_STT_ENDPOINT, {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}` },
    body: form,
    signal: AbortSignal.timeout(90_000),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `xai_stt_http_${response.status} fromEnv:${fromEnv}:${redact(detail, apiKey)}`,
    );
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch (err) {
    console.error('xai stt JSON parse failed', err);
    throw new Error(`xai_stt_invalid_json fromEnv:${fromEnv}`);
  }
  if (!isSttPayload(payload)) {
    throw new Error(`xai_stt_empty fromEnv:${fromEnv}`);
  }
  return {
    text: payload.text.trim(),
    duration: payload.duration,
    ...(typeof payload.language === 'string' ? { language: payload.language } : {}),
    model: XAI_STT_MODEL,
  };
}
