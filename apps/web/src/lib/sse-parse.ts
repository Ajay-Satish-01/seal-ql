/**
 * SSE parsing for POST /v1/chat stream responses.
 *
 * Single source of truth lives in the Seal TypeScript SDK (`seal/src/sse.ts`)
 * and is covered by `sdks/typescript/tests/sse.test.ts`. We re-export here so
 * the web demo and the SDK can never drift.
 */
export { parseSseEventBlock, splitSseBuffer, flushSseRemainder, type SseParseResult } from 'seal';
