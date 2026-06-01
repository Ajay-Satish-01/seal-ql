import Link from 'next/link';
import { cn } from '@/lib/utils';

interface DocLinkProps {
  href: string;
  children: React.ReactNode;
  className?: string;
}

/** Consistent in-doc navigation styling. */
export function DocLink({ href, children, className }: DocLinkProps) {
  return (
    <Link href={href} className={cn('text-primary underline-offset-4 hover:underline', className)}>
      {children}
    </Link>
  );
}
