/**
 * Canonical code examples for docs and demo — keep in sync with SDK method names.
 */
import { SITE } from '@/lib/constants';

export const DOC_API_KEY = 'your-api-key';

function escapeForDoubleQuotedString(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

function escapeForSingleQuotedString(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function escapeForShellSingleQuoted(value: string): string {
  return value.replace(/'/g, "'\\''");
}

export function curlWithAuth(
  baseUrl: string,
  method: string,
  path: string,
  body?: Record<string, unknown>,
): string {
  const url = `${baseUrl.replace(/\/+$/, '')}${path}`;
  const lines = [`curl -s -X ${method} "${url}"`];
  if (body) {
    lines.push('  -H "Content-Type: application/json" \\');
  }
  lines.push(`  -H "X-API-Key: ${DOC_API_KEY}"`);
  if (body) {
    const json = JSON.stringify(body);
    lines.push(`  -d '${escapeForShellSingleQuoted(json)}'`);
  }
  return lines.join(' \\\n');
}

export function curlChat(
  baseUrl: string,
  message: string,
  opts?: { sessionId?: string; includeCharts?: boolean; stream?: boolean },
): string {
  const body: Record<string, unknown> = {
    message,
    include_charts: opts?.includeCharts ?? false,
    stream: opts?.stream ?? false,
  };
  if (opts?.sessionId) body.session_id = opts.sessionId;
  const prefix = opts?.stream ? 'curl -N' : 'curl -s';
  const url = `${baseUrl.replace(/\/+$/, '')}/v1/chat`;
  const json = escapeForShellSingleQuoted(JSON.stringify(body));
  return `${prefix} -X POST "${url}" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: ${DOC_API_KEY}" \\
  -d '${json}'`;
}

export function pythonQuerySnippet(baseUrl: string, query: string): string {
  const q = escapeForDoubleQuotedString(query);
  const url = escapeForDoubleQuotedString(baseUrl);
  return `from seal import Seal

with Seal("${url}", api_key="${DOC_API_KEY}") as client:
    result = client.query("${q}")

print(result.sql)
print(result.results)
if result.chart:
    print(result.chart.chart_type)`;
}

export function pythonChatSnippet(
  baseUrl: string,
  message: string,
  opts?: { sessionId?: string; includeCharts?: boolean },
): string {
  const m = escapeForDoubleQuotedString(message);
  const url = escapeForDoubleQuotedString(baseUrl);
  const session = opts?.sessionId
    ? `\n        session_id="${escapeForDoubleQuotedString(opts.sessionId)}",`
    : '';
  const charts = opts?.includeCharts ? '\n        include_charts=True,' : '';
  return `from seal import Seal

with Seal("${url}", api_key="${DOC_API_KEY}") as client:
    reply = client.chat(
        "${m}",${session}${charts}
    )
    print(reply.session_id, reply.message)
    if reply.sql:
        print(reply.sql)
    if reply.chart:
        print(reply.chart.chart_type)`;
}

export function pythonChatStreamSnippet(baseUrl: string, message: string): string {
  const m = escapeForDoubleQuotedString(message);
  const url = escapeForDoubleQuotedString(baseUrl);
  return `from seal import Seal

with Seal("${url}", api_key="${DOC_API_KEY}") as client:
    for event in client.chat_stream("${m}", include_charts=True):
        if event["type"] == "meta":
            print(event["data"].get("sql"))
        elif event["type"] == "delta":
            print(event["content"], end="", flush=True)`;
}

export function pythonCatalogSnippet(baseUrl: string): string {
  const url = escapeForDoubleQuotedString(baseUrl);
  return `from seal import Seal

with Seal("${url}", api_key="${DOC_API_KEY}") as client:
    catalog = client.catalog()
    for entry in catalog.tables:
        print(entry.get("name"), entry.get("table_description"))`;
}

export function tsQuerySnippet(baseUrl: string, query: string): string {
  const q = escapeForSingleQuotedString(query);
  const url = escapeForSingleQuotedString(baseUrl);
  return `import { Seal, VegaChart } from 'seal';

const client = new Seal({
  baseUrl: '${url}',
  apiKey: '${DOC_API_KEY}',
});

const result = await client.query('${q}');
console.log(result.sql, result.results);
// <VegaChart spec={result.chart} theme="dark" />`;
}

export function tsChatSnippet(
  baseUrl: string,
  message: string,
  opts?: { sessionId?: string; includeCharts?: boolean },
): string {
  const m = escapeForSingleQuotedString(message);
  const url = escapeForSingleQuotedString(baseUrl);
  const options: string[] = [];
  if (opts?.includeCharts) options.push('includeCharts: true');
  if (opts?.sessionId) {
    options.push(`sessionId: '${escapeForSingleQuotedString(opts.sessionId)}'`);
  }
  const optStr = options.length ? `, { ${options.join(', ')} }` : '';
  return `import { Seal } from 'seal';

const client = new Seal({
  baseUrl: '${url}',
  apiKey: '${DOC_API_KEY}',
});

const reply = await client.chat('${m}'${optStr});
console.log(reply.session_id, reply.message, reply.sql);`;
}

export function tsChatStreamSnippet(baseUrl: string, message: string): string {
  const m = escapeForSingleQuotedString(message);
  const url = escapeForSingleQuotedString(baseUrl);
  return `import { Seal } from 'seal';

const client = new Seal({
  baseUrl: '${url}',
  apiKey: '${DOC_API_KEY}',
});

for await (const event of client.chatStream('${m}', { includeCharts: true })) {
  if (event.type === 'meta') console.log(event.data.sql, event.data.chart);
  if (event.type === 'delta') process.stdout.write(event.content);
}`;
}

export function tsCatalogSnippet(baseUrl: string): string {
  const url = escapeForSingleQuotedString(baseUrl);
  return `import { Seal } from 'seal';

const client = new Seal({
  baseUrl: '${url}',
  apiKey: '${DOC_API_KEY}',
});

const catalog = await client.catalog();
console.log(catalog.tables);`;
}

/** Chat example message derived from a query preset (for SDK panel). */
export function chatMessageFromQuery(query: string): string {
  const trimmed = query.trim();
  if (trimmed.length > 100) {
    return 'Summarize revenue by product category';
  }
  return trimmed.endsWith('?') ? trimmed : `${trimmed}?`;
}

export function localDevSetupSnippet(): string {
  return `cp .env.example .env
make up
make seed
make sync-catalog   # optional; API also syncs when CATALOG_AUTO_SYNC=true

curl -H "X-API-Key: $SEAL_API_KEY" ${SITE.defaultBaseUrl}/v1/catalog`;
}

export function productionCatalogEnvSnippet(): string {
  return `# .env beside docker-compose.example.yml
mkdir config
DATA_CATALOG_PATH=/app/config/catalog.yaml
CATALOG_AUTO_SYNC=true
CHAT_ENHANCEMENT_ENABLED=true
VECTOR_STORE=none`;
}
