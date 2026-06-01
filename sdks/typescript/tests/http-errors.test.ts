import { describe, expect, it } from 'vitest';
import { raiseForResponse } from '../src/http-errors.js';
import { QueryError } from '../src/errors.js';

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
});
