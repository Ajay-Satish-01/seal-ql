/**
 * Custom error classes for the Intelligence Connector SDK.
 */

export class IntelligenceConnectorError extends Error {
  public readonly statusCode?: number;

  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = 'IntelligenceConnectorError';
    this.statusCode = statusCode;
  }
}

export class ConnectionError extends IntelligenceConnectorError {
  constructor(message: string) {
    super(message);
    this.name = 'ConnectionError';
  }
}

export class QueryError extends IntelligenceConnectorError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = 'QueryError';
  }
}

export class ServerError extends IntelligenceConnectorError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = 'ServerError';
  }
}
