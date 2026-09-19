import { describe, expect, it } from 'vitest';
import {
  VIDEO_PACK_EXTRACT_PIPELINE_VERSION,
  classifyVideoPackExtractFailure,
  hostedExtractReasonFromDetail,
  isTransientVideoPackGatewayError,
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

  it('keeps parse and config failures on HOSTED_PACK_EXTRACT_FAILED', () => {
    expect(
      hostedExtractReasonFromDetail('Video pack spec extract requires AI Gateway'),
    ).toBe('HOSTED_PACK_EXTRACT_FAILED');
    expect(
      hostedExtractReasonFromDetail('Gemini 3.8 Flash returned unparseable spec JSON at position 12'),
    ).toBe('HOSTED_PACK_EXTRACT_FAILED');
  });

  it('classifies transient gateway errors for retry', () => {
    expect(isTransientVideoPackGatewayError(new Error('Vercel AI Gateway returned empty content'))).toBe(
      true,
    );
    expect(
      isTransientVideoPackGatewayError(
        new Error('GatewayInternalServerError: Service temporarily unavailable'),
      ),
    ).toBe(true);
    expect(isTransientVideoPackGatewayError(new Error('Video pack spec extract requires AI Gateway'))).toBe(
      false,
    );
    expect(
      isTransientVideoPackGatewayError(
        new Error('Gemini 3.8 Flash returned unparseable spec JSON at position 4'),
      ),
    ).toBe(false);
  });

  it('pins the extract pipeline version marker', () => {
    expect(VIDEO_PACK_EXTRACT_PIPELINE_VERSION).toBe('c1-gateway-retry-v1');
  });
});
