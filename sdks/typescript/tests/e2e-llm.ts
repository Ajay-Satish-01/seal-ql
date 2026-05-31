/**
 * Live LLM E2E helpers — skip transient provider failures; fail on bad 200s.
 */

import { expect } from 'vitest';
import { QueryError, SealError, ServerError } from '../src/errors.js';
import type { ChatResponse, QueryResponse } from '../src/types.js';

const LLM_SKIP_HTTP = new Set([429, 500, 502, 503, 504]);
const LLM_SKIP_MARKERS = [
  'ratelimit',
  'rate limit',
  'quota',
  'resource_exhausted',
  'too many requests',
  'timeout',
  'timed out',
  'litellm',
  'instructor',
  'internal error',
  'ollama',
];

export function llmUnavailableMessage(error: unknown): string | null {
  if (error instanceof SealError) {
    if (error.statusCode === 401) return null;
    if (error.statusCode !== undefined && LLM_SKIP_HTTP.has(error.statusCode)) {
      return error.message;
    }
  }
  const msg = error instanceof Error ? error.message : String(error);
  const lower = msg.toLowerCase();
  if (LLM_SKIP_MARKERS.some((m) => lower.includes(m))) {
    return msg;
  }
  if (error instanceof ServerError) {
    return msg;
  }
  return null;
}

export function assertChatResult(result: ChatResponse): void {
  expect(result.session_id).toBeTruthy();
  expect(String(result.message ?? '').trim().length).toBeGreaterThan(0);
}

export function assertQueryResult(result: QueryResponse): void {
  expect(String(result.sql ?? '').trim().length).toBeGreaterThan(0);
  expect(result.results.length).toBeGreaterThan(0);
  expect(result.metadata.row_count).toBeGreaterThan(0);
}

export function isUnexpectedClientError(error: unknown): boolean {
  if (error instanceof QueryError) {
    return true;
  }
  if (error instanceof SealError && error.statusCode === 400) {
    return true;
  }
  return false;
}
