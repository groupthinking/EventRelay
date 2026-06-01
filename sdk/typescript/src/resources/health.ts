/**
 * Health resource — API health and readiness checks.
 */

import type { EventRelayClient } from "../client";
import type { HealthResponse } from "../types";

export class HealthResource {
  constructor(private readonly _client: EventRelayClient) {}

  /**
   * Perform a basic health check.
   *
   * @returns `HealthResponse` with `status` field.
   */
  async check(): Promise<HealthResponse> {
    return this._client._get("/api/v1/health") as Promise<HealthResponse>;
  }

  /**
   * Perform a detailed health check including all sub-services.
   *
   * @returns `HealthResponse` with `services` breakdown.
   */
  async detailed(): Promise<HealthResponse> {
    return this._client._get("/api/v1/health/detailed") as Promise<HealthResponse>;
  }
}
