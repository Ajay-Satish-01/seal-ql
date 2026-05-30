/**
 * Seal TypeScript SDK client.
 *
 * Usage:
 *   import { Seal } from "seal";
 *
 *   const client = new Seal({ baseUrl: "http://localhost:8000" });
 *   const result = await client.query("Show me monthly revenue");
 *   console.log(result.sql);
 *   console.log(result.results);
 */

import { QueryError, SealConnectionError, ServerError } from './errors.js';
import { flushSseRemainder, splitSseBuffer } from './sse.js';
import type {
  CatalogResponse,
  ChatResponse,
  ChatStreamEvent,
  ChatStreamMeta,
  DatabaseSchema,
  HealthResponse,
  QueryResponse,
  SealOptions,
} from './types.js';

const DEFAULT_TIMEOUT = 120_000; // 120 seconds

export class Seal {
  private readonly baseUrl: string;
  private readonly timeout: number;
  private readonly headers: Record<string, string>;

  constructor(options: SealOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, '');
    this.timeout = options.timeout ?? DEFAULT_TIMEOUT;
    this.headers = {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
      ...(options.apiKey ? { 'X-API-Key': options.apiKey } : {}),
    };
  }

  // ============================================================
  // Private helpers
  // ============================================================

  private requestSignal(): { signal: AbortSignal; cleanup?: () => void } {
    // AbortSignal.timeout uses the same implementation as Node's fetch (undici).
    // jsdom's AbortController signal is rejected by fetch with "not an instance of AbortSignal".
    if (typeof AbortSignal.timeout === 'function') {
      return { signal: AbortSignal.timeout(this.timeout) };
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);
    return { signal: controller.signal, cleanup: () => clearTimeout(timer) };
  }

  private static isTimeoutError(error: unknown): boolean {
    // AbortSignal.timeout() rejects with "TimeoutError"; the AbortController
    // fallback aborts with "AbortError". We only ever abort on timeout, so both map here.
    if (error instanceof DOMException || error instanceof Error) {
      return error.name === 'TimeoutError' || error.name === 'AbortError';
    }
    return false;
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const { signal, cleanup } = this.requestSignal();

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
        signal,
      });
    } catch (error: unknown) {
      if (Seal.isTimeoutError(error)) {
        throw new SealConnectionError(`Request to ${url} timed out after ${this.timeout}ms`);
      }
      const message = error instanceof Error ? error.message : String(error);
      throw new SealConnectionError(`Cannot connect to ${url}: ${message}`);
    } finally {
      cleanup?.();
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

  /**
   * Fetch the global data catalog (business descriptions for tables/views).
   */
  async catalog(): Promise<CatalogResponse> {
    return this.request<CatalogResponse>('GET', '/v1/catalog');
  }

  /**
   * Schema-grounded conversational Q&A.
   */
  async chat(
    message: string,
    options?: {
      sessionId?: string;
      includeCharts?: boolean;
      enhancement?: boolean;
      databaseId?: string;
    },
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>('POST', '/v1/chat', {
      message,
      session_id: options?.sessionId,
      include_charts: options?.includeCharts ?? false,
      stream: false,
      enhancement: options?.enhancement,
      database_id: options?.databaseId ?? 'default',
    });
  }

  /**
   * Stream the final chat answer as SSE (`seal.meta` then OpenAI-style chunks).
   */
  async *chatStream(
    message: string,
    options?: {
      sessionId?: string;
      includeCharts?: boolean;
      enhancement?: boolean;
      databaseId?: string;
    },
  ): AsyncGenerator<ChatStreamEvent> {
    const url = `${this.baseUrl}/v1/chat`;
    const { signal, cleanup } = this.requestSignal();

    let response: Response;
    try {
      response = await fetch(url, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          message,
          session_id: options?.sessionId,
          include_charts: options?.includeCharts ?? false,
          stream: true,
          enhancement: options?.enhancement,
          database_id: options?.databaseId ?? 'default',
        }),
        signal,
      });
    } catch (error: unknown) {
      if (Seal.isTimeoutError(error)) {
        throw new SealConnectionError(`Request to ${url} timed out after ${this.timeout}ms`);
      }
      const messageText = error instanceof Error ? error.message : String(error);
      throw new SealConnectionError(`Cannot connect to ${url}: ${messageText}`);
    } finally {
      cleanup?.();
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
      throw new QueryError(`Chat rejected (${response.status}): ${detail}`, response.status);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new SealConnectionError('Streaming response has no body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    const yieldParsed = function* (
      raw: import('./sse.js').SseParseResult | null,
    ): Generator<ChatStreamEvent, void, unknown> {
      if (!raw) return;
      if (raw.kind === 'meta') {
        yield { type: 'meta' as const, data: raw.data as unknown as ChatStreamMeta };
      } else if (raw.kind === 'delta') {
        yield { type: 'delta' as const, content: raw.content };
      } else if (raw.kind === 'done') {
        yield { type: 'done' as const };
      }
    };

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const { events, remainder } = splitSseBuffer(buffer);
        buffer = remainder;
        for (const part of events) {
          yield* yieldParsed(part);
        }
      }
      buffer += decoder.decode();
      const { events: tailEvents, remainder } = splitSseBuffer(buffer);
      for (const part of [...tailEvents, ...flushSseRemainder(remainder)]) {
        yield* yieldParsed(part);
      }
    } finally {
      reader.releaseLock();
    }
  }
}
