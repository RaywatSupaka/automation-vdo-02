import { choices, fieldGroups, visible, type StoryDraft } from './fields';
export type { StoryDraft } from './fields';
export const createStoryDraft = (): StoryDraft => Object.fromEntries(fieldGroups.flatMap(group => group.fields.map(field => [field.id, Array.isArray(field.initial) ? [] : field.initial])));
export const batchTopics = (draft: StoryDraft): string[] => String(draft.batchTopics || '').split(/\r?\n/).map(line => line.trim()).filter(Boolean);

// UI feedback only; the future backend must enforce its own schema independently.
export function validateStoryStep(draft: StoryDraft, step: number): string | null {
  for (const field of fieldGroups.filter(group => group.step === step).flatMap(group => group.fields)) {
    if (!visible(field, draft) || field.disabled) continue;
    const value = draft[field.id], empty = Array.isArray(value) ? !value.length : !String(value ?? '').trim();
    if (field.required && empty) return `กรุณาระบุ${field.label}`;
    if (empty) continue;
    if (field.maxLength && String(value).length > field.maxLength) return `${field.label}ต้องไม่เกิน ${field.maxLength.toLocaleString()} ตัวอักษร`;
    if (field.kind === 'number' || field.kind === 'range') {
      const numeric = Number(value), increment = field.step || 1;
      if (!Number.isFinite(numeric) || numeric < field.min! || numeric > field.max! || Math.abs(numeric / increment - Math.round(numeric / increment)) > 1e-6)
        return `${field.label}ต้องอยู่ระหว่าง ${field.min} ถึง ${field.max} โดยเพิ่มทีละ ${increment}`;
    }
    if (field.kind === 'select' && !choices(field, draft).some(([key]) => key === value)) return `เลือก${field.label}ใหม่ให้ตรงกับตัวเลือกที่มี`;
    if (field.kind === 'file' && Array.isArray(value)) {
      if (value.some(file => 'missing' in file && file.missing)) return `${field.label}: ไฟล์ที่บันทึกไว้หาย กรุณาเลือกใหม่`;
      if (field.maxFiles && value.length > field.maxFiles) return `${field.label}เลือกได้ไม่เกิน ${field.maxFiles} ไฟล์`;
      const extensions = field.accept?.split(',') || [];
      if (value.some(file => !extensions.some(extension => file.name.toLowerCase().endsWith(extension)))) return `${field.label}: ชนิดไฟล์ไม่รองรับ`;
      if (value.some(file => file.size > 500 * 1024 * 1024)) return `${field.label}: แต่ละไฟล์ต้องไม่เกิน 500 MB`;
    }
  }
  if (step === 0 && draft.creationMode === 'batch' && batchTopics(draft).length > 10) return 'เพิ่มได้สูงสุด 10 หัวข้อในหนึ่งชุด';
  if (step === 3 && draft.musicEnabled && Array.isArray(draft.musicFiles) && Number(draft.musicCount) > draft.musicFiles.length) return 'จำนวนเพลงต่อคลิปต้องไม่เกินจำนวนไฟล์ที่เลือก';
  return null;
}

export function draftWarnings(draft: StoryDraft): string[] {
  const warnings: string[] = [];
  if (['solo', 'dialogue'].includes(String(draft.speaker)) && draft.videoMode === 'image_motion') warnings.push('ตัวละครพูดเองหรือสนทนาต้องใช้ Google Flow หรือ Meta AI เมื่อเชื่อมระบบจริง');
  if (draft.speaker === 'visual' && (draft.audioMode !== 'none' || draft.cta)) warnings.push('โหมดเล่าด้วยภาพควรปิดเสียงหลักและคำชวนติดตามที่เป็นบทพูด');
  if (draft.audioMode === 'flow_original' && draft.videoMode === 'image_motion') warnings.push('ภาพเคลื่อนไหวในเครื่องไม่มีเสียงต้นฉบับจากคลิป AI');
  if (draft.generatedMusic && draft.videoMode === 'image_motion') warnings.push('ดนตรีจาก AI ต้องใช้ provider ที่สร้างวิดีโอพร้อมเสียง');
  if (String(draft.flowModel).startsWith('Veo') && (draft.flowResolution === '360p' || draft.flowDuration === '10s')) warnings.push('ชุดค่า Flow นี้ไม่ตรงกับตัวเลือกที่บันทึกในระบบเดิม ต้องตรวจบัญชีจริงก่อนใช้');
  const topics = batchTopics(draft);
  if (draft.creationMode === 'batch' && new Set(topics).size !== topics.length) warnings.push('มีหัวข้อซ้ำในชุด ระบบเก็บข้อความเดิมไว้ให้คุณตรวจ');
  return warnings;
}
