/**
 * Guards doc install / quick-start snippets against packagesPublished drift.
 * Run: pnpm run verify:doc-snippets (from apps/docs)
 */
import assert from 'node:assert/strict';
import { SITE } from '../src/lib/constants';
import {
  cloneFromSourceStackSnippet,
  githubBlobUrl,
  githubRawUrl,
  githubRepoName,
  quickstartIntegratorDockerSnippet,
  selfHostingQuickStartSnippet,
  sdkInstallSnippet,
} from '../src/lib/doc-snippets';

const branchRe = new RegExp(SITE.githubDefaultBranch);

assert.match(githubRawUrl('apps/docs/public/compose/docker-compose.example.yml'), branchRe);
assert.match(githubBlobUrl('DEPLOYMENT.md'), branchRe);
assert.match(githubBlobUrl('DEPLOYMENT.md'), /DEPLOYMENT\.md$/);
assert.equal(githubRepoName(), 'seal');

const selfHostUnpublished = selfHostingQuickStartSnippet(false);
const quickstartUnpublished = quickstartIntegratorDockerSnippet(false);
const sdkUnpublished = sdkInstallSnippet(false);
const cloneSnippet = cloneFromSourceStackSnippet();

assert.equal(selfHostUnpublished, cloneSnippet);
assert.equal(quickstartUnpublished, cloneFromSourceStackSnippet({ silentCurl: true }));

assert.doesNotMatch(selfHostUnpublished, /docker pull/);
assert.match(selfHostUnpublished, /git clone/);
assert.match(selfHostUnpublished, /make up/);
assert.match(selfHostUnpublished, /SEAL_DEV_MODE/);

assert.doesNotMatch(quickstartUnpublished, /docker pull/);
assert.match(quickstartUnpublished, /make seed/);

assert.match(sdkUnpublished, /uv sync/);
assert.doesNotMatch(sdkUnpublished, /^pip install seal$/m);

const selfHostPublished = selfHostingQuickStartSnippet(true);
const quickstartPublished = quickstartIntegratorDockerSnippet(true);

assert.match(selfHostPublished, /docker pull/);
assert.match(quickstartPublished, /docker-compose.example.yml/);
assert.match(sdkInstallSnippet(true), /pip install seal/);

console.log('verify-doc-snippets: ok');
