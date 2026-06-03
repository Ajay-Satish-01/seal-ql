import Link from 'next/link';
import { SealLogo } from './seal-logo';
import { RegistryNavItem } from '@/components/docs/registry-nav-item';
import { SITE } from '@/lib/constants';
import { getApiVersion } from '@/lib/openapi';
import { siteTaglineSuffix } from '@/lib/site-display';

export function Footer() {
  const version = getApiVersion();

  return (
    <footer className="border-border/40 bg-card/30 mt-auto border-t">
      <div className="container mx-auto flex max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-col gap-2">
          <Link href="/" className="flex items-center gap-2">
            <SealLogo size={28} />
            <span className="font-heading text-sm font-semibold">{SITE.name}</span>
          </Link>
          <span className="text-muted-foreground text-xs">
            API v{version} · Open source · {siteTaglineSuffix()}
          </span>
        </div>
        <nav className="text-muted-foreground flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
          <Link href="/demo" className="hover:text-primary transition-colors">
            Demo
          </Link>
          <Link href="/docs/self-hosting" className="hover:text-primary transition-colors">
            Docker
          </Link>
          <Link href="/docs/authentication" className="hover:text-primary transition-colors">
            Authentication
          </Link>
          <RegistryNavItem label="PyPI" href={SITE.pypi} />
          <RegistryNavItem label="npm" href={SITE.npm} />
          <RegistryNavItem label="Docker Hub" href={SITE.dockerHub} />
          <a
            href={SITE.github}
            target="_blank"
            rel="noreferrer"
            className="hover:text-primary transition-colors"
          >
            GitHub
          </a>
          <Link href="/docs/contributing" className="hover:text-primary transition-colors">
            Develop from source
          </Link>
        </nav>
      </div>
    </footer>
  );
}
