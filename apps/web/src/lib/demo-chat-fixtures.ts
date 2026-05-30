import type { ChatApiResponse, ChatStreamMeta } from '@/lib/chat-api';
import type { DemoPreset } from '@/lib/demo-fixtures';
import { chatMessageFromQuery } from '@/lib/doc-snippets';

export interface ChatStreamDemo {
  message: string;
  meta: ChatStreamMeta;
  answerText: string;
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
    metadata: {
      used_sql: true,
      repair_attempts: 0,
      enhancement: { applied: ['schema_aware', 'multi_turn'] },
    },
  };
}

export function chatStreamDemoFromPreset(preset: DemoPreset): ChatStreamDemo {
  const chat = chatResponseFromPreset(preset);
  return {
    message: chatMessageFromQuery(preset.query),
    meta: {
      session_id: chat.session_id,
      sources: chat.sources,
      sql: chat.sql,
      chart: chat.chart,
      enhancement: chat.metadata?.enhancement as Record<string, unknown> | undefined,
    },
    answerText: chat.message,
  };
}
