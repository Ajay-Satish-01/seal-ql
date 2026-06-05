import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { DocLink } from '@/components/docs/doc-link';
import { MetadataFieldList } from '@/components/docs/metadata-field-list';
import { MetadataJsonBlock } from '@/components/docs/metadata-json-block';
import {
  CHAT_METADATA_REFUSAL_JSON,
  CHAT_METADATA_SQL_JSON,
  CHAT_STREAM_META_JSON,
  CHAT_METADATA_EXTRA_FIELDS,
  QUERY_EXECUTION_FIELDS,
  QUERY_METADATA_JSON,
} from '@/lib/execution-metadata';

export default function ExecutionMetadataPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Execution metadata"
        description="Shared execution fields on /v1/query and /v1/chat — aligned across JSON and SSE seal.meta."
      />

      <Callout variant="info" title="Same pipeline, two response shapes">
        Query and chat both run <code>execute_natural_language_query</code> when SQL executes. Execution
        fields are identical; chat adds <code>metadata.enhancement</code>, <code>metadata.scope</code>,
        and refusal/error flags. Streaming chat exposes the same fields on the flat{' '}
        <code>seal.meta</code> payload (see <DocLink href="/docs/chat-streaming">SSE streaming</DocLink>
        ).
      </Callout>

      <h2 className="font-heading mt-8 text-xl font-semibold">Query — POST /v1/query</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        Nested under <code>metadata</code> on every successful response (top-level <code>sql</code>{' '}
        is separate):
      </p>
      <MetadataFieldList fields={QUERY_EXECUTION_FIELDS} />
      <MetadataJsonBlock code={QUERY_METADATA_JSON} className="mt-4" />

      <h2 className="font-heading mt-8 text-xl font-semibold">Chat JSON — stream=false</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        When SQL runs, <code>metadata</code> includes the execution block plus chat-specific keys:
      </p>
      <MetadataFieldList fields={CHAT_METADATA_EXTRA_FIELDS} />
      <MetadataJsonBlock title="Example (SQL ran)" code={CHAT_METADATA_SQL_JSON} className="mt-6" />
      <MetadataJsonBlock title="Example (refusal)" code={CHAT_METADATA_REFUSAL_JSON} className="mt-6" />

      <h2 className="font-heading mt-8 text-xl font-semibold">Chat SSE — seal.meta</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        The first SSE event is <code>event: seal.meta</code>. Its <code>data:</code> line is a{' '}
        <strong>flat</strong> JSON object (not wrapped in <code>metadata</code>):{' '}
        <code>session_id</code>, <code>sources</code>, <code>sql</code>, <code>results</code>,{' '}
        <code>columns</code>, <code>chart</code>, execution fields, and <code>enhancement</code> at
        the top level. OpenAPI schema: <code>ChatStreamMeta</code>.
      </p>
      <MetadataJsonBlock code={CHAT_STREAM_META_JSON} className="mt-4" />

      <Callout variant="info" title="Typed fields (OpenAPI)">
        OpenAPI components <code>ScopeMetadata</code>, <code>EnhancementInfo</code>, and{' '}
        <code>QueryMetadata</code> use constrained enums where applicable — for example{' '}
        <code>scope.source</code> is one of <code>heuristic</code>, <code>llm</code>,{' '}
        <code>limits</code>, <code>disabled</code>. TypeScript SDK types come from{' '}
        <code>make openapi-ts</code>; docs and the dashboard validate SSE payloads with{' '}
        <code>shared/stream-meta.ts</code> (unknown enum values fail client parse).
      </Callout>

      <Callout variant="info" title="Trust / explainability toggle">
        Set <code>SEAL_TRUST_EXPLAINABILITY_ENABLED=true</code> to expose SQL provenance (
        <code>tables_used</code>, <code>columns_used</code>, <code>catalog_matches</code>),{' '}
        <code>sources</code>, <code>scope</code>, and <code>repair_attempts</code>. Default is{' '}
        <code>false</code> so production deployments do not leak SQL or provenance unless
        explicitly enabled. See <DocLink href="/docs/configuration">Configuration</DocLink>.
      </Callout>

      <Callout variant="info" title="Strict validation">
        Set <code>STRICT_STREAM_META_VALIDATION=true</code> (alias{' '}
        <code>STRICT_METADATA_VALIDATION</code>) to fail requests when metadata or{' '}
        <code>seal.meta</code> fail contract validation (default: log warning only). See{' '}
        <DocLink href="/docs/configuration">Configuration</DocLink>.
      </Callout>

      <Callout variant="info" title="unavailable_reason vs refusals">
        <code>metadata.enhancement.unavailable_reason</code> can appear on guardrails refusals when
        the client sends <code>enhancement: true</code> but the deployment has no orchestrator. It is
        omitted when an orchestrator is configured and the turn is a refusal (enhancement is off for
        that path).
      </Callout>

      <Callout variant="warning" title="used_sql semantics">
        <code>used_sql: true</code> only after successful SQL execution. Failed planner/executor paths
        set <code>metadata.sql_error: true</code> with <code>used_sql: false</code> and no{' '}
        <code>sql</code>.
      </Callout>

      <h2 className="font-heading mt-8 text-xl font-semibold">Related</h2>
      <ul className="text-muted-foreground mt-4 list-disc space-y-2 pl-6 text-sm">
        <li>
          <DocLink href="/docs/multi-database">Multi-database routing</DocLink> —{' '}
          <code>database_id</code> on every request
        </li>
        <li>
          <DocLink href="/docs/prompt-enhancement">Prompt enhancement</DocLink> —{' '}
          <code>metadata.enhancement.*</code>
        </li>
        <li>
          <DocLink href="/docs/guardrails">Guardrails</DocLink> —{' '}
          <code>metadata.scope.source</code> and <code>metadata.suggested_queries</code> on refusal
        </li>
        <li>
          <DocLink href="/docs/api-reference">API reference</DocLink> — OpenAPI components{' '}
          <code>QueryMetadata</code>, <code>ChatMetadata</code>, <code>ScopeMetadata</code>,{' '}
          <code>ChatStreamMeta</code>
        </li>
        <li>
          <DocLink href="/demo">Interactive demo</DocLink> — fixture chat panels show metadata JSON
        </li>
      </ul>
    </div>
  );
}
