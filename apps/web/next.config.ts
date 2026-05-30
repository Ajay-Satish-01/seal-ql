import path from 'node:path';
import type { NextConfig } from 'next';

const repoRoot = path.resolve(__dirname, '../..');

const nextConfig: NextConfig = {
  transpilePackages: ['seal'],
  outputFileTracingRoot: repoRoot,
};

export default nextConfig;
