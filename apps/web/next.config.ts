import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  transpilePackages: ['intelligence-sdk'],
  // Tells Turbopack where the actual workspace root is, avoiding traversal of the user's home directory
  experimental: {},
  turbopack: {
    root: '../../',
  },
};

export default nextConfig;
