/** @vitest-environment node */
/**
 * End-to-end tests for the TypeScript SDK against a live Docker stack.
 *
 * These tests are skipped if the API server is not reachable.
 * Run `make up` before executing these tests.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { Seal } from '../src/client.js';
import {
  assertChatResult,
  assertQueryResult,
  isUnexpectedClientError,
  llmUnavailableMessage,
} from './e2e-llm.js';

const API_URL = 'http://localhost:8000';
/** Matches `.env.example` / Python `test_sdk_e2e.py` for local and CI compose stacks. */
const API_KEY = process.env.SEAL_API_KEY ?? 'dev-local-change-me';

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

/** LLM-backed routes can take minutes on local Ollama; default Vitest timeout is 5s. */
const LLM_E2E_TIMEOUT_MS = 200_000;

describe('E2E Tests', { timeout: LLM_E2E_TIMEOUT_MS }, async () => {
  const reachable = await isApiReachable();

  // Conditionally skip all tests if the API is not reachable.
  const testFn = reachable ? it : it.skip;

  let client: Seal;

  beforeAll(() => {
    client = new Seal({
      baseUrl: API_URL,
      apiKey: API_KEY,
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

  testFn('fetch catalog', async () => {
    const result = await client.catalog();
    expect(result.tables.length).toBeGreaterThan(0);
  });

  testFn('catalog descriptions survive sync', async (context) => {
    const headers = { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' };
    const catalog = await fetch(`${API_URL}/v1/catalog`, { headers });
    if (!catalog.ok) {
      context.skip(`catalog GET failed: ${catalog.status}`);
      return;
    }
    const tables = ((await catalog.json()) as { tables?: { name?: string }[] }).tables ?? [];
    if (!tables.some((t) => t.name === 'orders')) {
      context.skip('public.orders not in catalog (run make seed)');
      return;
    }

    const patch = await fetch(`${API_URL}/v1/catalog/descriptions`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify({
        tables: [{ name: 'orders', schema: 'public', table_description: 'TS SDK E2E override' }],
      }),
    });
    expect(patch.ok).toBe(true);

    const sync = await fetch(`${API_URL}/v1/catalog/sync`, { method: 'POST', headers });
    expect(sync.ok).toBe(true);

    const after = await fetch(`${API_URL}/v1/catalog`, { headers });
    const body = (await after.json()) as {
      tables?: { name?: string; table_description?: string }[];
    };
    const orders = body.tables?.find((t) => t.name === 'orders');
    expect(orders?.table_description).toBe('TS SDK E2E override');
  });

  testFn('workspace settings', async () => {
    const res = await fetch(`${API_URL}/v1/workspace/settings`, {
      headers: { 'X-API-Key': API_KEY },
    });
    expect(res.ok).toBe(true);
    const body = (await res.json()) as { settings?: unknown; schema?: unknown[] };
    expect(body.settings).toBeDefined();
    expect(Array.isArray(body.schema)).toBe(true);
  });

  testFn('chat json', async (context) => {
    try {
      const result = await client.chat('Name one table in the database.', {
        includeCharts: false,
      });
      assertChatResult(result);
    } catch (e) {
      const skipReason = llmUnavailableMessage(e);
      if (skipReason) {
        console.warn(`⚠ Skipping chat E2E (LLM unavailable): ${skipReason}`);
        context.skip();
        return;
      }
      throw e;
    }
  });

  testFn('execute query', async (context) => {
    try {
      const result = await client.query('Show me 2 products');
      assertQueryResult(result);
    } catch (e) {
      const skipReason = llmUnavailableMessage(e);
      if (skipReason) {
        console.warn(`⚠ Skipping query E2E (LLM unavailable): ${skipReason}`);
        context.skip();
        return;
      }
      const msg = e instanceof Error ? e.message : String(e);
      if (isUnexpectedClientError(e) && /out_of_scope|query_out_of_scope/i.test(msg)) {
        throw new Error(`Benign query incorrectly marked out of scope: ${msg}`);
      }
      throw e;
    }
  });
});
