'use client';

import { useState } from 'react';
import { CodeBlock } from '@/components/code-block';
import { SITE } from '@/lib/constants';
import {
  curlChat,
  curlWithAuth,
  pythonCatalogSnippet,
  pythonChatSnippet,
  pythonChatStreamSnippet,
  pythonQuerySnippet,
  tsCatalogSnippet,
  tsChatSnippet,
  tsChatStreamSnippet,
  tsQuerySnippet,
  chatMessageFromQuery,
} from '@/lib/doc-snippets';
import { cn } from '@/lib/utils';

type LangTab = 'python' | 'typescript' | 'curl';
type ModeTab = 'query' | 'chat' | 'catalog' | 'stream';

interface SdkPanelProps {
  query: string;
}

export function SdkPanel({ query }: SdkPanelProps) {
  const [lang, setLang] = useState<LangTab>('python');
  const [mode, setMode] = useState<ModeTab>('query');

  const chatMessage = chatMessageFromQuery(query);

  const langTabs: { id: LangTab; label: string }[] = [
    { id: 'python', label: 'Python' },
    { id: 'typescript', label: 'TypeScript' },
    { id: 'curl', label: 'curl' },
  ];

  const modeTabs: { id: ModeTab; label: string }[] = [
    { id: 'query', label: 'Query' },
    { id: 'chat', label: 'Chat' },
    { id: 'stream', label: 'Stream' },
    { id: 'catalog', label: 'Catalog' },
  ];

  const code = (() => {
    const b = SITE.defaultBaseUrl;
    if (mode === 'query') {
      if (lang === 'python') return pythonQuerySnippet(b, query);
      if (lang === 'typescript') return tsQuerySnippet(b, query);
      return curlWithAuth(b, 'POST', '/v1/query', { query, database_id: 'default' });
    }
    if (mode === 'chat') {
      if (lang === 'python') return pythonChatSnippet(b, chatMessage, { includeCharts: true });
      if (lang === 'typescript') return tsChatSnippet(b, chatMessage, { includeCharts: true });
      return curlChat(b, chatMessage, { includeCharts: true });
    }
    if (mode === 'stream') {
      if (lang === 'python') return pythonChatStreamSnippet(b, chatMessage);
      if (lang === 'typescript') return tsChatStreamSnippet(b, chatMessage);
      return curlChat(b, chatMessage, { stream: true, includeCharts: true });
    }
    if (lang === 'python') return pythonCatalogSnippet(b);
    if (lang === 'typescript') return tsCatalogSnippet(b);
    return curlWithAuth(b, 'GET', '/v1/catalog');
  })();

  const blockLang = lang === 'curl' ? 'bash' : lang;

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground text-xs">
        Snippets target <code className="text-foreground">{SITE.defaultBaseUrl}</code>. Replace with
        your API URL and set <code className="text-foreground">apiKey</code> when{' '}
        <code className="text-foreground">SEAL_API_KEY</code> is enabled.
      </p>

      <div className="border-border/50 flex flex-wrap gap-1 border-b">
        {modeTabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setMode(t.id)}
            className={cn(
              '-mb-px border-b-2 px-3 py-2 text-xs font-medium tracking-wide uppercase transition-colors',
              mode === t.id
                ? 'border-primary text-foreground'
                : 'text-muted-foreground hover:text-foreground border-transparent',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="border-border/50 flex gap-1 border-b">
        {langTabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setLang(t.id)}
            className={cn(
              '-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors',
              lang === t.id
                ? 'border-primary text-foreground'
                : 'text-muted-foreground hover:text-foreground border-transparent',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <CodeBlock language={blockLang} code={code} />

      <p className="text-muted-foreground text-xs leading-relaxed">
        Query tab matches the preset above. Chat and stream tabs mirror the simulated panels below.
        Docs:{' '}
        <a href="/docs/integration-guide" className="text-primary underline-offset-4 hover:underline">
          Integration guide
        </a>
        .
      </p>
    </div>
  );
}
