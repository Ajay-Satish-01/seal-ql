/**
 * Verifies chatResponseToStreamMeta matches tests/fixtures/chat_flatten_golden.json.
 * Run: pnpm exec tsx scripts/verify_chat_flatten_contract.ts (from repo root)
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { chatResponseToStreamMeta } from '../shared/metadata-contract';

interface GoldenCase {
  id: string;
  response: Parameters<typeof chatResponseToStreamMeta>[0];
  expected_flat: Record<string, unknown>;
}

const goldenPath = resolve(__dirname, '../tests/fixtures/chat_flatten_golden.json');
const data = JSON.parse(readFileSync(goldenPath, 'utf-8')) as { cases: GoldenCase[] };

let failed = 0;
for (const testCase of data.cases) {
  const flat = chatResponseToStreamMeta(testCase.response) as Record<string, unknown>;
  const expected = testCase.expected_flat;
  try {
    assert.deepStrictEqual(flat, expected);
  } catch {
    console.error(
      `FAIL ${testCase.id}\n  got:      ${JSON.stringify(flat)}\n  expected: ${JSON.stringify(expected)}`,
    );
    failed += 1;
  }
}

if (failed > 0) {
  process.exit(1);
}
console.log(`OK ${data.cases.length} chat flatten contract case(s)`);
