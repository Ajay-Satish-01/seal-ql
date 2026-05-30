/**
 * SSE parsing for POST /v1/chat stream responses.
 * Keep apps/web/src/lib/sse-parse.ts in sync when changing this module.
 */

export type SseParseResult =
  | { kind: 'meta'; data: Record<string, unknown> }
  | { kind: 'delta'; content: string }
  | { kind: 'done' };

/** Parse one SSE event block (lines between blank-line separators). */
export function parseSseEventBlock(part: string): SseParseResult | null {
  const lines = part.split('\n');
  let eventName = '';
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).replace(/^\s/, ''));
    }
  }

  if (dataLines.length === 0) return null;
  const dataLine = dataLines.join('\n');
  if (dataLine === '[DONE]') return { kind: 'done' };

  if (eventName === 'seal.meta') {
    try {
      return { kind: 'meta', data: JSON.parse(dataLine) as Record<string, unknown> };
    } catch {
      return null;
    }
  }

  try {
    const payload = JSON.parse(dataLine) as {
      choices?: Array<{ delta?: { content?: string } }>;
    };
    const content = payload.choices?.[0]?.delta?.content;
    if (content) return { kind: 'delta', content };
  } catch {
    return null;
  }
  return null;
}

/** Split buffer on event boundaries and return [events, remainder]. */
export function splitSseBuffer(buffer: string): {
  events: SseParseResult[];
  remainder: string;
} {
  const events: SseParseResult[] = [];
  const parts = buffer.split('\n\n');
  const remainder = parts.pop() ?? '';
  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;
    const event = parseSseEventBlock(trimmed);
    if (event) events.push(event);
  }
  return { events, remainder };
}

/** Parse trailing buffer when the stream closes without a final blank line. */
export function flushSseRemainder(remainder: string): SseParseResult[] {
  const trimmed = remainder.trim();
  if (!trimmed) return [];
  const event = parseSseEventBlock(trimmed);
  return event ? [event] : [];
}
