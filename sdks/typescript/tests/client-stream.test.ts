/**
 * chatStream SSE tests — seal.error / stream_error forwarding.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Seal } from '../src/client.js';

function mockStreamFetch(sse: string): typeof globalThis.fetch {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(sse));
      controller.close();
    },
  });
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    statusText: 'OK',
    body: stream,
  } as Response);
}

describe('Seal.chatStream()', () => {
  const originalFetch = globalThis.fetch;
  let client: Seal;

  beforeEach(() => {
    client = new Seal({ baseUrl: 'http://testserver' });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('forwards seal.error as stream_error events', async () => {
    const sse =
      'event: seal.error\ndata: {"code":"rate_limit","message":"Rate limited. Try again soon."}\n\n' +
      'data: [DONE]\n\n';
    globalThis.fetch = mockStreamFetch(sse);

    const events = [];
    for await (const event of client.chatStream('hello')) {
      events.push(event);
    }

    expect(events).toEqual([
      {
        type: 'stream_error',
        code: 'rate_limit',
        message: expect.stringContaining('Rate limited'),
      },
      { type: 'done' },
    ]);
  });
});
