import { cn } from '@/lib/utils';

type SealLogoProps = {
  className?: string;
  size?: number;
};

/** Stylized harbor seal mark — works in light and dark themes. */
export function SealLogo({ className, size = 32 }: SealLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('shrink-0', className)}
      aria-hidden
    >
      <ellipse cx="24" cy="40" rx="20" ry="4" className="fill-teal-500/25 dark:fill-teal-400/20" />
      <path
        d="M8 28c2-10 8-16 16-16s14 6 16 16c-2 6-8 10-16 10S10 34 8 28z"
        className="fill-teal-700 dark:fill-teal-500"
      />
      <ellipse cx="24" cy="24" rx="11" ry="10" className="fill-teal-800 dark:fill-teal-400" />
      <circle cx="30" cy="20" r="5.5" className="fill-teal-800 dark:fill-teal-400" />
      <circle cx="31.5" cy="19" r="1.2" className="fill-amber-950 dark:fill-teal-950" />
      <path
        d="M34 21.5c2 1 3.5 2.5 4 4"
        stroke="currentColor"
        strokeWidth="0.8"
        strokeLinecap="round"
        className="text-teal-900/40 dark:text-teal-100/50"
      />
      <path
        d="M12 26c-2 2-3 4-2.5 6"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        className="text-teal-900/50 dark:text-teal-100/60"
      />
      <path
        d="M36 26c2 2 3 4 2.5 6"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        className="text-teal-900/50 dark:text-teal-100/60"
      />
      <path
        d="M18 32c1.5 1 3 1.5 6 1.5s4.5-.5 6-1.5"
        stroke="currentColor"
        strokeWidth="1"
        strokeLinecap="round"
        className="text-amber-800/60 dark:text-amber-200/50"
      />
    </svg>
  );
}
