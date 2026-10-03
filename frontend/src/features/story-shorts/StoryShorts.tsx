import { useRef, useState } from 'react';
import { useDraft } from './useDraft';
import { StepWizard, type WizardStep } from '../../components/step-wizard/StepWizard';
import { batchTopics, draftWarnings, validateStoryStep } from './draft';
import { fieldGroups, visible, type DraftValue } from './fields';
import { transport, type DraftIssue, type SaveState } from './persistence';
import { fieldDisplay, RequiredMark, StoryFields } from './StoryFields';
import { startStoryJob, type StartResult, type StoryJob } from './story-job';
import { QueuePanel } from '../queue/QueuePanel';
import './story-shorts.css';

const stepInfo = [
  ['idea', 'เรื่องที่จะเล่า', 'เรื่องราวของคุณ เริ่มจากอะไร?', 'แยกหัวข้อออกจากรายละเอียด เลือกรูปหลัก และเตรียมได้ทั้งคลิปเดียวหรือหลายคลิป'],
  ['style', 'โทนและสไตล์', 'อยากให้เรื่องนี้รู้สึกแบบไหน?', 'เลือกผู้พูด โครงเรื่อง โทน การเปิด–จบ และแนวภาพ'],
  ['scenes', 'ภาพและวิดีโอ', 'จัดฉากและรายละเอียดวิดีโอ', 'ตั้งผู้ให้บริการ จำนวนฉาก ปก อินโทร โลโก้ และเอฟเฟกต์ตามที่ต้องการ'],
  ['audio', 'เสียงและซับ', 'ให้เรื่องเล่ามีเสียงของตัวเอง', 'เสียงหลัก คำบรรยาย เพลง เอฟเฟกต์ และการทำงานอัตโนมัติ'],
];
const examples: Record<string, string> = {
  narrator: 'เล่าด้วยภาษาง่าย เปิดด้วยเหตุการณ์ชวนสงสัย แล้วค่อยเฉลยเหตุผลให้จบอย่างอบอุ่น',
  solo: 'ให้ตัวเอกเล่าเหตุการณ์ด้วยคำพูดของตัวเอง มีจังหวะลังเลก่อนตัดสินใจ โดยไม่มีผู้บรรยาย',
  dialogue: 'ให้ตัวละครสองคนพูดคุยสั้น ๆ เริ่มจากความเข้าใจผิด แล้วคลี่คลายผ่านบทสนทนา',
  visual: 'เล่าด้วยสีหน้า การกระทำ และรายละเอียดในภาพ โดยไม่ใช้บทพูด',
};

const issueText: Record<string, string> = {
  FIELD_REQUIRED: 'ยังไม่ได้ระบุ',
  VALUE_OUT_OF_RANGE: 'ค่าเกินช่วงที่รองรับ',
  OPTION_INVALID: 'ตัวเลือกไม่ตรงกับที่มี',
  DRAFT_ASSET_MISSING: 'ไฟล์ที่บันทึกไว้หาย กรุณาเลือกไฟล์ใหม่แทน',
};
const labels = new Map(fieldGroups.flatMap(group => group.fields.map(field => [field.id, field.label] as const)));
/** Short Thai lines from the server's issues, one per code; the draft is saved either way. */
export function issueSummary(issues: readonly DraftIssue[] = []): string[] {
  const byCode = new Map<string, string[]>();
  for (const { field, code } of issues) {
    const names = byCode.get(code) || [], label = labels.get(field) || field;
    if (!names.includes(label)) names.push(label);
    byCode.set(code, names);
  }
  return [...byCode].map(([code, names]) => `${issueText[code] || 'ต้องตรวจอีกครั้ง'}: ${names.slice(0, 3).join(', ')}${names.length > 3 ? ` และอีก ${names.length - 3} รายการ` : ''}`);
}
/** The server judged the last acknowledged save, so outside 'saved' its lines are labelled as possibly out of date. */
export function issueNotice(state: SaveState, issues?: readonly DraftIssue[]): { lines: string[]; stale: string } {
  const lines = issueSummary(issues);
  return { lines, stale: lines.length > 0 && state !== 'saved' ? 'ผลตรวจจากการบันทึกครั้งล่าสุด ยังไม่รวมการแก้ไขที่ยังไม่บันทึก' : '' };
}

