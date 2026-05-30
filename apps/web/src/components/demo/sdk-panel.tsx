'use client';

import { useState } from 'react';
import { CodeBlock } from '@/components/code-block';
import { SITE } from '@/lib/constants';
import { cn } from '@/lib/utils';

type Tab = 'python' | 'typescript' | 'curl';

function escapePythonString(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

function escapeTsString(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

interface SdkPanelProps {
  query: string;
  baseUrl: string;
  onBaseUrlChange: (url: string) => void;
}

function buildPythonSnippet(query: string, baseUrl: string): string {
  const q = escapePythonString(query);
  const url = escapePythonString(baseUrl);
  return `from seal import Seal

with Seal("${url}") as client:
    result = client.query("${q}")

print(result.sql)
print(result.results)
if result.chart:
    print(result.chart.chart_type)
    print(result.chart.vega_lite_spec)`;
}

function buildTypeScriptSnippet(query: string, baseUrl: string): string {
  const q = escapePythonString(query);
  const url = escapeTsString(baseUrl);
  return `import { Seal, VegaChart } from 'seal';

const client = new Seal({
  baseUrl: '${url}',
});

const result = await client.query("${q}");

console.log(result.sql, result.results);

// In React:
// <VegaChart spec={result.chart} theme="dark" />`;
}

function buildCurlSnippet(query: string, baseUrl: string): string {
  const body = JSON.stringify({ query, database_id: 'default' }, null, 2);
  return `curl -s -X POST "${baseUrl}/v1/query" \\
  -H "Content-Type: application/json" \\
  -d '${body.replace(/'/g, "'\\''")}'`;
}

export function SdkPanel({ query, baseUrl, onBaseUrlChange }: SdkPanelProps) {
  const [tab, setTab] = useState<Tab>('python');

  const tabs: { id: Tab; label: string }[] = [
    { id: 'python', label: 'Python' },
    { id: 'typescript', label: 'TypeScript' },
    { id: 'curl', label: 'curl' },
  ];

  const code =
    tab === 'python'
      ? buildPythonSnippet(query, baseUrl)
      : tab === 'typescript'
        ? buildTypeScriptSnippet(query, baseUrl)
        : buildCurlSnippet(query, baseUrl);

  const lang = tab === 'curl' ? 'bash' : tab;

  return (
    <div className="space-y-4">
      <div>
        <label
          htmlFor="base-url"
          className="text-muted-foreground mb-2 block text-xs font-medium tracking-wider uppercase"
        >
          API base URL
        </label>
        <input
          id="base-url"
          type="url"
          value={baseUrl}
          onChange={(e) => onBaseUrlChange(e.target.value)}
          className="border-input bg-background w-full rounded-md border px-3 py-2 font-mono text-sm"
          placeholder={SITE.defaultBaseUrl}
        />
        <p className="text-muted-foreground mt-2 text-xs">
          Point at your self-hosted API after{' '}
          <code className="text-foreground">docker compose up</code>.
        </p>
      </div>

      <div className="border-border/50 flex gap-1 border-b">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              '-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors',
              tab === t.id
                ? 'border-primary text-foreground'
                : 'text-muted-foreground hover:text-foreground border-transparent',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <CodeBlock language={lang} code={code} />

      <p className="text-muted-foreground text-xs leading-relaxed">
        This page uses pre-generated JSON. Install the SDK and set{' '}
        <code className="text-foreground">baseUrl</code> to your running container for live queries.
      </p>
    </div>
  );
}
