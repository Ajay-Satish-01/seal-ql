'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { demoPresets } from '@/lib/demo-fixtures';
import { chatResponseFromPreset, chatStreamDemoFromPreset } from '@/lib/demo-chat-fixtures';
import { ChatStreamErrorCallout } from '@/components/demo/chat-stream-error-callout';
import { chatMessageFromQuery } from '@/lib/doc-snippets';
import { QueryConsole } from '@/components/demo/query-console';
import { ResultsPanel } from '@/components/demo/results-panel';
import { SdkPanel } from '@/components/demo/sdk-panel';
import { ChatDemoPanel } from '@/components/demo/chat-demo-panel';
import { ChatStreamDemoPanel } from '@/components/demo/chat-stream-demo-panel';
import { Callout } from '@/components/docs/callout';

export default function DemoPage() {
  const [selectedId, setSelectedId] = useState(demoPresets[0]?.id ?? '');

  const preset = useMemo(
    () => demoPresets.find((p) => p.id === selectedId) ?? demoPresets[0],
    [selectedId],
  );

  const chatMessage = useMemo(
    () => (preset ? chatMessageFromQuery(preset.query) : ''),
    [preset],
  );

  const chatResponse = useMemo(
    () => (preset ? chatResponseFromPreset(preset) : null),
    [preset],
  );

  const streamDemo = useMemo(
    () => (preset ? chatStreamDemoFromPreset(preset) : null),
    [preset],
  );

  const handleSelect = (id: string) => {
    setSelectedId(id);
  };

  if (!preset || !chatResponse || !streamDemo) {
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
            Query &amp; chat demo
          </h1>
          <p className="text-muted-foreground max-w-2xl text-lg leading-relaxed">
            Explore NL → validated SQL → results → Vega-Lite charts and sample{' '}
            <code>/v1/chat</code> responses using pre-generated fixtures. Run a live API with{' '}
            <Link
              href="/docs/quickstart"
              className="text-primary underline-offset-4 hover:underline"
            >
              Quickstart
            </Link>{' '}
            or{' '}
            <Link
              href="/docs/self-hosting"
              className="text-primary underline-offset-4 hover:underline"
            >
              self-hosting
            </Link>
            .
          </p>
        </div>
      </div>

      <div className="container mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <Callout variant="info" title="Simulated output">
          Query, chart, and chat panels use the same pre-generated JSON as{' '}
          <code>make sync-docs-assets</code> fixtures — no API connection required. SDK snippets on
          the right use the default local base URL; point them at your deployment when integrating.
        </Callout>

        <div className="mt-8 grid gap-8 lg:grid-cols-12">
          <aside className="lg:col-span-3">
            <QueryConsole selectedId={preset.id} onSelect={handleSelect} query={preset.query} />
          </aside>
          <section className="lg:col-span-5">
            <h2 className="text-foreground mb-4 text-sm font-semibold tracking-wider uppercase">
              Query output
            </h2>
            <ResultsPanel response={preset.response} />
          </section>
          <aside className="lg:col-span-4">
            <h2 className="text-foreground mb-4 text-sm font-semibold tracking-wider uppercase">
              Integrate
            </h2>
            <SdkPanel query={preset.query} />
          </aside>
        </div>

        <div className="mt-12 grid gap-8 lg:grid-cols-2">
          <ChatDemoPanel message={chatMessage} response={chatResponse} />
          <div className="space-y-4">
            <ChatStreamDemoPanel demo={streamDemo} />
            <ChatStreamErrorCallout />
          </div>
        </div>
      </div>
    </main>
  );
}
