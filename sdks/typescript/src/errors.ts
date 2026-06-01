/**
 * Custom error classes for the Seal SDK.
 */

export class SealError extends Error {
  public readonly statusCode?: number;

  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = 'SealError';
    this.statusCode = statusCode;
  }
}

export class SealConnectionError extends SealError {
  constructor(message: string) {
    super(message);
    this.name = 'SealConnectionError';
  }
}

/** @deprecated Use {@link SealConnectionError} */
export class ConnectionError extends SealConnectionError {
  constructor(message: string) {
    super(message);
    this.name = 'ConnectionError';
  }
}

export class QueryError extends SealError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = 'QueryError';
  }
}

/** Guardrails rejected the query (HTTP 400, structured detail). */
export class QueryOutOfScopeError extends QueryError {
  readonly reason: string;
  readonly suggestedQueries: readonly string[];

  constructor(
    message: string,
    statusCode: number,
    reason: string,
    suggestedQueries: readonly string[],
  ) {
    super(message, statusCode);
    this.name = 'QueryOutOfScopeError';
    this.reason = reason;
    this.suggestedQueries = suggestedQueries;
  }
}

export class ServerError extends SealError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = 'ServerError';
  }
}