const startErrorText: Record<string, string> = {
  DRAFT_NOT_SAVED: 'แบบร่างยังไม่บันทึก กรุณารอสถานะ “บันทึกแล้ว” แล้วลองใหม่',
  DRAFT_REVISION_CONFLICT: 'แบบร่างเปลี่ยนระหว่างเริ่มงาน กรุณาบันทึกแล้วลองใหม่ หากยังพบปัญหาให้โหลดแบบร่างล่าสุด',
  STORY_DRAFT_INVALID: 'แบบร่างยังไม่ถูกต้อง กรุณาตรวจรายการช่องที่ต้องแก้',
  STORY_CAPABILITY_UNAVAILABLE: 'รอบนี้รองรับการทำงานจำลองแบบคลิปเดียวเท่านั้น',
  DRAFT_ASSET_MISSING: 'ไฟล์แนบหาย กรุณาเลือกไฟล์ใหม่',
  DRAFT_ASSET_INVALID: 'ไฟล์แนบไม่ถูกต้อง กรุณาเลือกไฟล์ใหม่',
  PERMISSION_DENIED: 'ไม่มีสิทธิ์เริ่มงานจำลอง',
  CONNECTION_FAILED: 'เชื่อมต่อไม่สำเร็จ กรุณาลองใหม่',
};

type Queued = { jobId: string; title: string; opened: boolean };

