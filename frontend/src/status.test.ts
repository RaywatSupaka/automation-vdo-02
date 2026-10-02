import { describe, expect, it } from 'vitest';
import { actions } from './status';

describe('recovery actions', () => {
  it('never offers replay of an uncertain send', () => {
    expect(actions('needs_review', 'unknown')).toEqual({ resume: false, reconcile: true, cancel: true });
    expect(actions('cancelled', 'dispatching').resume).toBe(false);
  });
  it('allows storage recovery with the completed receipt', () => {
    expect(actions('failed', 'completed').resume).toBe(true);
    expect(actions('completed', 'completed').cancel).toBe(false);
  });
});
