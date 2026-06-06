import {
  parseTrustExplainabilityFlag,
  readTrustExplainabilityFromEnv,
} from '@seal/trust-explainability';

/** Demo fixtures simulate trust-enabled API responses unless explicitly disabled. */
export function isDemoTrustExplainabilityEnabled(): boolean {
  const explicitDemoFlag = parseTrustExplainabilityFlag(
    process.env.NEXT_PUBLIC_SEAL_DEMO_TRUST_EXPLAINABILITY,
  );
  if (explicitDemoFlag !== undefined) {
    return explicitDemoFlag;
  }
  return readTrustExplainabilityFromEnv();
}