export function StoryShorts({ canStart = false, canCommand = false, canQueue = false }:
  { canStart?: boolean; canCommand?: boolean; canQueue?: boolean }) {
  const persistence = useDraft();
  const [starting, setStarting] = useState(false);
  const [startResult, setStartResult] = useState<StartResult | null>(null);
  const [queued, setQueued] = useState<Queued | null>(null);
  const startKey = useRef<{ draft: string; value: string } | null>(null);
  const inFlight = useRef(false);
  /** The job is queued; continue on a new draft (settings kept, story content reset) at step 1. */
  async function openNext(job: StoryJob, title: string) {
    const opened = await persistence.next(`successor-${job.id}`);
    setQueued({ jobId: job.id, title, opened });
    if (opened) setStartResult(null);
  }
  async function start() {
    if (inFlight.current) return;
    inFlight.current = true; setStarting(true); setStartResult(null);
    const title = String(persistence.draft.topic || '').trim();
    try {
      const result = await startStoryJob({ flush: persistence.flush, identity: persistence.identity, send: transport(),
        key: () => {
          // One key per draft revision: retrying the same revision returns the same job, never a duplicate.
          const { id, revision } = persistence.identity(), draftKey = `${id}:${revision}`;
          if (startKey.current?.draft !== draftKey) startKey.current = { draft: draftKey, value: crypto.randomUUID() };
          return startKey.current.value;
        } });
      setStartResult(result);
      if (result.ok) await openNext(result.job, title);
    } finally { inFlight.current = false; setStarting(false); }
  }
  const draft = persistence.draft;
  // The footer's last button starts the job directly; users can still step back to review.
  const startAction = { label: starting ? 'กำลังเริ่มงานจำลอง…' : 'เริ่มงานจำลอง',
    disabled: starting || issueSummary(persistence.issues).length > 0, run: () => { void start(); } };
  const warnings = draftWarnings(draft);
  const serverIssues = issueNotice(persistence.state, persistence.issues);
  const steps: WizardStep[] = stepInfo.map(([id, label, title, description], index) => ({
    id, label, title, description, validate: () => validateStoryStep(draft, index),
    render: dirty => {
      function update(key: string, value: DraftValue) { persistence.update({ ...draft, [key]: value }); dirty(); }
      const topics = batchTopics(draft);
      return <div className="story-all-details">
        <div className="story-form-note"><span><RequiredMark/> ช่องที่ต้องระบุ</span><span>เลือกค่าเพื่อเตรียมแบบร่าง · ยังไม่เชื่อมบริการหรือสร้างสื่อ</span></div>
        {index === 0 && draft.creationMode === 'batch' && <p className="story-group-help">{topics.length} / 10 หัวข้อ · รายละเอียดและการตั้งค่าใช้ร่วมกันทั้งชุด</p>}
        {fieldGroups.filter(group => group.step === index).map(group => <StoryFields key={group.id} group={group} draft={draft} update={update}/>)}
        {index === 0 && <details className="story-writing-example"><summary>ตัวอย่างการเขียนแนวทาง</summary>
          <p>{examples[String(draft.speaker)]}</p><button type="button" onClick={() => {
            const example = examples[String(draft.speaker)];
            if (!String(draft.storyText).includes(example)) update('storyText', [draft.storyText, example].filter(Boolean).join('\n\n'));
          }}>เพิ่มตัวอย่างในรายละเอียด</button></details>}
        {warnings.length > 0 && <aside className="story-configuration-notes" aria-label="ข้อสังเกตของการตั้งค่า"><strong>ตรวจอีกครั้งก่อนเชื่อมระบบจริง</strong><ul>{warnings.map(warning => <li key={warning}>{warning}</li>)}</ul></aside>}
      </div>;
    },
  }));
  steps.push({ id: 'review', label: 'ตรวจรายละเอียด', title: 'ตรวจรายละเอียดเรื่องของคุณ',
    description: 'ตรวจแบบร่างก่อนเริ่มงานจำลอง ผลที่ได้ไม่ใช่สื่อจริง', render: () => <div className="story-review">
      <div className="story-review-topic"><h3>{draft.creationMode === 'batch' ? batchTopics(draft).join('\n') : String(draft.topic)}</h3><p>{draft.creationMode === 'batch' ? `${batchTopics(draft).length} คลิป` : 'คลิปเดียว'} · สำหรับ{String(draft.audience)}</p></div>
      {fieldGroups.map(group => <details className="story-review-section" key={group.id} open={group.step === 0 || undefined}><summary>{group.title}</summary>
        <dl className="story-review-grid">{group.fields.filter(field => visible(field, draft)).map(field => <div key={field.id}><dt>{field.label}</dt><dd>{fieldDisplay(field, draft)}</dd></div>)}</dl>
      </details>)}
      {warnings.length > 0 && <aside className="story-configuration-notes"><strong>ยังต้องตรวจความเข้ากันได้</strong><ul>{warnings.map(warning => <li key={warning}>{warning}</li>)}</ul></aside>}
      <p className="story-draft-notice">แบบร่างและไฟล์บันทึกไว้ในเครื่อง งานที่เริ่มจากหน้านี้เป็นการจำลองเท่านั้น</p>
      {canStart && startResult && !startResult.ok && <div className="story-start-actions">
        <p role="alert">{startErrorText[startResult.code] || startResult.message || startResult.code}
          {startResult.traceId && <> · Trace: {startResult.traceId}</>}</p></div>}
    </div> });
  return <div className="story-workspace"><div className="story-page-heading"><h1>เรื่องเล่า short</h1>
    <div className="draft-save-status" role="status">{{ loading: 'กำลังเปิดแบบร่าง…', load_error: 'เปิดแบบร่างไม่สำเร็จ', saved: 'บันทึกแล้วในเครื่อง', saving: 'กำลังบันทึก…', error: 'บันทึกไม่สำเร็จ', conflict: 'พบข้อมูลจากอีกหน้าต่าง' }[persistence.state]}</div>
      {serverIssues.lines.length > 0 && <ul className="draft-issue-summary" aria-label="สิ่งที่ต้องตรวจก่อนสร้าง" style={{ listStyle: 'none', margin: '4px 0 0', padding: 0, opacity: serverIssues.stale ? 0.7 : 1 }}>
        {serverIssues.stale && <li><em>{serverIssues.stale}</em></li>}
        {serverIssues.lines.map(line => <li key={line}>{line}</li>)}</ul>}</div>
    {queued && <div className="story-queued-notice" role="status">
      <span className="pill">SIMULATION</span> เพิ่ม “{queued.title || queued.jobId.slice(0, 8)}” เข้าคิวแล้ว · ดูความคืบหน้าในคิวงาน
      {!queued.opened && <> · ยังเปิดแบบร่างใหม่ไม่สำเร็จ <button type="button"
        onClick={() => void openNext({ id: queued.jobId }, queued.title)}>เปิดแบบร่างใหม่</button></>}</div>}
    {canQueue && <QueuePanel kind="story" compact canCommand={canCommand}/>}
    {persistence.error && <div role="alert" className="story-configuration-notes">{persistence.error}
      {persistence.state === 'conflict' ? <button onClick={() => { if (confirm('แทนข้อมูลในหน้านี้ด้วยแบบร่างล่าสุดที่บันทึกไว้?')) void persistence.reload(); }}>โหลดแบบร่างล่าสุดแทนหน้านี้</button>
        : <button onClick={() => void persistence.retry()}>ลองบันทึกอีกครั้ง</button>}</div>}
    {!['loading', 'load_error'].includes(persistence.state) && <StepWizard key={persistence.generation} steps={steps} initialStep={persistence.step}
      onStepChange={step => { if (step !== persistence.step) persistence.update(draft, step); }}
      finishLabel="ยืนยันรายละเอียดแบบร่าง" completionMessage="ตรวจรายละเอียดครบแล้ว · ยังไม่เริ่มสร้างสื่อ"
      finishAction={canStart ? startAction : undefined}
      footerNote="บันทึกอัตโนมัติในเครื่อง · รอสถานะบันทึกแล้วก่อนปิดโปรแกรม"/>}
  </div>;
}
