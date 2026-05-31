import { toast } from 'sonner';

/** Show a success toast after a completed API call. */
export function notifySuccess(message: string): void {
  toast.success(message);
}

/** Show an error toast (API or client failure). */
export function notifyError(message: string): void {
  toast.error(message);
}

/** Map thrown values (usually `Error` from seal-api) to an error toast. */
export function notifyErrorFrom(error: unknown, fallback: string): void {
  notifyError(error instanceof Error ? error.message : fallback);
}

/** Neutral toast for non-error feedback (e.g. nothing to save). */
export function notifyInfo(message: string): void {
  toast.info(message);
}
