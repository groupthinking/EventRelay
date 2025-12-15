export const APP_NAME = 'AI Infrastructure Platform';
export const APP_DESCRIPTION = 'Production-ready AI infrastructure';

export const API_VERSION = 'v1';
export const API_PREFIX = `/api/${API_VERSION}`;

export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

export const CACHE_TTL = {
  SHORT: 60, // 1 minute
  MEDIUM: 300, // 5 minutes
  LONG: 3600, // 1 hour
  DAY: 86400, // 24 hours
} as const;

export const RATE_LIMITS = {
  ANONYMOUS: {
    requests: 10,
    window: 60, // per minute
  },
  AUTHENTICATED: {
    requests: 100,
    window: 60,
  },
  PREMIUM: {
    requests: 1000,
    window: 60,
  },
} as const;

export const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
} as const;
