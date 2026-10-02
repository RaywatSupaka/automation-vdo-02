import { useState } from 'react';
import { Clapperboard, Image, Mic2, Sparkles, Captions, Check } from 'lucide-react';
import { StepWizard, type WizardStep } from '../../components/step-wizard/StepWizard';
import { createStoryDraft, validateStoryStep, type StoryDraft } from './draft';
import './story-shorts.css';

function Choices({ label, options, value, onChange }: { label: string; options: string[]; value: string; onChange: (value: string) => void }) {
  return <fieldset className="story-choices"><legend>{label}</legend><div>{options.map(option => <label key={option} className={value === option ? 'is-selected' : ''}>
    <input type="radio" name={label} value={option} checked={value === option} onChange={() => onChange(option)}/>
    <span>{option}</span>{value === option && <Check size={15} aria-hidden="true"/>}
  </label>)}</div></fieldset>;
}

export function StoryShorts() {
  const [draft, setDraft] = useState(createStoryDraft);
  function fields(markChanged: () => void) {
    return <K extends keyof StoryDraft>(key: K, value: StoryDraft[K]) => {
      setDraft(current => ({ ...current, [key]: value })); markChanged();
    };
  }
  const steps: WizardStep[] = [
    { id: 'idea', label: 'เรื่องที่จะเล่า', title: 'เรื่องราวของคุณ เริ่มจากอะไร?',
      description: 'มีแค่ไอเดียสั้น ๆ ก็เริ่มได้ หรือใส่เรื่องย่อที่อยากให้ยึดเป็นแนวทาง',
      validate: () => validateStoryStep(draft, 0), render: dirty => {
        const update = fields(dirty);
        return <div className="story-intro-grid"><div className="story-fields">
          <label htmlFor="story-topic">หัวข้อหรือเรื่องย่อ <span className="required-label">จำเป็น</span></label>
          <textarea id="story-topic" rows={3} maxLength={2000} aria-required="true" value={draft.topic} onChange={e => update('topic', e.target.value)}
            placeholder="เช่น แมวจรตัวหนึ่งที่รอเจ้าของหน้าสถานีรถไฟทุกเย็น จนวันหนึ่งมีเด็กน้อยเข้ามานั่งข้าง ๆ" aria-describedby="story-topic-help"/>
          <div className="story-field-hint" id="story-topic-help"><span>เล่าว่าใคร เจออะไร และอยากให้คนดูรู้สึกอย่างไร</span><span>{draft.topic.length}/2,000</span></div>
          <label htmlFor="story-audience">เล่าให้ใครฟัง</label><select id="story-audience" value={draft.audience} onChange={e => update('audience', e.target.value)}>
            {['ผู้ชมทั่วไป', 'เด็กและครอบครัว', 'วัยรุ่น', 'วัยทำงาน'].map(value => <option key={value}>{value}</option>)}
          </select>
        </div><aside className="story-tip"><span className="story-tip-icon"><Sparkles size={23}/></span><p className="eyebrow">จากไอเดีย สู่เรื่องราว</p>
          <h3>เรื่องเล็ก ๆ<br/>ก็เป็น Short ที่น่าจดจำได้</h3><p>เริ่มจากหนึ่งตัวละคร หนึ่งเหตุการณ์ และหนึ่งความรู้สึกที่อยากทิ้งไว้ให้คนดู</p>
          <div className="story-example">“ร้านกาแฟที่รับฟังความฝัน<br/>แทนการรับเงิน”</div><small>ตัวอย่างไอเดีย · ไม่ได้เติมลงในเรื่องของคุณ</small></aside></div>;
      } },
    { id: 'style', label: 'โทนและสไตล์', title: 'อยากให้เรื่องนี้รู้สึกแบบไหน?',
      description: 'เลือกอารมณ์ของเรื่องและแนวภาพ เพื่อให้ทุกฉากไปในทิศทางเดียวกัน', render: dirty => {
        const update = fields(dirty);
        return <div className="story-fields">
          <Choices label="โทนเรื่อง" options={['อบอุ่น', 'ตลก', 'ลึกลับ', 'ดราม่า', 'สร้างแรงบันดาลใจ']} value={draft.tone} onChange={value => update('tone', value)}/>
          <Choices label="สไตล์ภาพ" options={['ภาพยนตร์', 'การ์ตูน 3D', 'ภาพวาด', 'อนิเมะ']} value={draft.visualStyle} onChange={value => update('visualStyle', value)}/>
          <Choices label="ตอนจบ" options={['จบสมบูรณ์', 'หักมุม', 'ทิ้งคำถาม']} value={draft.ending} onChange={value => update('ending', value)}/>
          <label htmlFor="story-notes">รายละเอียดที่ต้องการเน้นหรือหลีกเลี่ยง <span className="optional-label">ไม่จำเป็น</span></label>
          <textarea id="story-notes" rows={3} maxLength={1000} value={draft.notes} onChange={e => update('notes', e.target.value)} placeholder="เช่น ตัวเอกใส่เสื้อสีเหลืองตลอดเรื่อง ไม่ใช้ฉากรุนแรง"/>
        </div>;
      } },
    { id: 'scenes', label: 'ฉากและความยาว', title: 'จัดจังหวะให้เรื่องของคุณ',
      description: 'กำหนดกรอบของเรื่องก่อนแบ่งบทและภาพเป็นฉาก ระยะเวลาจริงจะปรับตามเสียงพากย์',
      validate: () => validateStoryStep(draft, 2), render: dirty => {
        const update = fields(dirty);
        return <div className="story-scene-grid"><div className="story-fields">
          <label htmlFor="story-seconds">ความยาวเป้าหมาย (วินาที)</label><input id="story-seconds" type="number" min={30} max={60} step={1} value={draft.seconds} onChange={e => update('seconds', e.target.value)}/>
          <p className="story-help">30–60 วินาทีสำหรับแบบร่างรุ่นแรก</p>
          <label htmlFor="story-scenes">จำนวนฉาก</label><input id="story-scenes" type="number" min={1} max={12} step={1} value={draft.scenes} onChange={e => update('scenes', e.target.value)}/>
          <p className="story-help">1–12 ฉาก · เริ่มต้นแนะนำ 6 ฉาก</p>
          <div className="story-info"><Image size={20}/><div><strong>ภาพนิ่ง พร้อมแพนและซูม</strong><p>วางแผนภาพจาก ChatGPT Web แล้วประกอบการเคลื่อนไหวในเครื่อง</p></div></div>
        </div><div className="story-format"><div className="story-phone"><span>STORY SHORTS</span><Clapperboard size={34}/><strong>9:16</strong><small>แนวตั้ง</small></div><p>เป้าหมาย 1080 × 1920</p></div></div>;
      } },
    { id: 'audio', label: 'เสียงและซับ', title: 'ให้เรื่องเล่ามีเสียงของตัวเอง',
      description: 'กำหนดรูปแบบเสียงและซับไว้ก่อน รายชื่อเสียงจริงจะเพิ่มเมื่อเชื่อมผู้ให้บริการแล้ว', render: dirty => {
        const update = fields(dirty);
        return <div className="story-fields"><div className="story-info"><Mic2 size={23}/><div><strong>ผู้บรรยายภาษาไทย · หนึ่งคน</strong><p>เสียงพากย์จะสร้างผ่านบริการเสียงแยกจาก ChatGPT Web</p><span className="story-coming">ยังไม่ได้เชื่อมบริการเสียง</span></div></div>
          <label className="story-toggle"><span className="story-toggle-icon"><Captions size={23}/></span><span><strong>ซับภาษาไทย</strong><small>วางซับตามจังหวะเสียงพากย์</small></span><input type="checkbox" checked={draft.subtitles} onChange={e => update('subtitles', e.target.checked)} aria-label="ซับภาษาไทย"/></label>
          <label className="story-toggle"><span className="story-toggle-icon"><Check size={23}/></span><span><strong>พักให้ตรวจบทก่อนสร้างภาพ</strong><small>ปิดไว้เพื่อให้ทำต่ออัตโนมัติเมื่อข้อมูลผ่านการตรวจ</small></span><input type="checkbox" checked={draft.reviewBeforeImages} onChange={e => update('reviewBeforeImages', e.target.checked)} aria-label="พักให้ตรวจบทก่อนสร้างภาพ"/></label>
        </div>;
      } },
    { id: 'review', label: 'ตรวจรายละเอียด', title: 'เรื่องของคุณ พร้อมวางแผนแล้ว',
      description: 'ตรวจรายละเอียดอีกครั้ง กดขั้นตอนด้านบนเพื่อย้อนกลับไปแก้ไขได้', render: () => <div className="story-review">
        <div className="story-review-topic"><p className="eyebrow">เรื่องที่จะเล่า</p><h3>{draft.topic}</h3><p>สำหรับ{draft.audience}</p></div>
        <dl className="story-review-grid">
          <div><dt>โทน / ตอนจบ</dt><dd>{draft.tone} · {draft.ending}</dd></div><div><dt>แนวภาพ</dt><dd>{draft.visualStyle}</dd></div>
          <div><dt>ฉาก / ความยาวเป้าหมาย</dt><dd>{draft.scenes} ฉาก · {draft.seconds} วินาที</dd></div><div><dt>รูปแบบ</dt><dd>9:16 · ภาพนิ่งแพน/ซูม</dd></div>
          <div><dt>เสียงและซับ</dt><dd>ผู้บรรยายไทย · {draft.subtitles ? 'เปิดซับ' : 'ไม่ใส่ซับ'}</dd></div><div><dt>ก่อนสร้างภาพ</dt><dd>{draft.reviewBeforeImages ? 'พักให้ตรวจบท' : 'ทำต่ออัตโนมัติ'}</dd></div>
        </dl>{draft.notes && <div className="story-review-notes"><strong>รายละเอียดเพิ่มเติม</strong><p>{draft.notes}</p></div>}
        <p className="story-draft-notice">นี่คือแบบร่างหน้าจอ ยังไม่ส่งให้ AI และยังไม่สร้างบท ภาพ หรือวิดีโอ</p>
      </div> },
  ];

  return <div className="story-workspace"><div className="story-page-heading"><div><p className="eyebrow">CREATE A STORY</p><h1>เรื่องเล่า Shorts</h1><p>ค่อย ๆ เติมไอเดีย แล้วให้เรื่องราวเป็นรูปเป็นร่าง</p></div><span className="story-draft-badge">แบบร่าง</span></div>
    <StepWizard steps={steps} finishLabel="ยืนยันรายละเอียดแบบร่าง" completionMessage="ตรวจรายละเอียดครบแล้ว · แบบร่างยังอยู่ในหน้านี้ ยังไม่เริ่มสร้างสื่อ"
      footerNote="ข้อมูลอยู่ชั่วคราวในหน้านี้ · ปิดหรือรีโหลดโปรแกรมแล้วข้อมูลจะหาย"/>
  </div>;
}
