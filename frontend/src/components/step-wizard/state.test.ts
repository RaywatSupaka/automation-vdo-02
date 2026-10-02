import { describe, expect, it } from 'vitest';
import { advance, initialWizardState, invalidate, visit } from './state';

describe('wizard navigation', () => {
  it('does not allow jumping to an unseen step', () => {
    const initial = initialWizardState();
    expect(visit(initial, 4)).toEqual(initial);
    expect(visit(initial, -1)).toEqual(initial);
  });
  it('invalidates the edited step and later reviews without erasing earlier completion', () => {
    let state = initialWizardState();
    for (let i = 0; i < 5; i++) state = advance(state, 5);
    expect(state.confirmed).toBe(true);
    state = invalidate(visit(state, 1));
    expect(state).toEqual({ active: 1, completed: [0], confirmed: false });
    expect(visit(state, 4)).toEqual(state);
    expect(advance(state, 5).active).toBe(2);
  });
  it('reviewing a completed step does not double-count progress', () => {
    let state = initialWizardState();
    for (let i = 0; i < 5; i++) state = advance(state, 5);
    state = advance(visit(state, 0), 5);
    expect(state.completed).toHaveLength(5);
    expect(state.active).toBe(1);
  });
});
