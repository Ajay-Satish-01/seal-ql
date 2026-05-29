/**
 * Intelligence Connector TypeScript SDK client.
 *
 * Usage:
 *   import { IntelligenceConnector } from "intelligence-sdk";
 *
 *   const client = new IntelligenceConnector({ baseUrl: "http://localhost:8000" });
 *   const result = await client.query("Show me monthly revenue");
 *   console.log(result.sql);
 *   console.log(result.results);
 */

import { ConnectionError, QueryError, ServerError } from './errors.js';
import type { ConnectorOptions, DatabaseSchema, HealthResponse, QueryResponse } from './types.js';

const DEFAULT_TIMEOUT = 120_000; // 120 seconds

export class IntelligenceConnector {
  private readonly baseUrl: string;
  private readonly timeout: number;
  private readonly headers: Record<string, string>;

  constructor(options: ConnectorOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, '');
    this.timeout = options.timeout ?? DEFAULT_TIMEOUT;
    this.headers = {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    };
  }

  // ============================================================
  // Private helpers
  // ============================================================

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
    } catch (error: unknown) {
      clearTimeout(timer);
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ConnectionError(`Request to ${url} timed out after ${this.timeout}ms`);
      }
      const message = error instanceof Error ? error.message : String(error);
      throw new ConnectionError(`Cannot connect to ${url}: ${message}`);
    } finally {
      clearTimeout(timer);
    }

    if (!response.ok) {
      let detail: string;
      try {
        const errorBody = (await response.json()) as { detail?: string };
        detail = errorBody.detail ?? response.statusText;
      } catch {
        detail = response.statusText;
      }

      if (response.status >= 500) {
        throw new ServerError(`Server error (${response.status}): ${detail}`, response.status);
      }
      throw new QueryError(`Query rejected (${response.status}): ${detail}`, response.status);
    }

    return (await response.json()) as T;
  }

  // ============================================================
  // Public API
  // ============================================================

  /**
   * Check API health.
   */
  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>('GET', '/health');
  }

  /**
   * Send a natural language query to the API.
   *
   * @param query - The natural language question.
   * @param databaseId - Optional database identifier.
   * @returns QueryResponse containing SQL, results, chart spec, and metadata.
   */
  async query(query: string, databaseId: string = 'default'): Promise<QueryResponse> {
    return this.request<QueryResponse>('POST', '/v1/query', {
      query,
      database_id: databaseId,
    });
  }

  /**
   * Fetch the introspected database schema.
   */
  async schema(): Promise<DatabaseSchema> {
    return this.request<DatabaseSchema>('GET', '/v1/schema');
  }
}
