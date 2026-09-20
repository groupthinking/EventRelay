import {
  buildIdentityPack,
  isIdentityOnlyPack,
  type VideoPackV0Json,
} from '@/lib/video-pack';
import { getPackRecordWithMeta, type VideoPackRecord } from '@/lib/video-pack-store';

const PACK_ID_RE = /^vp:v0:[A-Za-z0-9_-]+$/;
const MAX_TRANSCRIPT_CHARS = 12_000;
const MAX_VISUAL_EVENTS = 24;
const MAX_SOP_STEPS = 32;
const MAX_ACTION_ITEMS = 24;

export type ChatPackBinding = {
  videoId: string;
  packId: string;
};

export type ChatPackGroundingFailure = {
  ok: false;
  status: number;
  answer: string;
  code: string;
};

export type ChatPackGroundingSuccess = {
  ok: true;
  pack: VideoPackV0Json;
  systemPrompt: string;
};

export type ChatPackGroundingResult = ChatPackGroundingFailure | ChatPackGroundingSuccess;

export function parseChatPackBinding(input: {
  video_id?: unknown;
  pack_id?: unknown;
}): ChatPackBinding | null {
  const rawVideo =
    typeof input.video_id === 'string' ? input.video_id.trim() : '';
  const rawPack = typeof input.pack_id === 'string' ? input.pack_id.trim() : '';

  let videoId = rawVideo;
  if (!videoId && rawPack && PACK_ID_RE.test(rawPack)) {
    videoId = rawPack.slice('vp:v0:'.length);
  }
  if (!videoId) return null;

  const expectedPackId = `vp:v0:${videoId}`;
  if (rawPack) {
    if (!PACK_ID_RE.test(rawPack) || rawPack !== expectedPackId) {
      return null;
    }
  }
  return { videoId, packId: rawPack || expectedPackId };
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max)}\n…[truncated]`;
}

export function buildVideoPackChatSystemPrompt(pack: VideoPackV0Json): string {
  const visualElements =
    pack.visual_context?.visual_elements?.slice(0, MAX_VISUAL_EVENTS) ?? [];
  const visualLines = visualElements.map(
    (event) =>
      `- ${event.timestamp}s ${event.element_type ?? 'scene'}: ${event.content}`,
  );
  const sopLines = pack.requirements.slice(0, MAX_SOP_STEPS).map(
    (step) => `- ${step.id}: ${step.title}${step.detail ? ` — ${step.detail}` : ''}`,
  );
  const actionLines = pack.action_items.slice(0, MAX_ACTION_ITEMS).map(
    (item) => `- ${item.id}: ${item.title}${item.description ? ` — ${item.description}` : ''}`,
  );
  const tools = pack.stack?.tools?.map((tool) => tool.name).filter(Boolean) ?? [];

  return [
    'You are UVAI assistant on a hosted Video Pack page (/d). Ground every answer ONLY in the pack JSON below.',
    'Do not claim G.A.T.E. PASS, deploy, or live ship receipts. If the pack lacks evidence, say so.',
    `packId: ${pack.id}`,
    `video_id: ${pack.video_id}`,
    `source_url: ${pack.source_url}`,
    `source_hash: ${pack.provenance.source_hash}`,
    '',
    '## Transcript',
    truncate(pack.transcript.full_text || '(empty)', MAX_TRANSCRIPT_CHARS),
    '',
    '## SOP / requirements',
    sopLines.length ? sopLines.join('\n') : '(none)',
    '',
    '## Visual events',
    visualLines.length ? visualLines.join('\n') : '(none)',
    '',
    '## Ship action_items',
    actionLines.length ? actionLines.join('\n') : '(none)',
    '',
    '## stack.tools',
    tools.length ? tools.join(', ') : '(none)',
  ].join('\n');
}

function packFailure(
  status: number,
  code: string,
  answer: string,
): ChatPackGroundingFailure {
  return { ok: false, status, answer, code };
}

function readyPackFromRecord(
  record: VideoPackRecord,
  binding: ChatPackBinding,
): ChatPackGroundingResult {
  if (record.state === 'processing') {
    return packFailure(
      409,
      'pack_processing',
      'This Video Pack is still extracting. Wait until the hosted page shows READY, then try again.',
    );
  }
  if (record.state === 'error') {
    return packFailure(
      422,
      'pack_error',
      'This Video Pack failed extraction. Live chat cannot ground on a broken pack.',
    );
  }
  const pack = record.pack;
  if (pack.video_id !== binding.videoId || pack.id !== binding.packId) {
    return packFailure(
      400,
      'pack_id_mismatch',
      'The pack id on this request does not match the video on this page. Refresh /d and try again.',
    );
  }
  if (isIdentityOnlyPack(pack)) {
    return packFailure(
      404,
      'pack_not_ready',
      'No ready Video Pack is stored for this video yet. Run pack extraction before using live chat.',
    );
  }
  return {
    ok: true,
    pack,
    systemPrompt: buildVideoPackChatSystemPrompt(pack),
  };
}

export async function resolveChatPackGrounding(
  binding: ChatPackBinding,
): Promise<ChatPackGroundingResult> {
  const identity = buildIdentityPack(binding.videoId);
  const lookup = await getPackRecordWithMeta(identity.provenance.source_hash);

  if (lookup.outcome === 'store_error') {
    return packFailure(
      503,
      'pack_store_error',
      'Video Pack storage is temporarily unavailable. Try again in a moment.',
    );
  }
  if (lookup.outcome === 'miss') {
    return packFailure(
      404,
      'pack_not_found',
      'No Video Pack found for this video. Live chat needs a ready pack on the same id as /d.',
    );
  }

  return readyPackFromRecord(lookup.record, binding);
}
