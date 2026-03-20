export declare const APP_NAME = "AI Infrastructure Platform";
export declare const APP_DESCRIPTION = "Production-ready AI infrastructure";
export declare const API_VERSION = "v1";
export declare const API_PREFIX = "/api/v1";
export declare const DEFAULT_PAGE_SIZE = 20;
export declare const MAX_PAGE_SIZE = 100;
export declare const CACHE_TTL: {
    readonly SHORT: 60;
    readonly MEDIUM: 300;
    readonly LONG: 3600;
    readonly DAY: 86400;
};
export declare const RATE_LIMITS: {
    readonly ANONYMOUS: {
        readonly requests: 10;
        readonly window: 60;
    };
    readonly AUTHENTICATED: {
        readonly requests: 100;
        readonly window: 60;
    };
    readonly PREMIUM: {
        readonly requests: 1000;
        readonly window: 60;
    };
};
export declare const RETRY_CONFIG: {
    readonly maxRetries: 3;
    readonly baseDelay: 1000;
    readonly maxDelay: 10000;
};
