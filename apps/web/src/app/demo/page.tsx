'use client';

import { useMemo, useState, useTransition } from 'react';
import Link from 'next/link';
import { demoPresets } from '@/lib/demo-fixtures';
import { SITE } from '@/lib/constants';
import { QueryConsole } from '@/components/demo/query-console';
import { ResultsPanel } from '@/components/demo/results-panel';
import { SdkPanel } from '@/components/demo/sdk-panel';
import { Callout } from '@/components/docs/callout';

export default function DemoPage() {
  const [selectedId, setSelectedId] = useState(demoPresets[0]?.id ?? '');
  const [baseUrl, setBaseUrl] = useState<string>(SITE.defaultBaseUrl);
  const [, startTransition] = useTransition();

  const preset = useMemo(
    () => demoPresets.find((p) => p.id === selectedId) ?? demoPresets[0],
    [selectedId],
  );

  const handleSelect = (id: string) => {
    startTransition(() => setSelectedId(id));
  };

  if (!preset) {
    return null;
  }

  return (
    <main className="flex-1">
      <div className="border-border/40 hero-grid border-b">
        <div className="container mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:py-16">
          <p className="text-primary mb-2 font-mono text-xs tracking-widest uppercase">
            Interactive demo
          </p>
          <h1 className="font-heading mb-4 text-3xl font-semibold tracking-tight md:text-4xl">
            Sample query flow — no install required
          </h1>
          <p className="text-muted-foreground max-w-2xl text-lg leading-relaxed">
            Explore natural language → validated SQL → results → Vega-Lite charts using sample data
            aligned with our analytics seed schema. Connect your SDK to a{' '}
            <Link
              href="/docs/self-hosting"
              className="text-primary underline-offset-4 hover:underline"
            >
              Docker-hosted API
            </Link>{' '}
            for live queries.
          </p>
        </div>
      </div>

      <div className="container mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <Callout variant="info" title="Simulated output">
          Responses are pre-generated with the same <code>ChartEngine</code> used in production.
          Change the base URL in the SDK panel to match your self-hosted instance.
        </Callout>

        <div className="mt-8 grid gap-8 lg:grid-cols-12">
          <aside className="lg:col-span-3">
            <QueryConsole selectedId={preset.id} onSelect={handleSelect} query={preset.query} />
          </aside>
          <section className="lg:col-span-5">
            <h2 className="text-foreground mb-4 text-sm font-semibold tracking-wider uppercase">
              Output
            </h2>
            <ResultsPanel response={preset.response} />
          </section>
          <aside className="lg:col-span-4">
            <h2 className="text-foreground mb-4 text-sm font-semibold tracking-wider uppercase">
              Integrate
            </h2>
            <SdkPanel query={preset.query} baseUrl={baseUrl} onBaseUrlChange={setBaseUrl} />
          </aside>
        </div>
      </div>
    </main>
  );
}
