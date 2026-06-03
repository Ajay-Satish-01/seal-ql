/**
 * Canonical code examples for docs and demo — keep in sync with SDK method names.
 */
import { SITE } from '@/lib/constants';

export const DOC_API_KEY = 'your-api-key';

function escapeControlChars(value: string): string {
  return value
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '\\r')
    .replace(/\t/g, '\\t')
    .replace(/[\b]/g, '\\b')
    .replace(/\f/g, '\\f')
    .replace(/\v/g, '\\v');
}

function escapeForDoubleQuotedString(value: string): string {
  return escapeControlChars(value.replace(/\\/g, '\\\\').replace(/"/g, '\\"'));
}

function escapeForSingleQuotedString(value: string): string {
  return escapeControlChars(value.replace(/\\/g, '\\\\').replace(/'/g, "\\'"));
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
# Set SEAL_API_KEY in .env (see .env.example). For local dev, placeholder + SEAL_DEV_MODE=true is OK.

make up
make seed
# Workspace schema (first time or fresh DB):
docker compose exec -T postgres psql -U postgres -d seal < scripts/migrate_app.sql

make sync-catalog   # optional; API also syncs when CATALOG_AUTO_SYNC=true

curl -s http://localhost:8000/health
curl -H "X-API-Key: $SEAL_API_KEY" ${SITE.defaultBaseUrl}/v1/catalog | head`;
}

export function fullLocalVerifySnippet(): string {
  return `curl -s http://localhost:8000/health
curl -H "X-API-Key: $SEAL_API_KEY" ${SITE.defaultBaseUrl}/v1/schema | head
curl -H "X-API-Key: $SEAL_API_KEY" ${SITE.defaultBaseUrl}/v1/catalog | head
# Live E2E (optional; needs LLM configured):
make check-e2e`;
}

export function productionCatalogEnvSnippet(): string {
  return `# .env beside docker-compose.example.yml
mkdir config
DATA_CATALOG_PATH=/app/config/catalog.yaml
CATALOG_AUTO_SYNC=true
CHAT_ENHANCEMENT_ENABLED=true
CHAT_RECENT_MESSAGES=6
CHAT_ANSWER_PREVIEW_ROWS=20
CHAT_MAX_CONTEXT_TABLES=8
VECTOR_STORE=none`;
}

/** `seal` from `https://github.com/org/seal` */
export function githubRepoName(): string {
  return SITE.github.replace(/\/$/, '').split('/').pop() ?? 'seal';
}

function githubSlug(): string {
  return SITE.github.replace('https://github.com/', '').replace(/\/$/, '');
}

export function githubRawUrl(repoPath: string): string {
  return `https://raw.githubusercontent.com/${githubSlug()}/${SITE.githubDefaultBranch}/${repoPath}`;
}

export function githubBlobUrl(repoPath: string): string {
  return `${SITE.github}/blob/${SITE.githubDefaultBranch}/${repoPath}`;
}

const PROD_ENV_BLOCK = `export SEAL_API_KEY=$(openssl rand -hex 32)
printf '%s\\n' \\
  "SEAL_API_KEY=$SEAL_API_KEY" \\
  "SEAL_AUTH_REQUIRED=true" \\
  "SEAL_DEV_MODE=false" \\
  "SEAL_DISABLE_DOCS=true" \\
  > .env`;

/** Clone repo, dev .env, make up + seed (shared unpublished / contributor path). */
export function cloneFromSourceStackSnippet(options?: { silentCurl?: boolean }): string {
  const repo = githubRepoName();
  const curlFlag = options?.silentCurl ? '-s ' : '';
  return `git clone ${SITE.github}.git
cd ${repo}
cp .env.example .env
# Dev-friendly .env (SEAL_DEV_MODE=true). For production keys, see Self-hosting after registry publish.
make up
make seed
curl ${curlFlag}http://localhost:8000/health`;
}

export function selfHostingQuickStartSnippet(published: boolean = SITE.packagesPublished): string {
  if (published) {
    return `docker pull ${SITE.dockerImage}

mkdir seal && cd seal
# Download docker-compose.example.yml and seed.sql (links below)
${PROD_ENV_BLOCK}

docker compose -f docker-compose.example.yml up -d
curl http://localhost:8000/health`;
  }

  return cloneFromSourceStackSnippet();
}

export function quickstartIntegratorDockerSnippet(published: boolean = SITE.packagesPublished): string {
  if (published) {
    return `docker pull ${SITE.dockerImage}
mkdir seal-quickstart && cd seal-quickstart
curl -O ${githubRawUrl('apps/docs/public/compose/docker-compose.example.yml')}
curl -O ${githubRawUrl('apps/docs/public/samples/seed.sql')}

${PROD_ENV_BLOCK}

mkdir config
docker compose -f docker-compose.example.yml up -d
curl -s http://localhost:8000/health`;
  }

  return cloneFromSourceStackSnippet({ silentCurl: true });
}

export function sdkInstallSnippet(published: boolean = SITE.packagesPublished): string {
  if (published) {
    return `# Python
pip install ${SITE.pypiPackage}

# TypeScript / React
npm install ${SITE.npmPackage}
npm install react react-dom vega vega-lite vega-embed`;
  }

  return `# Planned: pip install ${SITE.pypiPackage}
# Today: from repo root
uv sync --all-packages --all-extras

# Planned: npm install ${SITE.npmPackage}
# Today:
cd sdks/typescript && pnpm install && pnpm build
npm install react react-dom vega vega-lite vega-embed`;
}

export function sdkInstallSnippetShort(published: boolean = SITE.packagesPublished): string {
  if (published) {
    return `pip install ${SITE.pypiPackage}
# or: npm install ${SITE.npmPackage}`;
  }

  return `# Planned: pip install ${SITE.pypiPackage} / npm install ${SITE.npmPackage}
# Today: uv sync from repo root, or build sdks/typescript`;
}

export function pythonSdkInstallSnippet(published: boolean = SITE.packagesPublished): string {
  if (published) {
    return `pip install ${SITE.pypiPackage}`;
  }
  return `# Planned: pip install ${SITE.pypiPackage}\n# Today: from repo root\nuv sync --all-packages --all-extras`;
}

export function typescriptSdkInstallSnippet(published: boolean = SITE.packagesPublished): string {
  if (published) {
    return `npm install ${SITE.npmPackage}
npm install react react-dom vega vega-lite vega-embed`;
  }
  return `# Planned: npm install ${SITE.npmPackage}
# Today:
cd sdks/typescript && pnpm install && pnpm build
npm install react react-dom vega vega-lite vega-embed`;
}
