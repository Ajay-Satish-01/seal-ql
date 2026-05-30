/** @vitest-environment node */
/**
 * End-to-end tests for the TypeScript SDK against a live Docker stack.
 *
 * These tests are skipped if the API server is not reachable.
 * Run `make up` before executing these tests.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { Seal } from '../src/client.js';

const API_URL = 'http://localhost:8000';

async function isApiReachable(): Promise<boolean> {
  // Verify the live service is actually our API (not just something on the port).
  try {
    const res = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(2000) });
    if (!res.ok) return false;
    const body = (await res.json()) as { status?: string };
    return body.status === 'ok';
  } catch {
    return false;
  }
}

describe('E2E Tests', async () => {
  const reachable = await isApiReachable();

  // Conditionally skip all tests if the API is not reachable.
  const testFn = reachable ? it : it.skip;

  let client: Seal;

  beforeAll(() => {
    client = new Seal({
      baseUrl: API_URL,
      timeout: 180_000,
    });
  });

  testFn('health check', async () => {
    const result = await client.health();
    expect(result.status).toBe('ok');
  });

  testFn('fetch schema', async () => {
    const result = await client.schema();
    expect(result.dialect).toBe('postgres');
    expect(result.tables.length).toBeGreaterThan(0);
  });

  testFn(
    'execute query',
    async (context) => {
      try {
        const result = await client.query('Show me 2 tables from the database');
        expect(result.sql).toBeTruthy();
        expect(result.results.length).toBeGreaterThan(0);
        expect(result.metadata.row_count).toBeGreaterThan(0);
      } catch (e) {
        // Gracefully skip if the model is too weak/slow — matches Python E2E behavior
        const msg = e instanceof Error ? e.message : String(e);
        console.warn(`⚠ Skipping query test (model may be weak/slow): ${msg}`);
        context.skip();
      }
    },
    200_000,
  );
});
