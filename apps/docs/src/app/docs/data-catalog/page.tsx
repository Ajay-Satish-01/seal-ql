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
    <div className="w-full">
      <PageHeader
        title="Data catalog"
        description="Auto-generated YAML with optional business descriptions — used globally by chat and query."
      />

      <Callout variant="info" title="You only edit descriptions">
        Seal generates <code>config/catalog.yaml</code> from introspection. Add{' '}
        <code>table_description</code> for tables and hypertables, or <code>view_description</code>{' '}
        for views and continuous aggregates. Re-run sync after migrations; your text is preserved.
      </Callout>

      <Callout variant="info" title="Dashboard storage (Postgres primary)">
        The operational dashboard (<Link href="/docs/dashboard">port 3001</Link>) saves description
        overrides to <code>seal_app.workspace_kv</code> in Postgres. YAML on disk is rebuilt on{' '}
        <code>POST /v1/catalog/sync</code>; overrides are re-applied from the database after sync. If
        a description exists only in YAML and not in the DB, it may be replaced on the next sync —
        use the dashboard or API <code>PATCH /v1/catalog/descriptions</code> for durable edits.
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

      <h2 className="font-heading mt-8 text-xl font-semibold">Catalog YAML structure</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        The generated YAML contains one entry per table/view with columns, types, and optional
        descriptions. The planner and enhancement chain use these descriptions to ground SQL
        generation.
      </p>
      <CodeBlock
        language="yaml"
        code={`tables:
  - schema_name: public
    table_name: orders
    table_description: "Customer purchase orders with timestamps and amounts"
    columns:
      - column_name: id
        data_type: integer
        is_nullable: false
      - column_name: customer_id
        data_type: integer
        is_nullable: false
      - column_name: amount
        data_type: numeric
        is_nullable: true
      - column_name: created_at
        data_type: timestamp with time zone
        is_nullable: false
    primary_key: [id]
    foreign_keys:
      - column: customer_id
        references_table: customers
        references_column: id`}
      />

      <h2 className="font-heading mt-8 text-xl font-semibold">API</h2>
      <h3 className="text-foreground mt-4 text-lg font-medium">List catalog</h3>
      <CodeBlock language="bash" code={curlWithAuth(base, 'GET', '/v1/catalog')} />
      <p className="text-muted-foreground mt-2 text-sm">Example response (abbreviated):</p>
      <CodeBlock
        language="json"
        code={`{
  "tables": [
    {
      "schema_name": "public",
      "table_name": "orders",
      "table_description": "Customer purchase orders with timestamps and amounts",
      "columns": [
        { "column_name": "id", "data_type": "integer", "is_nullable": false },
        { "column_name": "amount", "data_type": "numeric", "is_nullable": true }
      ]
    }
  ]
}`}
      />

      <h3 className="text-foreground mt-4 text-lg font-medium">Sync catalog from schema</h3>
      <CodeBlock
        language="bash"
        code={curlWithAuth(base, 'POST', '/v1/catalog/sync')}
      />

      <h3 className="text-foreground mt-4 text-lg font-medium">Update descriptions</h3>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        Descriptions are stored in workspace (Postgres) and survive catalog syncs. Use the
        dashboard editor or this API:
      </p>
      <CodeBlock
        language="bash"
        code={curlWithAuth(base, 'PATCH', '/v1/catalog/descriptions', {
          descriptions: {
            'public.orders': 'Customer purchase orders with timestamps, amounts, and shipping status',
            'public.customers': 'Registered customer accounts with contact information',
          },
        })}
      />
      <p className="text-muted-foreground mt-2 text-sm">
        Format: <code>{'{'}schema.table_name: description{'}'}</code>. Existing descriptions for
        unlisted tables are preserved.
      </p>

      <h2 className="font-heading mt-8 text-xl font-semibold">SDK</h2>
      <CodeBlock language="python" code={pythonCatalogSnippet(base)} />
      <CodeBlock language="typescript" code={tsCatalogSnippet(base)} />

      <h2 className="font-heading mt-8 text-xl font-semibold">Curation loop (edit → save → query)</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        Descriptions you save are merged into the live catalog registry immediately — the{' '}
        <strong>next</strong> <code>POST /v1/query</code> or chat turn uses your text. No API restart
        is required.
      </p>
      <ol className="text-muted-foreground mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed">
        <li>
          Open the operational dashboard <Link href="/docs/dashboard">Catalog page</Link> (port 3001)
          or call <code>PATCH /v1/catalog/descriptions</code>.
        </li>
        <li>
          Edit a table description and click <strong>Save descriptions</strong>. The dashboard
          shows an <em>Active override</em> badge and a confirmation that overrides are live for
          planning.
        </li>
        <li>
          Run a query or chat message on the same API instance. The planner reads your description
          from the in-memory registry.
        </li>
        <li>
          After a schema migration, run <code>POST /v1/catalog/sync</code>. YAML is rebuilt from
          introspection; Postgres overrides are <strong>re-applied</strong> (see{' '}
          <code>preserved</code> in the sync response).
        </li>
      </ol>

      <Callout variant="success" title="Try it">
        Add a distinctive description to <code>public.orders</code>, save, then ask{' '}
        <em>&quot;What is total revenue from completed orders?&quot;</em> on{' '}
        <Link href="/demo">/demo</Link> or the dashboard Query page. Compare SQL table choice before
        and after.
      </Callout>

      <h2 className="font-heading mt-8 text-xl font-semibold">How descriptions improve answers</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        Without descriptions, the planner sees only column names and types. Adding a description
        like <em>&quot;Customer purchase orders with timestamps and amounts&quot;</em> helps the
        LLM understand that <code>orders</code> is the right table for revenue questions. Better
        descriptions lead to more accurate SQL and fewer repair attempts. When{' '}
        <Link href="/docs/trust-explainability" className="text-primary underline-offset-4 hover:underline">
          trust explainability
        </Link>{' '}
        is enabled, <code>catalog_matches</code> in the response shows which descriptions were
        matched.
      </p>

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
