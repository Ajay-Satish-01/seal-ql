/**
 * User-facing deployment copy derived from SITE — keep docs pages DRY.
 */
import { SITE } from '@/lib/constants';

export function isPackagesPublished(): boolean {
  return SITE.packagesPublished;
}

export function siteTaglineSuffix(): string {
  return SITE.packagesPublished ? 'Image-first' : 'Build from source';
}

export function siteHeroBadgeLabel(): string {
  return `${SITE.name} · Open source · ${siteTaglineSuffix()}`;
}

export function deploymentDockerSummary(): string {
  if (SITE.packagesPublished) {
    return `${SITE.dockerImage} on Docker Hub; compose with Postgres and optional Ollama`;
  }
  return `Clone the repo and run make up (Docker Hub publish in progress; planned image ${SITE.dockerImage})`;
}

export function deploymentSdkSummary(): string {
  if (SITE.packagesPublished) {
    return `pip install ${SITE.pypiPackage} / npm install ${SITE.npmPackage} from your app server`;
  }
  return 'PyPI/npm publish in progress — install from sdks/python and sdks/typescript in the monorepo';
}

export function composeYamlNote(): string {
  if (SITE.packagesPublished) {
    return 'Production compose using a published image (image:, not build:).';
  }
  return `Reference compose for after Docker Hub publish (uses image: ${SITE.dockerImage}). Until then, use the git quick start above with make up.`;
}
