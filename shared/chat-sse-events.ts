/**
 * Map parsed SSE events to chat stream events (shared by apps/docs and apps/web).
 */

import { formatClientError } from './api-error';
import type { ChatStreamMeta } from './metadata-contract';
import { partialStreamMetaFromRaw, tryParseStreamMeta } from './stream-meta';

export type ChatSseParseResult =
  | { kind: 'meta'; data: unknown }
  | { kind: 'delta'; content: string }
  | { kind: 'error'; code: string; message: string }
  | { kind: 'done' };

export type ChatStreamEvent =
  | { type: 'meta'; data: ChatStreamMeta }
  | { type: 'meta_error'; error: string; partial: Partial<ChatStreamMeta> }
  | { type: 'stream_error'; code: string; message: string }
  | { type: 'delta'; content: string }
  | { type: 'done' };

export function mapChatSseEvent(event: ChatSseParseResult): ChatStreamEvent | null {
  if (event.kind === 'meta') {
    const parsed = tryParseStreamMeta(event.data);
    if (!parsed.ok) {
      return {
        type: 'meta_error',
        error: parsed.error,
        partial: partialStreamMetaFromRaw(event.data) as Partial<ChatStreamMeta>,
      };
    }
    return { type: 'meta', data: parsed.data as ChatStreamMeta };
  }
  if (event.kind === 'error') {
    return {
      type: 'stream_error',
      code: event.code,
      message: formatClientError(new Error(event.message), event.message),
    };
  }
  if (event.kind === 'delta') {
    return { type: 'delta', content: event.content };
  }
  if (event.kind === 'done') {
    return { type: 'done' };
  }
  return null;
}
