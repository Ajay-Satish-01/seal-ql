/**
 * Unit tests for the TypeScript SDK — mocked fetch.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Seal } from '../src/client.js';
import { QueryError, ServerError, SealConnectionError } from '../src/errors.js';
import { VEGA_LITE_SCHEMA } from '../src/types.js';

// ============================================================
// Helpers
// ============================================================

function mockFetch(status: number, body: unknown, ok?: boolean): typeof globalThis.fetch {
  return vi.fn().mockResolvedValue({
    ok: ok ?? (status >= 200 && status < 300),
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response);
}

// ============================================================
// Tests
// ============================================================

describe('Seal', () => {
  let client: Seal;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    client = new Seal({ baseUrl: 'http://testserver' });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  // -- Health --

  describe('health()', () => {
    it('should return health status', async () => {
      globalThis.fetch = mockFetch(200, { status: 'ok' });
      const result = await client.health();
      expect(result.status).toBe('ok');
    });
  });

  // -- Query --

  describe('query()', () => {
    it('should return query results', async () => {
      const mockResponse = {
        sql: 'SELECT 1 AS id LIMIT 10000',
        columns: [{ name: 'id', type: 'int', nullable: true }],
        results: [{ id: 1 }],
        chart: null,
        metadata: { row_count: 1 },
      };
      globalThis.fetch = mockFetch(200, mockResponse);

      const result = await client.query('test query');
      expect(result.sql).toBe('SELECT 1 AS id LIMIT 10000');
      expect(result.results).toHaveLength(1);
      expect(result.results[0].id).toBe(1);
      expect(result.chart).toBeNull();
    });

    it('should return query results with chart', async () => {
      const mockResponse = {
        sql: 'SELECT name, COUNT(*) FROM users GROUP BY name',
        columns: [
          { name: 'name', type: 'text' },
          { name: 'count', type: 'int8' },
        ],
        results: [{ name: 'Alice', count: 5 }],
        chart: {
          chart_type: 'bar',
          vega_lite_spec: {
            $schema: VEGA_LITE_SCHEMA,
          },
          metadata: {},
        },
        metadata: { row_count: 1 },
      };
      globalThis.fetch = mockFetch(200, mockResponse);

      const result = await client.query('Users by name');
      expect(result.chart).not.toBeNull();
      expect(result.chart!.chart_type).toBe('bar');
    });

    it('should throw QueryError on 400', async () => {
      globalThis.fetch = mockFetch(400, { detail: 'Validation failed' }, false);
      await expect(client.query('bad query')).rejects.toThrow(QueryError);
      await expect(client.query('bad query')).rejects.toThrow(/Validation failed/);
    });

    it('should throw QueryError with message on chat session database mismatch', async () => {
      globalThis.fetch = mockFetch(
        400,
        {
          detail: {
            code: 'session_database_id_mismatch',
            message: "Session 's1' is pinned to database_id 'default'; got 'analytics'",
            session_id: 's1',
            pinned_database_id: 'default',
            requested_database_id: 'analytics',
          },
        },
        false,
      );
      await expect(
        client.chat('follow up', { sessionId: 's1', databaseId: 'analytics' }),
      ).rejects.toThrow(/pinned to database/i);
    });

    it('should throw QueryOutOfScopeError on structured guardrails 400', async () => {
      globalThis.fetch = mockFetch(
        400,
        {
          detail: {
            detail: 'query_out_of_scope',
            reason: 'off-topic pattern',
            suggested_queries: ['Show order count by month'],
          },
        },
        false,
      );
      await expect(client.query('write me a poem')).rejects.toMatchObject({
        name: 'QueryOutOfScopeError',
        reason: 'off-topic pattern',
        suggestedQueries: ['Show order count by month'],
      });
    });

    it('should throw ServerError on 500', async () => {
      globalThis.fetch = mockFetch(500, { detail: 'Internal error' }, false);
      await expect(client.query('query')).rejects.toThrow(ServerError);
      await expect(client.query('query')).rejects.toThrow(/Internal error/);
    });

    it('should throw SealConnectionError on fetch failure', async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('fetch failed'));
      await expect(client.query('query')).rejects.toThrow(SealConnectionError);
    });

    it('should send database_id in the request body', async () => {
      const fetchMock = mockFetch(200, {
        sql: 'SELECT 1',
        columns: [],
        results: [],
        chart: null,
        metadata: {},
      });
      globalThis.fetch = fetchMock;

      await client.query('test', 'my_db');

      expect(fetchMock).toHaveBeenCalledWith(
        'http://testserver/v1/query',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ query: 'test', database_id: 'my_db' }),
        }),
      );
    });
  });

  // -- Chat --

  describe('chat()', () => {
    it('should parse execution metadata on chat responses', async () => {
      globalThis.fetch = mockFetch(200, {
        session_id: 's1',
        message: 'Ten orders.',
        sql: 'SELECT COUNT(*) AS n FROM orders',
        columns: [{ name: 'n', type: 'int8', nullable: true }],
        results: [{ n: 10 }],
        metadata: {
          database_id: 'default',
          row_count: 1,
          execution_time_ms: 2,
          truncated: false,
          warnings: [],
          repair_attempts: 1,
          used_sql: true,
          enhancement: { enabled: false, applied: [] },
        },
      });

      const result = await client.chat('How many orders?');
      expect(result.metadata?.row_count).toBe(1);
      expect(result.metadata?.repair_attempts).toBe(1);
      expect(result.metadata?.enhancement?.enabled).toBe(false);
      expect(result.columns?.[0]?.name).toBe('n');
    });
  });

  // -- Schema --

  describe('schema()', () => {
    it('should return database schema', async () => {
      globalThis.fetch = mockFetch(200, {
        dialect: 'postgres',
        tables: [
          {
            name: 'users',
            columns: [{ name: 'id', type: 'int4', nullable: false }],
            kind: 'table',
          },
        ],
      });

      const result = await client.schema();
      expect(result.dialect).toBe('postgres');
      expect(result.tables).toHaveLength(1);
      expect(result.tables[0].name).toBe('users');
    });

    it('should pass databaseId query param', async () => {
      const fetchMock = mockFetch(200, { dialect: 'duckdb', tables: [] });
      globalThis.fetch = fetchMock;

      await client.schema({ databaseId: 'analytics' });

      expect(fetchMock).toHaveBeenCalledWith(
        'http://testserver/v1/schema?database_id=analytics',
        expect.any(Object),
      );
    });
  });

  // -- Options --

  describe('options', () => {
    it('should strip trailing slashes from baseUrl', async () => {
      const fetchMock = mockFetch(200, { status: 'ok' });
      globalThis.fetch = fetchMock;

      const c = new Seal({
        baseUrl: 'http://testserver///',
      });
      await c.health();

      expect(fetchMock).toHaveBeenCalledWith('http://testserver/health', expect.anything());
    });

    it('should merge custom headers', async () => {
      const fetchMock = mockFetch(200, { status: 'ok' });
      globalThis.fetch = fetchMock;

      const c = new Seal({
        baseUrl: 'http://testserver',
        headers: { Authorization: 'Bearer token123' },
      });
      await c.health();

      expect(fetchMock).toHaveBeenCalledWith(
        'http://testserver/health',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer token123',
            'Content-Type': 'application/json',
          }),
        }),
      );
    });

    it('should let apiKey override X-API-Key in custom headers', async () => {
      const fetchMock = mockFetch(200, {
        sql: 'SELECT 1',
        columns: [],
        results: [],
        chart: null,
        metadata: {},
      });
      globalThis.fetch = fetchMock;

      const c = new Seal({
        baseUrl: 'http://testserver',
        apiKey: 'correct-key',
        headers: { 'X-API-Key': 'wrong-key' },
      });
      await c.query('test');

      expect(fetchMock).toHaveBeenCalledWith(
        'http://testserver/v1/query',
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Key': 'correct-key',
          }),
        }),
      );
    });

    it('should send X-API-Key on v1 requests when apiKey is set', async () => {
      const fetchMock = mockFetch(200, {
        sql: 'SELECT 1',
        columns: [],
        results: [],
        chart: null,
        metadata: {},
      });
      globalThis.fetch = fetchMock;

      const c = new Seal({
        baseUrl: 'http://testserver',
        apiKey: 'secret-key',
      });
      await c.query('test');

      expect(fetchMock).toHaveBeenCalledWith(
        'http://testserver/v1/query',
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Key': 'secret-key',
          }),
        }),
      );
    });

    it('should throw QueryError on 401', async () => {
      globalThis.fetch = mockFetch(401, { detail: 'Invalid or missing API key' }, false);
      const c = new Seal({ baseUrl: 'http://testserver' });
      await expect(c.query('query')).rejects.toThrow(QueryError);
      await expect(c.query('query')).rejects.toThrow(/Invalid or missing API key/);
    });
  });
});
