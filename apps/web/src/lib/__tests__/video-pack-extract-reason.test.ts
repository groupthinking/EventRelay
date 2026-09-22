import { describe, expect, it } from 'vitest';
import {
  VIDEO_PACK_EXTRACT_PIPELINE_VERSION,
  classifyVideoPackExtractFailure,
  hostedExtractReasonFromDetail,
  isTransientVideoPackExtractError,
} from '@/lib/video-pack-extract-reason';

describe('video-pack-extract-reason', () => {
  it('maps empty gateway content to HOSTED_PACK_GATEWAY_EMPTY', () => {
    expect(
      hostedExtractReasonFromDetail('Vercel AI Gateway returned empty content'),
    ).toBe('HOSTED_PACK_GATEWAY_EMPTY');
    expect(classifyVideoPackExtractFailure('Gemini 3.8 Flash returned no extracted spec content.')).toBe(
      'HOSTED_PACK_GATEWAY_EMPTY',
    );
  });

  it('maps transient gateway outages to HOSTED_PACK_GATEWAY_UNAVAILABLE', () => {
    expect(
      hostedExtractReasonFromDetail(
        'GatewayInternalServerError: Service temporarily unavailable',
      ),
    ).toBe('HOSTED_PACK_GATEWAY_UNAVAILABLE');
    expect(hostedExtractReasonFromDetail('Vercel AI Gateway HTTP 503: upstream')).toBe(
      'HOSTED_PACK_GATEWAY_UNAVAILABLE',
    );
  });

  it('maps deleted or missing YouTube sources to HOSTED_PACK_SOURCE_NOT_FOUND', () => {
    expect(hostedExtractReasonFromDetail('Requested entity was not found.')).toBe(
      'HOSTED_PACK_SOURCE_NOT_FOUND',
    );
    expect(
      classifyVideoPackExtractFailure(
        'Vercel AI Gateway failed after 5 attempts: Requested entity was not found.',
      ),
    ).toBe('HOSTED_PACK_SOURCE_NOT_FOUND');
    expect(
      isTransientVideoPackExtractError(new Error('Requested entity was not found.')),
    ).toBe(false);
  });

  it('keeps parse and config failures on HOSTED_PACK_EXTRACT_FAILED', () => {
    expect(
      hostedExtractReasonFromDetail('Video pack spec extract requires AI Gateway'),
    ).toBe('HOSTED_PACK_EXTRACT_FAILED');
    expect(
      hostedExtractReasonFromDetail('Gemini 3.8 Flash returned unparseable spec JSON at position 12'),
    ).toBe('HOSTED_PACK_EXTRACT_FAILED');
  });

  it('classifies transient gateway errors for retry', () => {
    expect(isTransientVideoPackExtractError(new Error('Vercel AI Gateway returned empty content'))).toBe(
      true,
    );
    expect(
      isTransientVideoPackExtractError(
        new Error('GatewayInternalServerError: Service temporarily unavailable'),
      ),
    ).toBe(true);
    expect(isTransientVideoPackExtractError(new Error('Video pack spec extract requires AI Gateway'))).toBe(
      false,
    );
    expect(
      isTransientVideoPackExtractError(
        new Error('Video pack spec extract requires direct Google video access and model gemini-3.8-flash.'),
      ),
    ).toBe(false);
    expect(
      isTransientVideoPackExtractError(
        new Error('Gemini 3.8 Flash returned unparseable spec JSON at position 4'),
      ),
    ).toBe(false);
  });

  it('pins the extract pipeline version marker', () => {
    expect(VIDEO_PACK_EXTRACT_PIPELINE_VERSION).toBe('p1.6-direct-shard-v1');
  });
});
