import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { ArrowLeft, ArrowRight, Check, CheckCircle2, Play } from 'lucide-react';
import { advance, initialWizardState, invalidate, visit } from './state';
import './step-wizard.css';

export type WizardStep = {
  id: string;
  label: string;
  title: string;
  description: string;
  render: (markChanged: () => void) => ReactNode;
  validate?: () => string | null;
};

/** Replaces "confirm" on the last step: after every step validates, the host runs its own action. */
export type FinishAction = { label: string; disabled?: boolean; run: () => void };

type Props = { steps: WizardStep[]; finishLabel: string; completionMessage: string; footerNote: string;
  initialStep?: number; onStepChange?: (step: number) => void; finishAction?: FinishAction };

/** Presentation/navigation only. Hosts own data, validation and persistence. Keep step IDs stable. */
export function StepWizard({ steps, finishLabel, completionMessage, footerNote, initialStep = 0, onStepChange, finishAction }: Props) {
  const [state, setState] = useState(() => {
    let active = Math.min(initialStep, steps.length - 1);
    for (let i = 0; i < active; i++) if (steps[i].validate?.()) { active = i; break; }
    return { ...initialWizardState(), active, completed: Array.from({ length: active }, (_, i) => i) };
  });
  const [error, setError] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  const alert = useRef<HTMLDivElement>(null);
  const body = useRef<HTMLDivElement>(null);
  const previous = useRef(state.active);
  const prefix = useId();
  const step = steps[state.active];

  useEffect(() => {
    if (previous.current !== state.active) {
      body.current?.scrollTo({ top: 0 });
      heading.current?.focus();
      previous.current = state.active;
    }
  }, [state.active]);
  useEffect(() => { if (error) alert.current?.focus(); }, [error]);
  useEffect(() => { onStepChange?.(state.active); }, [state.active, onStepChange]);

  if (!step) return null;
  function markChanged() { setState(invalidate); setError(''); }
  function go(target: number) { setState(current => visit(current, target)); setError(''); }
  function next() {
    // Check all earlier steps too before confirming; completion is never a validation bypass.
    for (let index = 0; index <= state.active; index++) {
      const problem = steps[index].validate?.();
      if (problem) {
        setState(current => ({ ...current, active: index,
          completed: current.completed.filter(value => value < index), confirmed: false }));
        setError(problem); return;
      }
    }
    setError('');
    if (finishAction && state.active === steps.length - 1) { finishAction.run(); return; }
    setState(current => advance(current, steps.length));
  }
  const last = state.active === steps.length - 1;
  const primaryLabel = !last ? 'ถัดไป' : finishAction ? finishAction.label : state.confirmed ? 'ตรวจรายละเอียดแล้ว' : finishLabel;
  const primaryDisabled = last && (finishAction ? Boolean(finishAction.disabled) : state.confirmed);

  return <section className="step-wizard" aria-label="แบบฟอร์มทีละขั้น">
    <header className="wizard-progress">
      <span className="wizard-sr-only" role="progressbar" aria-label="ขั้นตอนที่ผ่านแล้ว"
        aria-valuemin={0} aria-valuemax={steps.length} aria-valuenow={state.completed.length}/>
      <ol className="wizard-steps" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}>
        {steps.map((item, index) => {
          const done = state.completed.includes(index);
          const current = index === state.active;
          const status = current ? 'ขั้นปัจจุบัน' : done ? 'ผ่านแล้ว' : 'ยังไม่ถึง';
          return <li key={item.id} className={done ? 'is-done' : ''}>
            {index < steps.length - 1 && <span className="wizard-connector" aria-hidden="true"><span/></span>}
            <button type="button" aria-current={current ? 'step' : undefined}
            aria-label={`${index + 1}. ${item.label} · ${status}`} disabled={!current && !done}
            className={`wizard-step ${current ? 'is-current' : ''} ${done ? 'is-done' : ''}`} onClick={() => go(index)}>
            <span className="wizard-step-number">{done ? <Check size={15}/> : index + 1}</span>
            <span className="wizard-step-copy"><strong>{item.label}</strong></span>
          </button></li>;
        })}
      </ol>
    </header>
    <div className="wizard-body" ref={body}>
      <div className="wizard-page" key={step.id}>
        <div className="wizard-step-heading"><p className="eyebrow">STEP {String(state.active + 1).padStart(2, '0')}</p>
          <h2 id={`${prefix}-heading`} tabIndex={-1} ref={heading}>{step.title}</h2><p>{step.description}</p></div>
        {error && <div className="wizard-error" role="alert" tabIndex={-1} ref={alert}>{error}</div>}
        {state.confirmed && state.active === steps.length - 1 && <div className="wizard-confirmation" role="status"><CheckCircle2 size={20}/>{completionMessage}</div>}
        <div role="group" aria-labelledby={`${prefix}-heading`}>{step.render(markChanged)}</div>
      </div>
    </div>
    <footer className="wizard-footer"><p>{footerNote}</p><div className="wizard-actions">
      <button type="button" disabled={state.active === 0} onClick={() => go(state.active - 1)}><ArrowLeft size={17}/>ย้อนกลับ</button>
      <button type="button" className="primary" disabled={primaryDisabled} onClick={next}>
        {primaryLabel}
        {!last ? <ArrowRight size={17}/> : finishAction ? <Play size={17}/> : <Check size={17}/>}
      </button>
    </div></footer>
  </section>;
}
