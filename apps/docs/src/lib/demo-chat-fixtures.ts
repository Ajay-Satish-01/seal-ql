import type { ChatApiResponse } from '@/lib/chat-api';
import { RATE_LIMIT_USER_MESSAGE } from '@/lib/api-error';
import {
  buildDemoChatMetadata,
  chatResponseToStreamMeta,
  type ChatStreamMeta,
} from '@/lib/execution-metadata';
import type { DemoPreset } from '@/lib/demo-fixtures';
import { chatMessageFromQuery } from '@/lib/doc-snippets';

export interface ChatStreamDemo {
  message: string;
  meta: ChatStreamMeta;
  answerText: string;
  streamError?: {
    code: string;
    message: string;
  };
}

export function chatResponseFromPreset(preset: DemoPreset): ChatApiResponse {
  const rows = preset.response.results;
  const top = rows[0];
  const summaryKey = top ? Object.keys(top)[0] : 'value';
  const summaryVal = top ? top[summaryKey] : null;

  return {
    session_id: 'demo-session-a1b2c3d4',
    message: [
      `Based on the query data, here's a concise summary for "${preset.query}".`,
      summaryVal != null
        ? `The top row shows ${summaryKey} = ${String(summaryVal)}.`
        : 'Results are available in the SQL preview below.',
      'All figures come from validated, read-only SQL against your schema.',
    ].join('\n\n'),
    sources: ['orders', 'products', 'events'].slice(0, Math.min(3, rows.length || 2)),
    sql: preset.response.sql,
    results: rows.slice(0, 5),
    chart: preset.response.chart as ChatApiResponse['chart'],
    columns: preset.response.columns,
    metadata: buildDemoChatMetadata({
      row_count: rows.length,
      execution_time_ms: 48,
      truncated: false,
      warnings: [],
      repair_attempts: 0,
    }),
  };
}

export function chatStreamDemoFromPreset(preset: DemoPreset): ChatStreamDemo {
  const chat = chatResponseFromPreset(preset);
  return {
    message: chatMessageFromQuery(preset.query),
    meta: chatResponseToStreamMeta(chat),
    answerText: chat.message,
  };
}

/** Simulated mid-stream failure (seal.error → stream_error). */
export function chatStreamErrorDemo(): NonNullable<ChatStreamDemo['streamError']> {
  return {
    code: 'rate_limit',
    message: RATE_LIMIT_USER_MESSAGE,
  };
}
