import path from 'node:path';
import type { NextConfig } from 'next';

/** Monorepo root — required for production file tracing and dev Turbopack resolution of `link:../../sdks/typescript`. */
const repoRoot = path.resolve(__dirname, '../..');
/** Absolute path used only by the webpack dev fallback (`pnpm dev:webpack`). */
const sealSdkRoot = path.join(repoRoot, 'sdks/typescript');
const isProd = process.env.NODE_ENV === 'production';

const nextConfig: NextConfig = {
  // Compile the linked TypeScript SDK (React VegaChart, SSE helpers) with the docs app.
  transpilePackages: ['seal'],
  ...(isProd
    ? {
        /**
         * Production builds: trace dependencies from the monorepo root so Next can bundle
         * `node_modules/seal` → `sdks/typescript` for deployable output.
         * Expect: `pnpm build` in apps/docs succeeds; `/demo` works in `next start`.
         */
        outputFileTracingRoot: repoRoot,
      }
    : {
        /**
         * Development (Turbopack): project root must include the linked SDK path.
         * Expect: `pnpm dev` serves `/demo` without "Can't resolve 'seal'".
         * Do NOT set outputFileTracingRoot here — it expands the watcher to the whole repo
         * and can leave dev stuck on "Compiling…".
         */
        turbopack: {
          root: repoRoot,
        },
        /**
         * Webpack dev (`pnpm dev:webpack`): explicit alias when Turbopack is disabled.
         */
        webpack: (config) => {
          config.resolve.alias = {
            ...config.resolve.alias,
            seal: sealSdkRoot,
          };
          return config;
        },
      }),
};

export default nextConfig;
