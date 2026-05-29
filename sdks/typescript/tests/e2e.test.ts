/**
 * End-to-end tests for the TypeScript SDK against a live Docker stack.
 *
 * These tests are skipped if the API server is not reachable.
 * Run `make up` before executing these tests.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { IntelligenceConnector } from '../src/client.js';
import * as net from 'net';

const API_URL = 'http://localhost:8000';

function isApiReachable(): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(2000);
    socket
      .connect(8000, 'localhost', () => {
        socket.destroy();
        resolve(true);
      })
      .on('error', () => {
        socket.destroy();
        resolve(false);
      })
      .on('timeout', () => {
        socket.destroy();
        resolve(false);
      });
  });
}

describe('E2E Tests', async () => {
  const reachable = await isApiReachable();

  // Conditionally skip all tests if the API is not reachable.
  const testFn = reachable ? it : it.skip;

  let client: IntelligenceConnector;

  beforeAll(() => {
    client = new IntelligenceConnector({
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

  testFn('execute query', async () => {
    const result = await client.query('Show me 2 tables from the database');
    expect(result.sql).toBeTruthy();
    expect(result.results.length).toBeGreaterThan(0);
    expect(result.metadata.row_count).toBeGreaterThan(0);
  });
});
