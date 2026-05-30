'use client';

import Link from 'next/link';
import { Callout } from '@/components/docs/callout';
import { SITE } from '@/lib/constants';

interface DemoConnectionProps {
  baseUrl: string;
  apiKey: string;
  onBaseUrlChange: (url: string) => void;
  onApiKeyChange: (key: string) => void;
}

export function DemoConnection({
  baseUrl,
  apiKey,
  onBaseUrlChange,
  onApiKeyChange,
}: DemoConnectionProps) {
  const ready = baseUrl.trim().length > 0;

  return (
    <section className="border-border/60 bg-card/30 mb-10 rounded-xl border p-6">
      <h2 className="text-foreground mb-2 text-sm font-semibold tracking-wider uppercase">
        Live API connection
      </h2>
      <p className="text-muted-foreground mb-4 text-sm">
        Point chat panels at your self-hosted Seal API. Use{' '}
        <code className="text-foreground">{SITE.defaultBaseUrl}</code> after{' '}
        <code className="text-foreground">make up</code>.
      </p>

      <Callout variant="warning" title="Local development only">
        Do not embed <code>SEAL_API_KEY</code> in production frontends. Your backend should call
        Seal (BFF pattern). See{' '}
        <Link href="/docs/authentication" className="text-primary underline-offset-4 hover:underline">
          Authentication
        </Link>
        .
      </Callout>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <label className="text-sm">
          <span className="text-muted-foreground mb-1 block text-xs font-medium tracking-wide uppercase">
            API base URL
          </span>
          <input
            type="url"
            value={baseUrl}
            onChange={(e) => onBaseUrlChange(e.target.value)}
            className="border-border bg-background w-full rounded-md border px-3 py-2 font-mono text-sm"
            placeholder={SITE.defaultBaseUrl}
            autoComplete="off"
          />
        </label>
        <label className="text-sm">
          <span className="text-muted-foreground mb-1 block text-xs font-medium tracking-wide uppercase">
            API key (X-API-Key)
          </span>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => onApiKeyChange(e.target.value)}
            className="border-border bg-background w-full rounded-md border px-3 py-2 font-mono text-sm"
            placeholder="From .env SEAL_API_KEY"
            autoComplete="off"
          />
        </label>
      </div>

      {!ready ? (
        <p className="text-muted-foreground mt-3 text-xs" role="status">
          Enter a base URL to enable live chat.
        </p>
      ) : null}
    </section>
  );
}
