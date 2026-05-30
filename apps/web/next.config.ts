import path from 'node:path';
import type { NextConfig } from 'next';

const repoRoot = path.resolve(__dirname, '../..');

const nextConfig: NextConfig = {
  transpilePackages: ['intelligence-sdk'],
  outputFileTracingRoot: repoRoot,
};

export default nextConfig;
