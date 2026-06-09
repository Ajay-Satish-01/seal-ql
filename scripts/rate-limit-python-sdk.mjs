#!/usr/bin/env node
/**
 * Generate sdks/python/seal/rate_limit.py from packages/core/seal_core/llm/rate_limit.py.
 * The seal:python-sdk-markers-read block in _read_markers_json() is the only SDK-specific section.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const READ_BEGIN = '# seal:python-sdk-markers-read-begin';
const READ_END = '# seal:python-sdk-markers-read-end';

const CORE_DOCSTRING =
  '"""Shared rate-limit detection (markers sourced from config/rate_limit_markers.json)."""';
const SDK_DOCSTRING =
  '"""Rate-limit helpers (generated from seal_core.llm.rate_limit — do not edit)."""';

const CORE_READ = `    # seal:python-sdk-markers-read-begin
    from pathlib import Path

    return Path(__file__).with_name("rate_limit_markers.json").read_text(encoding="utf-8")
    # seal:python-sdk-markers-read-end`;

const SDK_READ = `    # seal:python-sdk-markers-read-begin
    from importlib.resources import files

    return files("seal").joinpath("rate_limit_markers.json").read_text(encoding="utf-8")
    # seal:python-sdk-markers-read-end`;

export function replaceMarkerBlock(source, begin, end, inner) {
  const start = source.indexOf(begin);
  if (start < 0) {
    throw new Error(`Missing marker: ${begin}`);
  }
  const innerStart = start + begin.length;
  const stop = source.indexOf(end, innerStart);
  if (stop < 0) {
    throw new Error(`Missing marker: ${end}`);
  }
  return `${source.slice(0, start)}${inner}${source.slice(stop + end.length)}`;
}

export function generateSdkRateLimitModule(coreSource) {
  if (!coreSource.includes(CORE_DOCSTRING)) {
    throw new Error('Core rate_limit.py must include the expected module docstring');
  }
  if (!coreSource.includes(CORE_READ)) {
    throw new Error(
      'Core rate_limit.py _read_markers_json() must match the expected marker block',
    );
  }
  return coreSource.replace(CORE_DOCSTRING, SDK_DOCSTRING).replace(CORE_READ, SDK_READ);
}

export function paths(repoRoot = root) {
  return {
    core: resolve(repoRoot, 'packages/core/seal_core/llm/rate_limit.py'),
    sdk: resolve(repoRoot, 'sdks/python/seal/rate_limit.py'),
  };
}

export function readExpectedSdkModule(repoRoot = root) {
  const { core } = paths(repoRoot);
  const coreSource = readFileSync(core, 'utf8');
  return generateSdkRateLimitModule(coreSource);
}

export function writeSdkRateLimitModule(repoRoot = root) {
  const { sdk } = paths(repoRoot);
  writeFileSync(sdk, readExpectedSdkModule(repoRoot), 'utf8');
}

export function checkSdkRateLimitModule(repoRoot = root) {
  const { sdk } = paths(repoRoot);
  const expected = readExpectedSdkModule(repoRoot);
  let actual;
  try {
    actual = readFileSync(sdk, 'utf8');
  } catch {
    return { ok: false, reason: `Missing ${sdk}` };
  }
  if (actual !== expected) {
    return { ok: false, reason: `Out of sync: ${sdk}` };
  }
  return { ok: true };
}

function main() {
  const args = new Set(process.argv.slice(2));
  if (args.has('--write')) {
    writeSdkRateLimitModule();
    return;
  }
  if (args.has('--check')) {
    const result = checkSdkRateLimitModule();
    if (!result.ok) {
      console.error(result.reason);
      console.error('Run: node scripts/sync-sdk-meta-vendor.mjs');
      process.exit(1);
    }
    console.log('✅ sdks/python/seal/rate_limit.py matches core markers');
    return;
  }
  console.error('Usage: node scripts/rate-limit-python-sdk.mjs --write|--check');
  process.exit(1);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  main();
}
