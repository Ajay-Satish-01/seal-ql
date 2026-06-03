export const SITE = {
  name: 'Seal',
  github: 'https://github.com/Ajay-Satish-01/seal',
  /** Default branch for githubRawUrl() asset links */
  githubDefaultBranch: 'main',
  /**
   * Set to true after the first public release on Docker Hub, PyPI, and npm.
   * While false, docs show planned package names and "in progress" messaging.
   */
  packagesPublished: false,
  /** Planned Docker image (compose examples and self-hosting docs) */
  dockerImage: 'seal/api:latest',
  /** Registry URLs — use only when packagesPublished is true */
  dockerHub: 'https://hub.docker.com/r/seal/api',
  pypi: 'https://pypi.org/project/seal/',
  npm: 'https://www.npmjs.com/package/seal',
  pypiPackage: 'seal',
  npmPackage: 'seal',
  defaultBaseUrl: 'http://localhost:8000',
} as const;

/** Shown in docs when packagesPublished is false */
export const PACKAGES_IN_PROGRESS_NOTE =
  'Docker Hub (`seal/api`), PyPI (`seal`), and npm (`seal`) releases are in progress. Use a git checkout and `make up` / `make docker-build`, or install SDKs from `sdks/` in the monorepo until publish.';
