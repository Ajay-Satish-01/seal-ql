#!/usr/bin/env node
/** Copy shared metadata modules into the TypeScript SDK src/vendor for publishing. */
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { writeSdkRateLimitModule } from './rate-limit-python-sdk.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const vendorDir = resolve(root, 'sdks/typescript/src/vendor');
const keysSrc = resolve(root, 'config/stream_meta_metadata_keys.json');
const rateLimitSrc = resolve(root, 'config/rate_limit_markers.json');

const KEYS_IMPORT = '../config/stream_meta_metadata_keys.json';
const RATE_LIMIT_IMPORT = '../config/rate_limit_markers.json';

mkdirSync(vendorDir, { recursive: true });

copyFileSync(resolve(root, 'shared/stream-meta.ts'), resolve(vendorDir, 'stream-meta.ts'));
copyFileSync(resolve(root, 'shared/chat-sse-events.ts'), resolve(vendorDir, 'chat-sse-events.ts'));

let apiError = readFileSync(resolve(root, 'shared/api-error.ts'), 'utf8');
const rateLimitImportCount = apiError.match(
  new RegExp(RATE_LIMIT_IMPORT.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'),
)?.length;
if (rateLimitImportCount !== 1) {
  console.error(
    `api-error.ts: expected exactly one "${RATE_LIMIT_IMPORT}" import, found ${rateLimitImportCount ?? 0}`,
  );
  process.exit(1);
}
apiError = apiError.replace(RATE_LIMIT_IMPORT, './rate_limit_markers.json');
writeFileSync(resolve(vendorDir, 'api-error.ts'), apiError);
copyFileSync(keysSrc, resolve(vendorDir, 'stream_meta_metadata_keys.json'));
copyFileSync(rateLimitSrc, resolve(vendorDir, 'rate_limit_markers.json'));
copyFileSync(
  rateLimitSrc,
  resolve(root, 'packages/core/seal_core/llm/rate_limit_markers.json'),
);
copyFileSync(rateLimitSrc, resolve(root, 'sdks/python/seal/rate_limit_markers.json'));
writeSdkRateLimitModule(root);

let contract = readFileSync(resolve(root, 'shared/metadata-contract.ts'), 'utf8');
const occurrences = contract.match(
  new RegExp(KEYS_IMPORT.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'),
);
const count = occurrences?.length ?? 0;
if (count !== 1) {
  console.error(
    `metadata-contract.ts: expected exactly one "${KEYS_IMPORT}" import, found ${count}`,
  );
  process.exit(1);
}
contract = contract.replace(KEYS_IMPORT, './stream_meta_metadata_keys.json');
writeFileSync(resolve(vendorDir, 'metadata-contract.ts'), contract);

console.log('Synced shared metadata modules → sdks/typescript/src/vendor/');
