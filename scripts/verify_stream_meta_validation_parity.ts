/**
 * Verifies parseStreamMeta pass/fail matches tests/fixtures/stream_meta_validation_matrix.json.
 * Run: cd apps/docs && pnpm run verify:stream-meta (or `make check`)
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { parseStreamMeta } from '../shared/stream-meta';
import { STREAM_META_METADATA_KEYS } from '../shared/metadata-contract';

interface MatrixCase {
  id: string;
  should_pass: boolean;
  payload: Record<string, unknown>;
}

const root = resolve(__dirname, '..');
const matrixPath = resolve(root, 'tests/fixtures/stream_meta_validation_matrix.json');
const keysPath = resolve(root, 'config/stream_meta_metadata_keys.json');

const matrix = JSON.parse(readFileSync(matrixPath, 'utf-8')) as { cases: MatrixCase[] };
const keys = JSON.parse(readFileSync(keysPath, 'utf-8')) as string[];

assert.deepStrictEqual([...STREAM_META_METADATA_KEYS], keys, 'STREAM_META_METADATA_KEYS drift');

let failed = 0;
for (const testCase of matrix.cases) {
  let passed = false;
  try {
    parseStreamMeta(testCase.payload);
    passed = true;
  } catch {
    passed = false;
  }
  if (passed !== testCase.should_pass) {
    console.error(
      `FAIL ${testCase.id}: TS ${passed ? 'pass' : 'fail'}, expected ${testCase.should_pass ? 'pass' : 'fail'}`,
    );
    failed += 1;
  }
}

if (failed > 0) {
  process.exit(1);
}
console.log(`OK ${matrix.cases.length} stream meta validation parity case(s)`);
