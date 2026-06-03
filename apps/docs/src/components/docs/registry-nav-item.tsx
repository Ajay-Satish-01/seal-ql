import Link from 'next/link';
import { PACKAGES_IN_PROGRESS_NOTE, SITE } from '@/lib/constants';

export function RegistryNavItem({ label, href }: { label: string; href: string }) {
  if (SITE.packagesPublished) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="hover:text-primary transition-colors"
      >
        {label}
      </a>
    );
  }

  return (
    <Link
      href="/docs/contributing"
      className="text-muted-foreground/70 hover:text-primary transition-colors"
      title={PACKAGES_IN_PROGRESS_NOTE}
    >
      {label} (soon)
    </Link>
  );
}
