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

export class ServerError extends SealError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = 'ServerError';
  }
}
