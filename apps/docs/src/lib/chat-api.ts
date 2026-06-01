import { formatApiError } from '@/lib/api-error';
import type { ChatMetadata, ChatStreamMeta, ColumnDescriptor } from '@/lib/execution-metadata';
import { flushSseRemainder, splitSseBuffer, type SseParseResult } from '@/lib/sse-parse';
import { mapChatSseEvent, type ChatStreamEvent } from '@seal/chat-sse-events';

export type { ChatMetadata, ChatStreamMeta, ColumnDescriptor, EnhancementMetadata } from '@/lib/execution-metadata';

export type { ChatStreamEvent };

export interface ChatApiResponse {
  session_id: string;
  message: string;
  sources?: string[];
  sql?: string | null;
  results?: ReadonlyArray<Record<string, unknown>> | null;
  chart?: Record<string, unknown> | null;
  columns?: ReadonlyArray<ColumnDescriptor> | null;
  metadata?: ChatMetadata;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '');
}

function authHeaders(apiKey?: string): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (apiKey) headers['X-API-Key'] = apiKey;
  return headers;
}

async function readError(res: Response): Promise<never> {
  const detail = await res.text();
  throw new Error(formatApiError(res.status, detail));
}

export async function postChat(
  baseUrl: string,
  body: {
    message: string;
    session_id?: string;
    include_charts?: boolean;
    stream?: boolean;
    enhancement?: boolean;
  },
  apiKey?: string,
  signal?: AbortSignal,
): Promise<ChatApiResponse> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/chat`, {
    method: 'POST',
    headers: authHeaders(apiKey),
    body: JSON.stringify({ stream: false, ...body }),
    signal,
  });
  if (!res.ok) await readError(res);
  return res.json() as Promise<ChatApiResponse>;
}

function mapSseEvent(event: SseParseResult): ChatStreamEvent | null {
  if (event.kind === 'meta' || event.kind === 'delta' || event.kind === 'done') {
    return mapChatSseEvent(event);
  }
  return null;
}

export async function* streamChat(
  baseUrl: string,
  body: {
    message: string;
    session_id?: string;
    include_charts?: boolean;
    enhancement?: boolean;
  },
  apiKey?: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/chat`, {
    method: 'POST',
    headers: authHeaders(apiKey),
    body: JSON.stringify({ stream: true, ...body }),
    signal,
  });
  if (!res.ok) await readError(res);

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const { events, remainder } = splitSseBuffer(buffer);
      buffer = remainder;
      for (const raw of events) {
        const mapped = mapSseEvent(raw);
        if (mapped) yield mapped;
      }
    }
    buffer += decoder.decode();
    const { events: tailEvents, remainder } = splitSseBuffer(buffer);
    for (const raw of [...tailEvents, ...flushSseRemainder(remainder)]) {
      const mapped = mapSseEvent(raw);
      if (mapped) yield mapped;
    }
  } finally {
    await reader.cancel().catch(() => {});
  }
}
