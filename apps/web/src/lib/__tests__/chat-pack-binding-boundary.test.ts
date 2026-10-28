import { expect, it, vi } from 'vitest';
vi.mock('@/lib/video-pack', () => ({ buildIdentityPack: vi.fn(() => { throw new Error('Identity builder must not run for malformed input'); }), isIdentityOnlyPack: vi.fn() }));
vi.mock('@/lib/video-pack-store', () => ({ getPackRecordWithMeta: vi.fn() }));
import { buildIdentityPack } from '@/lib/video-pack';
import { parseChatPackBinding, resolveChatPackGrounding } from '@/lib/chat-pack-grounding';
it('rejects malformed video and pack identifiers before constructing identity', () => {
  for (const video_id of ['bad', 'auJzb1D-fag-extra', 'https://youtu.be/auJzb1D-fag']) {
    expect(parseChatPackBinding({video_id})).toBeNull();
    expect(parseChatPackBinding({pack_id:`vp:v0:${video_id}`})).toBeNull();
  }
});
it('rejects directly supplied malformed bindings with400 and no identity lookup', async () => {
  expect(await resolveChatPackGrounding({videoId:'bad',packId:'vp:v0:bad'})).toMatchObject({ok:false,status:400,code:'pack_id_mismatch'});
  expect(buildIdentityPack).not.toHaveBeenCalled();
});
it('accepts only matching canonical identifiers', () => {
  expect(parseChatPackBinding({pack_id:'vp:v0:auJzb1D-fag'})).toEqual({videoId:'auJzb1D-fag',packId:'vp:v0:auJzb1D-fag'});
  expect(parseChatPackBinding({video_id:'auJzb1D-fag',pack_id:'vp:v0:jNQXAC9IVRw'})).toBeNull();
});
