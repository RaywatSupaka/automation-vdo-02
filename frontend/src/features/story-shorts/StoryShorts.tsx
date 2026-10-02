import { useState } from 'react';
import { StepWizard, type WizardStep } from '../../components/step-wizard/StepWizard';
import { batchTopics, createStoryDraft, draftWarnings, validateStoryStep } from './draft';
import { fieldGroups, visible, type DraftValue } from './fields';
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

export function StoryShorts() {
  const [draft, setDraft] = useState(createStoryDraft);
  const warnings = draftWarnings(draft);
  const steps: WizardStep[] = stepInfo.map(([id, label, title, description], index) => ({
    id, label, title, description, validate: () => validateStoryStep(draft, index),
    render: dirty => {
      function update(key: string, value: DraftValue) { setDraft(current => ({ ...current, [key]: value })); dirty(); }
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
      <p className="story-draft-notice">ยังไม่บันทึกลงฐานข้อมูล ไม่อัปโหลดไฟล์ ไม่เชื่อม API และไม่สร้างบท ภาพ เสียง หรือวิดีโอ</p>
    </div> });
  return <div className="story-workspace"><div className="story-page-heading"><h1>เรื่องเล่า short</h1></div>
    <StepWizard steps={steps} finishLabel="ยืนยันรายละเอียดแบบร่าง" completionMessage="ตรวจรายละเอียดครบแล้ว · แบบร่างยังอยู่ในหน้านี้ ยังไม่เริ่มสร้างสื่อ"
      footerNote="ข้อมูลและไฟล์ที่เลือกอยู่ชั่วคราวในหน้านี้ · ปิดหรือรีโหลดแล้วข้อมูลจะหาย"/>
  </div>;
}
