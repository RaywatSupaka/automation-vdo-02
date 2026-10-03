import { useDraft } from './useDraft';
import { StepWizard, type WizardStep } from '../../components/step-wizard/StepWizard';
import { batchTopics, draftWarnings, validateStoryStep } from './draft';
import { fieldGroups, visible, type DraftValue } from './fields';
import type { DraftIssue, SaveState } from './persistence';
import { fieldDisplay, RequiredMark, StoryFields } from './StoryFields';
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

export function StoryShorts() {
  const persistence = useDraft();
  const draft = persistence.draft;
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
    description: 'ข้อมูลทั้งหมดที่เลือกไว้เป็นแบบร่าง ยังไม่ส่งให้ AI หรือเพิ่มลงคิวจริง', render: () => <div className="story-review">
      <div className="story-review-topic"><h3>{draft.creationMode === 'batch' ? batchTopics(draft).join('\n') : String(draft.topic)}</h3><p>{draft.creationMode === 'batch' ? `${batchTopics(draft).length} คลิป` : 'คลิปเดียว'} · สำหรับ{String(draft.audience)}</p></div>
      {fieldGroups.map(group => <details className="story-review-section" key={group.id} open={group.step === 0 || undefined}><summary>{group.title}</summary>
        <dl className="story-review-grid">{group.fields.filter(field => visible(field, draft)).map(field => <div key={field.id}><dt>{field.label}</dt><dd>{fieldDisplay(field, draft)}</dd></div>)}</dl>
      </details>)}
      {warnings.length > 0 && <aside className="story-configuration-notes"><strong>ยังต้องตรวจความเข้ากันได้</strong><ul>{warnings.map(warning => <li key={warning}>{warning}</li>)}</ul></aside>}
      <p className="story-draft-notice">บันทึกแบบร่างและไฟล์ไว้ในเครื่อง ยังไม่ส่งให้ AI หรือสร้างสื่อ</p>
    </div> });
  return <div className="story-workspace"><div className="story-page-heading"><h1>เรื่องเล่า short</h1>
    <div className="draft-save-status" role="status">{{ loading: 'กำลังเปิดแบบร่าง…', load_error: 'เปิดแบบร่างไม่สำเร็จ', saved: 'บันทึกแล้วในเครื่อง', saving: 'กำลังบันทึก…', error: 'บันทึกไม่สำเร็จ', conflict: 'พบข้อมูลจากอีกหน้าต่าง' }[persistence.state]}</div>
      {serverIssues.lines.length > 0 && <ul className="draft-issue-summary" aria-label="สิ่งที่ต้องตรวจก่อนสร้าง" style={{ listStyle: 'none', margin: '4px 0 0', padding: 0, opacity: serverIssues.stale ? 0.7 : 1 }}>
        {serverIssues.stale && <li><em>{serverIssues.stale}</em></li>}
        {serverIssues.lines.map(line => <li key={line}>{line}</li>)}</ul>}</div>
    {persistence.error && <div role="alert" className="story-configuration-notes">{persistence.error}
      {persistence.state === 'conflict' ? <button onClick={() => { if (confirm('แทนข้อมูลในหน้านี้ด้วยแบบร่างล่าสุดที่บันทึกไว้?')) void persistence.reload(); }}>โหลดแบบร่างล่าสุดแทนหน้านี้</button>
        : <button onClick={() => void persistence.retry()}>ลองบันทึกอีกครั้ง</button>}</div>}
    {!['loading', 'load_error'].includes(persistence.state) && <StepWizard key={persistence.generation} steps={steps} initialStep={persistence.step}
      onStepChange={step => { if (step !== persistence.step) persistence.update(draft, step); }}
      finishLabel="ยืนยันรายละเอียดแบบร่าง" completionMessage="ตรวจรายละเอียดครบแล้ว · ยังไม่เริ่มสร้างสื่อ"
      footerNote="บันทึกอัตโนมัติในเครื่อง · รอสถานะบันทึกแล้วก่อนปิดโปรแกรม"/>}
  </div>;
}
