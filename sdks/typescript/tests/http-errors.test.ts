import { describe, expect, it } from 'vitest';
import { raiseForResponse } from '../src/http-errors.js';
import { QueryError, ServerError } from '../src/errors.js';
import { RATE_LIMIT_USER_MESSAGE } from '../src/vendor/api-error.js';

describe('raiseForResponse', () => {
  it('formats FastAPI 422 validation detail arrays', () => {
    try {
      raiseForResponse(422, {
        detail: [
          { type: 'missing', loc: ['body', 'query'], msg: 'Field required' },
          { type: 'string_too_long', loc: ['body', 'query'], msg: 'Too long' },
        ],
      });
      expect.fail('expected QueryError');
    } catch (err) {
      expect(err).toBeInstanceOf(QueryError);
      expect((err as QueryError).message).toContain('Field required; Too long');
    }
  });

  it('normalizes HTTP 503 rate-limit detail to RATE_LIMIT_USER_MESSAGE', () => {
    try {
      raiseForResponse(503, { detail: RATE_LIMIT_USER_MESSAGE });
      expect.fail('expected ServerError');
    } catch (err) {
      expect(err).toBeInstanceOf(ServerError);
      expect((err as ServerError).message).toContain('Rate limited');
    }
  });
});
