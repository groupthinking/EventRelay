import { describe, expect, it, vi, beforeEach } from 'vitest';
import {
  buildVideoPackChatSystemPrompt,
  parseChatPackBinding,
  resolveChatPackGrounding,
} from '@/lib/chat-pack-grounding';
import { buildIdentityPack, identityHash } from '@/lib/video-pack';
import { QJ_SOP_STEPS, QJ_TRANSCRIPT, QJ_VIDEO_ID } from '@/lib/__fixtures__/qj-z5ohr7sga-emit';
import * as store from '@/lib/video-pack-store';

describe('chat-pack-grounding', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('parses matching video_id and pack_id', () => {
    expect(
      parseChatPackBinding({
        video_id: QJ_VIDEO_ID,
        pack_id: `vp:v0:${QJ_VIDEO_ID}`,
      }),
    ).toEqual({ videoId: QJ_VIDEO_ID, packId: `vp:v0:${QJ_VIDEO_ID}` });
  });

  it('fails closed on pack/video mismatch', () => {
    expect(
      parseChatPackBinding({
        video_id: QJ_VIDEO_ID,
        pack_id: 'vp:v0:otherVideo99',
      }),
    ).toBeNull();
  });

  it('includes packId and transcript in system prompt', () => {
    const pack = buildIdentityPack(QJ_VIDEO_ID);
    pack.transcript = QJ_TRANSCRIPT;
    pack.requirements = QJ_SOP_STEPS.map((step) => ({
      id: step.id,
      title: step.title,
      detail: step.description,
    }));
    pack.id = `vp:v0:${QJ_VIDEO_ID}`;
    const prompt = buildVideoPackChatSystemPrompt(pack);
    expect(prompt).toContain(`packId: vp:v0:${QJ_VIDEO_ID}`);
    expect(prompt).toContain('five flat tires');
    expect(prompt).toContain('Do not claim G.A.T.E. PASS');
  });

  it('returns not_found when store misses', async () => {
    vi.spyOn(store, 'getPackRecordWithMeta').mockResolvedValue({
      outcome: 'miss',
      store: { backend: 'memory', ok: true },
    });
    const result = await resolveChatPackGrounding({
      videoId: QJ_VIDEO_ID,
      packId: `vp:v0:${QJ_VIDEO_ID}`,
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.code).toBe('pack_not_found');
      expect(result.status).toBe(404);
    }
  });

  it('rejects identity-only packs', async () => {
    const identity = buildIdentityPack(QJ_VIDEO_ID);
    vi.spyOn(store, 'getPackRecordWithMeta').mockResolvedValue({
      outcome: 'hit',
      record: { state: 'ready', pack: identity },
      store: { backend: 'memory', ok: true },
    });
    const result = await resolveChatPackGrounding({
      videoId: QJ_VIDEO_ID,
      packId: identity.id,
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.code).toBe('pack_not_ready');
    }
    expect(identityHash(QJ_VIDEO_ID)).toBe(identity.provenance.source_hash);
  });
});
