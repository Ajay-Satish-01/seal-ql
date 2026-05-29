import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Tells Turbopack where the actual workspace root is, avoiding traversal of the user's home directory
  experimental: {},
  // @ts-ignore - newer next.js setting
  turbopack: {
    root: '../../',
  },
};

export default nextConfig;
