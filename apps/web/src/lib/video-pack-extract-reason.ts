/** Bump when extract retry/salvage policy changes — triggers reclaimReady on POST. */
export const VIDEO_PACK_EXTRACT_PIPELINE_VERSION = 'h1-extract-reliability-v1' as const;

export type VideoPackExtractFailureReason =
  | 'HOSTED_PACK_GATEWAY_EMPTY'
  | 'HOSTED_PACK_GATEWAY_UNAVAILABLE'
  | 'HOSTED_PACK_SOURCE_NOT_FOUND'
  | 'HOSTED_PACK_EXTRACT_FAILED';

export function isVideoPackSourceNotFoundMessage(message: string): boolean {
  const lower = message.trim().toLowerCase();
  if (!lower) return false;
  return (
    lower.includes('requested entity was not found') ||
    lower.includes('entity was not found') ||
    lower.includes('youtube reports this video is unavailable') ||
    lower.includes('video is unavailable or was removed')
  );
}

export function normalizeExtractFailureMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message.trim() || 'Video pack spec extract failed.';
  }
  if (typeof error === 'string' && error.trim()) {
    return error.trim();
  }
  return 'Video pack spec extract failed.';
}

export function classifyVideoPackExtractFailure(message: string): VideoPackExtractFailureReason {
  const lower = message.trim().toLowerCase();
  if (!lower) {
    return 'HOSTED_PACK_EXTRACT_FAILED';
  }
  if (
    lower.includes('returned empty content') ||
    lower.includes('returned no extracted spec content')
  ) {
    return 'HOSTED_PACK_GATEWAY_EMPTY';
  }
  if (isVideoPackSourceNotFoundMessage(message)) {
    return 'HOSTED_PACK_SOURCE_NOT_FOUND';
  }
  if (
    lower.includes('gatewayinternalservererror') ||
    lower.includes('service temporarily unavailable') ||
    /vercel ai gateway http 503/i.test(message) ||
    (lower.includes('vercel ai gateway') && lower.includes('503'))
  ) {
    return 'HOSTED_PACK_GATEWAY_UNAVAILABLE';
  }
  if (
    lower.includes('after 5 attempts') ||
    lower.includes('after 4 attempts') ||
    lower.includes('after 3 attempts') ||
    (lower.includes('failed after') && lower.includes('attempt'))
  ) {
    if (isVideoPackSourceNotFoundMessage(message)) {
      return 'HOSTED_PACK_SOURCE_NOT_FOUND';
    }
    if (lower.includes('empty content') || lower.includes('no extracted spec')) {
      return 'HOSTED_PACK_GATEWAY_EMPTY';
    }
    return 'HOSTED_PACK_GATEWAY_UNAVAILABLE';
  }
  return 'HOSTED_PACK_EXTRACT_FAILED';
}

export function hostedExtractReasonFromDetail(message: string): VideoPackExtractFailureReason {
  return classifyVideoPackExtractFailure(message);
}

export function isTransientVideoPackGatewayError(error: unknown): boolean {
  const message = normalizeExtractFailureMessage(error);
  const lower = message.toLowerCase();

  if (isVideoPackSourceNotFoundMessage(message)) {
    return false;
  }
  if (lower.includes('requires ai gateway') || lower.includes('ai gateway api key is not configured')) {
    return false;
  }
  if (lower.includes('returned no extracted spec content') && !lower.includes('gateway')) {
    return false;
  }
  if (lower.includes('unparseable spec json') && !lower.includes('truncated')) {
    return false;
  }

  if (lower.includes('returned empty content')) return true;
  if (lower.includes('gatewayinternalservererror')) return true;
  if (lower.includes('service temporarily unavailable')) return true;
  if (message.includes('503')) return true;
  if (message.includes('429') || lower.includes('resource_exhausted')) return true;
  if (lower.includes('high traffic') || lower.includes('overloaded')) return true;
  if (lower.includes('econnreset') || lower.includes('fetch failed')) return true;

  if (lower.includes('unparseable spec json') && lower.includes('truncated')) {
    return true;
  }

  return false;
}

export function isRetryableTruncatedParseError(error: unknown, rawText?: string): boolean {
  if (!(error instanceof Error)) return false;
  const lower = error.message.toLowerCase();
  if (!lower.includes('unparseable spec json')) return false;
  if (!(lower.includes('truncated mid-string') || lower.includes('(truncated'))) {
    return false;
  }
  if (rawText !== undefined) {
    const trimmed = rawText.trim();
    if (!trimmed.startsWith('{') && !trimmed.startsWith('```')) {
      return false;
    }
  }
  return true;
}

export function jitteredExtractBackoffMs(attemptIndex: number, baseMs = 1500): number {
  const exponential = baseMs * 2 ** attemptIndex;
  const jitter = Math.floor(Math.random() * 400);
  return exponential + jitter;
}

export function sleepMs(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
