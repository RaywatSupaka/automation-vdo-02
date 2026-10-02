import { useId, type ReactNode } from 'react';
import { choices, visible, type Field, type FieldGroup, type StoryDraft, type DraftValue } from './fields';

export function RequiredMark() { return <span className="required-mark" aria-hidden="true">*</span>; }
type Props = { group: FieldGroup; draft: StoryDraft; update: (id: string, value: DraftValue) => void };

function FieldControl({ field, draft, update }: { field: Field; draft: StoryDraft; update: Props['update'] }) {
  const id = useId(), value = draft[field.id];
  const common = { id, 'aria-label': field.label, 'aria-required': field.required || undefined,
    'aria-describedby': field.help ? `${id}-help` : undefined, disabled: field.disabled };
  let control: ReactNode;
  if (field.kind === 'select') control = <select {...common} value={String(value)} onChange={e => update(field.id, e.target.value)}>
    {choices(field, draft).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>;
  else if (field.kind === 'textarea') control = <textarea {...common} rows={3} maxLength={field.maxLength} value={String(value)} onChange={e => update(field.id, e.target.value)}/>;
  else if (field.kind === 'file') {
    const files = Array.isArray(value) ? value : [];
    const reorder = (index: number, offset: number) => {
      const copy = [...files]; [copy[index], copy[index + offset]] = [copy[index + offset], copy[index]]; update(field.id, copy);
    };
    control = <><input {...common} type="file" accept={field.accept} multiple={field.multiple} onChange={e => {
      update(field.id, Array.from(e.target.files || [])); e.target.value = '';
    }}/>{files.length > 0 && <ul className="story-file-list">{files.map((file, index) => <li key={`${index}-${file.name}`}>
      <span>{file.name} · {Math.max(1, Math.round(file.size / 1024))} KB {'missing' in file && file.missing ? '· ไม่พบไฟล์ กรุณาเลือกใหม่' : ''}</span><div>
        {field.id === 'greenFiles' && <><button type="button" disabled={index === 0} aria-label={`เลื่อนเอฟเฟกต์ ${index + 1} ขึ้น`} onClick={() => reorder(index, -1)}>↑</button>
          <button type="button" disabled={index === files.length - 1} aria-label={`เลื่อนเอฟเฟกต์ ${index + 1} ลง`} onClick={() => reorder(index, 1)}>↓</button></>}
        <button type="button" aria-label={`เอาไฟล์ ${file.name} ออกจากแบบร่าง`} onClick={() => update(field.id, files.filter((_, i) => i !== index))}>เอาออก</button>
      </div></li>)}</ul>}</>;
  } else control = <input {...common} type={field.kind} value={String(value)} min={field.min} max={field.max} step={field.step} maxLength={field.maxLength} onChange={e => update(field.id, e.target.value)}/>;

  if (field.kind === 'checkbox') return <label className="story-setting-toggle"><input id={id} type="checkbox" aria-label={field.label} checked={value === true} onChange={e => update(field.id, e.target.checked)}/><span>{field.label}</span></label>;
  return <div className={`story-setting-field ${['textarea', 'file'].includes(field.kind) ? 'full-width' : ''}`}>
    <label htmlFor={id}>{field.label} {field.required && <RequiredMark/>}{field.kind === 'range' && <output htmlFor={id}>{String(value)}</output>}</label>
    {control}{field.help && <small id={`${id}-help`}>{field.help}</small>}
  </div>;
}

export function StoryFields({ group, draft, update }: Props) {
  return <details className="story-setting-group" open={group.open || undefined}>
    <summary>{group.title}<span>แบบร่าง</span></summary>
    <div className="story-setting-content">{group.help && <p className="story-group-help">{group.help}</p>}
      {group.id === 'voice' && <div className="story-service-placeholder"><p>SmartSub ยังไม่เชื่อมต่อ · เครดิตและรายชื่อเสียงยังไม่พร้อม</p><button type="button" disabled>เชื่อมต่อ / เลือกเสียง / ฟังตัวอย่าง — ยังไม่เปิดใช้</button></div>}
      <div className="story-settings-grid">{group.fields.filter(field => visible(field, draft)).map(field => <FieldControl key={field.id} field={field} draft={draft} update={update}/>)}</div>
      {['flow', 'logo', 'subtitles', 'intro', 'green'].includes(group.id) && <p className="story-group-help">เลือกค่าได้ แต่ยังไม่เชื่อมบริการ พรีวิวผลจริง หรือบันทึกเป็นค่าเริ่มต้น</p>}
    </div>
  </details>;
}

export function fieldDisplay(field: Field, draft: StoryDraft): string {
  const value = draft[field.id];
  if (Array.isArray(value)) return value.length ? value.map(file => file.name).join(', ') : 'ยังไม่ได้เลือกไฟล์';
  if (typeof value === 'boolean') return value ? 'เปิด' : 'ปิด';
  if (field.kind === 'select') return choices(field, draft).find(([key]) => key === value)?.[1] || 'ยังไม่ได้เลือก';
  return String(value || 'ไม่ได้ระบุ');
}
