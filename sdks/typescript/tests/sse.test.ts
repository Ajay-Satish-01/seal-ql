import { describe, it, expect } from 'vitest';
import { flushSseRemainder, parseSseEventBlock, splitSseBuffer } from '../src/sse.js';

describe('parseSseEventBlock', () => {
  it('parses seal.meta', () => {
    const block = 'event: seal.meta\ndata: {"session_id":"s1","sql":"SELECT 1"}';
    const event = parseSseEventBlock(block);
    expect(event?.kind).toBe('meta');
    if (event?.kind === 'meta') {
      expect(event.data.session_id).toBe('s1');
    }
  });

  it('parses openai delta', () => {
    const block = 'data: {"choices":[{"delta":{"content":"Hi"},"finish_reason":null}]}';
    const event = parseSseEventBlock(block);
    expect(event).toEqual({ kind: 'delta', content: 'Hi' });
  });

  it('parses DONE', () => {
    expect(parseSseEventBlock('data: [DONE]')).toEqual({ kind: 'done' });
  });

  it('parses seal.error', () => {
    const block =
      'event: seal.error\ndata: {"code":"rate_limit","message":"Rate limited. Try again soon."}';
    expect(parseSseEventBlock(block)).toEqual({
      kind: 'error',
      code: 'rate_limit',
      message: 'Rate limited. Try again soon.',
    });
  });

  it('joins multiple data lines for meta', () => {
    const block = 'event: seal.meta\ndata: {"session_id":\ndata: "s1"}';
    const event = parseSseEventBlock(block);
    expect(event?.kind).toBe('meta');
    if (event?.kind === 'meta') {
      expect(event.data.session_id).toBe('s1');
    }
  });

  it('returns null for invalid meta json', () => {
    const block = 'event: seal.meta\ndata: {not-json';
    expect(parseSseEventBlock(block)).toBeNull();
  });
});

describe('splitSseBuffer and flush', () => {
  it('splits complete events', () => {
    const buffer =
      'event: seal.meta\ndata: {"session_id":"s1"}\n\n' +
      'data: {"choices":[{"delta":{"content":"x"}}]}\n\n';
    const { events, remainder } = splitSseBuffer(buffer);
    expect(events).toHaveLength(2);
    expect(remainder).toBe('');
  });

  it('flushes trailing event without blank line', () => {
    const buffer = 'data: [DONE]';
    const { events, remainder } = splitSseBuffer(buffer);
    expect(events).toHaveLength(0);
    const flushed = flushSseRemainder(remainder);
    expect(flushed).toEqual([{ kind: 'done' }]);
  });

  it('flushes decoder tail after stream end', () => {
    let buffer = 'event: seal.meta\ndata: {"session_id":"s1"}\n\n';
    const first = splitSseBuffer(buffer);
    buffer = first.remainder + 'data: [DONE]';
    const second = splitSseBuffer(buffer);
    const all = [...first.events, ...second.events, ...flushSseRemainder(second.remainder)];
    expect(all.some((e) => e.kind === 'meta')).toBe(true);
    expect(all.some((e) => e.kind === 'done')).toBe(true);
  });
});
