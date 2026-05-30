import Link from 'next/link';
import { Callout } from '@/components/docs/callout';
import { CodeBlock } from '@/components/code-block';
import { PageHeader } from '@/components/page-header';
import { SITE } from '@/lib/constants';
import {
  curlWithAuth,
  productionCatalogEnvSnippet,
  pythonCatalogSnippet,
  tsCatalogSnippet,
} from '@/lib/doc-snippets';

export default function DataCatalogPage() {
  const base = SITE.defaultBaseUrl;

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Data catalog"
        description="Auto-generated YAML with optional business descriptions — used globally by chat and query."
      />

      <Callout variant="info" title="You only edit descriptions">
        Seal generates <code>config/catalog.yaml</code> from introspection. Add{' '}
        <code>table_description</code> for tables and hypertables, or <code>view_description</code>{' '}
        for views and continuous aggregates. Re-run sync after migrations; your text is preserved.
      </Callout>

      <h2 className="font-heading mt-8 text-xl font-semibold">Setup</h2>
      <h3 className="text-foreground mt-4 text-lg font-medium">Develop from source</h3>
      <CodeBlock
        language="bash"
        code={`make up && make seed
make sync-catalog          # writes config/catalog.yaml
# edit descriptions in config/catalog.yaml`}
      />
      <h3 className="text-foreground mt-4 text-lg font-medium">Production Docker</h3>
      <CodeBlock language="bash" code={productionCatalogEnvSnippet()} />
      <p className="text-muted-foreground mt-2 text-sm">
        Mount <code>./config:/app/config</code> on the API service (included in{' '}
        <a href="/compose/docker-compose.example.yml" className="text-primary underline-offset-4 hover:underline">
          docker-compose.example.yml
        </a>
        ). Sample entries:{' '}
        <a href="/config/catalog.example.yaml" className="text-primary underline-offset-4 hover:underline">
          catalog.example.yaml
        </a>
        .
      </p>

      <h2 className="font-heading mt-8 text-xl font-semibold">API</h2>
      <CodeBlock language="bash" code={curlWithAuth(base, 'GET', '/v1/catalog')} />
      <CodeBlock
        language="bash"
        code={curlWithAuth(base, 'POST', '/v1/catalog/sync')}
      />

      <h2 className="font-heading mt-8 text-xl font-semibold">SDK</h2>
      <CodeBlock language="python" code={pythonCatalogSnippet(base)} />
      <CodeBlock language="typescript" code={tsCatalogSnippet(base)} />

      <p className="text-muted-foreground mt-6 text-sm">
        Used automatically by <Link href="/docs/chat-qa" className="text-primary underline-offset-4 hover:underline">Chat</Link> and{' '}
        <code>POST /v1/query</code>. Configure enhancement:{' '}
        <Link href="/docs/prompt-enhancement" className="text-primary underline-offset-4 hover:underline">
          Prompt enhancement
        </Link>
        .
      </p>
    </div>
  );
}
