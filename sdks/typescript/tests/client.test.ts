/**
 * Unit tests for the TypeScript SDK — mocked fetch.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { IntelligenceConnector } from '../src/client.js';
import { QueryError, ServerError, ConnectionError } from '../src/errors.js';

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

describe('IntelligenceConnector', () => {
  let client: IntelligenceConnector;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    client = new IntelligenceConnector({ baseUrl: 'http://testserver' });
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
            $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
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

    it('should throw ServerError on 500', async () => {
      globalThis.fetch = mockFetch(500, { detail: 'Internal error' }, false);
      await expect(client.query('query')).rejects.toThrow(ServerError);
      await expect(client.query('query')).rejects.toThrow(/Internal error/);
    });

    it('should throw ConnectionError on fetch failure', async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('fetch failed'));
      await expect(client.query('query')).rejects.toThrow(ConnectionError);
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
  });

  // -- Options --

  describe('options', () => {
    it('should strip trailing slashes from baseUrl', async () => {
      const fetchMock = mockFetch(200, { status: 'ok' });
      globalThis.fetch = fetchMock;

      const c = new IntelligenceConnector({
        baseUrl: 'http://testserver///',
      });
      await c.health();

      expect(fetchMock).toHaveBeenCalledWith('http://testserver/health', expect.anything());
    });

    it('should merge custom headers', async () => {
      const fetchMock = mockFetch(200, { status: 'ok' });
      globalThis.fetch = fetchMock;

      const c = new IntelligenceConnector({
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
  });
});
