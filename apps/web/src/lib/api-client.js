"use strict";
/**
 * Base API client with retry logic and error handling.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.apiClient = exports.ApiClient = void 0;
const DEFAULT_BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.BACKEND_URL ||
    'http://localhost:8000';
class ApiClient {
    baseUrl;
    maxRetries;
    constructor(baseUrl, maxRetries = 2) {
        this.baseUrl = baseUrl || DEFAULT_BACKEND_URL;
        this.maxRetries = maxRetries;
    }
    async request(path, options = {}) {
        const url = `${this.baseUrl}${path}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        let lastError = null;
        for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
            try {
                const res = await fetch(url, { ...options, headers });
                if (!res.ok) {
                    const body = await res.json().catch(() => ({}));
                    return {
                        status: 'error',
                        error: body.detail || body.error || res.statusText,
                        detail: body.detail,
                        timestamp: new Date().toISOString(),
                        request_id: body.request_id || '',
                    };
                }
                return (await res.json());
            }
            catch (err) {
                lastError = err instanceof Error ? err : new Error(String(err));
                if (attempt < this.maxRetries) {
                    await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
                }
            }
        }
        return {
            status: 'error',
            error: lastError?.message || 'Request failed',
            timestamp: new Date().toISOString(),
            request_id: '',
        };
    }
    async get(path) {
        return this.request(path, { method: 'GET' });
    }
    async post(path, body) {
        return this.request(path, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    }
    async put(path, body) {
        return this.request(path, {
            method: 'PUT',
            body: JSON.stringify(body),
        });
    }
    async del(path) {
        return this.request(path, { method: 'DELETE' });
    }
}
exports.ApiClient = ApiClient;
/** Singleton client for use throughout the app */
exports.apiClient = new ApiClient();
//# sourceMappingURL=api-client.js.map