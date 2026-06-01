#!/usr/bin/env node
/** Copy shared metadata modules into the TypeScript SDK src/vendor for publishing. */
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const vendorDir = resolve(root, 'sdks/typescript/src/vendor');
const keysSrc = resolve(root, 'config/stream_meta_metadata_keys.json');

const KEYS_IMPORT = '../config/stream_meta_metadata_keys.json';

mkdirSync(vendorDir, { recursive: true });

copyFileSync(resolve(root, 'shared/stream-meta.ts'), resolve(vendorDir, 'stream-meta.ts'));
copyFileSync(resolve(root, 'shared/chat-sse-events.ts'), resolve(vendorDir, 'chat-sse-events.ts'));
copyFileSync(keysSrc, resolve(vendorDir, 'stream_meta_metadata_keys.json'));

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
