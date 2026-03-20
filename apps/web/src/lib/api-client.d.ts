/**
 * Base API client with retry logic and error handling.
 */
import type { ApiResponse } from './types';
export declare class ApiClient {
    private baseUrl;
    private maxRetries;
    constructor(baseUrl?: string, maxRetries?: number);
    private request;
    get<T>(path: string): Promise<ApiResponse<T>>;
    post<T>(path: string, body: unknown): Promise<ApiResponse<T>>;
    put<T>(path: string, body: unknown): Promise<ApiResponse<T>>;
    del<T>(path: string): Promise<ApiResponse<T>>;
}
/** Singleton client for use throughout the app */
export declare const apiClient: ApiClient;
