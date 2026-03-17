"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.RETRY_CONFIG = exports.RATE_LIMITS = exports.CACHE_TTL = exports.MAX_PAGE_SIZE = exports.DEFAULT_PAGE_SIZE = exports.API_PREFIX = exports.API_VERSION = exports.APP_DESCRIPTION = exports.APP_NAME = void 0;
exports.APP_NAME = 'AI Infrastructure Platform';
exports.APP_DESCRIPTION = 'Production-ready AI infrastructure';
exports.API_VERSION = 'v1';
exports.API_PREFIX = `/api/${exports.API_VERSION}`;
exports.DEFAULT_PAGE_SIZE = 20;
exports.MAX_PAGE_SIZE = 100;
exports.CACHE_TTL = {
    SHORT: 60, // 1 minute
    MEDIUM: 300, // 5 minutes
    LONG: 3600, // 1 hour
    DAY: 86400, // 24 hours
};
exports.RATE_LIMITS = {
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
};
exports.RETRY_CONFIG = {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
};
//# sourceMappingURL=constants.js.map