import { describe, expect, it } from 'vitest';
import { reasonEnvelope, reasonEnvelopeJson } from '@/lib/api-reason-envelope';

describe('api-reason-envelope', () => {
  it('builds ok/reason_code envelopes with optional detail', () => {
    expect(reasonEnvelope(false, 'HOSTED_PACK_NOT_FOUND')).toEqual({
      ok: false,
      reason_code: 'HOSTED_PACK_NOT_FOUND',
    });
    expect(reasonEnvelope(false, 'HOSTED_PACK_STORE_ERROR', 'upstash timeout')).toEqual({
      ok: false,
      reason_code: 'HOSTED_PACK_STORE_ERROR',
      detail: 'upstash timeout',
    });
  });

  it('merges envelope fields with extra payload keys', () => {
    expect(
      reasonEnvelopeJson(reasonEnvelope(false, 'HOSTED_ASSET_PATH_INVALID'), {
        videoId: 'abc',
      }),
    ).toEqual({
      videoId: 'abc',
      ok: false,
      reason_code: 'HOSTED_ASSET_PATH_INVALID',
    });
  });
});
