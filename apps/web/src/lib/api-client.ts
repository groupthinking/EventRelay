/**
 * Base API client with retry logic and error handling.
 */

import type { ApiResponse } from './types';

const DEFAULT_BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  'http://localhost:8000';

export class ApiClient {
  private baseUrl: string;
  private maxRetries: number;

  constructor(baseUrl?: string, maxRetries = 2) {
    this.baseUrl = baseUrl || DEFAULT_BACKEND_URL;
    this.maxRetries = maxRetries;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    let lastError: Error | null = null;

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
          } as ApiResponse<T>;
        }

        return (await res.json()) as ApiResponse<T>;
      } catch (err) {
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
    } as ApiResponse<T>;
  }

  async get<T>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>(path, { method: 'GET' });
  }

  async post<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async put<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  async del<T>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>(path, { method: 'DELETE' });
  }
}

/** Singleton client for use throughout the app */
export const apiClient = new ApiClient();
