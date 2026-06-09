import { describe, expect, it } from 'vitest';
import {
  formatApiError,
  formatClientError,
  isRateLimitSignal,
  RATE_LIMIT_USER_MESSAGE,
} from '../../../shared/api-error.js';

describe('isRateLimitSignal', () => {
  it('detects rate limit keywords in message text', () => {
    expect(isRateLimitSignal(502, 'Groq RateLimitError: rate limit exceeded')).toBe(true);
    expect(isRateLimitSignal(200, 'Rate limited by provider')).toBe(true);
    expect(isRateLimitSignal(200, 'tokens per minute limit hit')).toBe(true);
  });

  it('treats empty-body HTTP 503 as rate limiting', () => {
    expect(isRateLimitSignal(503, '')).toBe(true);
  });

  it('does not treat unrelated HTTP 503 bodies as rate limiting', () => {
    expect(isRateLimitSignal(503, 'Service temporarily unavailable')).toBe(false);
  });
});

describe('formatApiError', () => {
  it('normalizes LLM rate limit JSON detail', () => {
    const body = JSON.stringify({
      detail:
        'Rate limited. The LLM provider is throttling requests — wait a few seconds and try again.',
    });
    expect(formatApiError(503, body)).toBe(RATE_LIMIT_USER_MESSAGE);
  });
});

describe('formatClientError', () => {
  it('maps Error messages with rate limit markers', () => {
    expect(formatClientError(new Error('rate_limit exceeded'), 'fallback')).toBe(
      RATE_LIMIT_USER_MESSAGE,
    );
  });
});
