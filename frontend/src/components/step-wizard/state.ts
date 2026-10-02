export type WizardState = { active: number; completed: number[]; confirmed: boolean };
export const initialWizardState = (): WizardState => ({ active: 0, completed: [], confirmed: false });

export function advance(state: WizardState, count: number): WizardState {
  const completed = [...new Set([...state.completed, state.active])];
  return { active: Math.min(state.active + 1, count - 1), completed,
    confirmed: completed.length === count };
}

export function visit(state: WizardState, target: number): WizardState {
  if (target < 0 || (target !== state.active && !state.completed.includes(target))) return state;
  return { ...state, active: target };
}

// An edit requires the current step and everything after it to be reviewed again.
export function invalidate(state: WizardState): WizardState {
  return { ...state, completed: state.completed.filter(index => index < state.active), confirmed: false };
}
