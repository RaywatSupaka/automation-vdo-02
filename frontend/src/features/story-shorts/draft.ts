export type StoryDraft = {
  topic: string; audience: string; notes: string; tone: string; visualStyle: string;
  ending: string; scenes: string; seconds: string; subtitles: boolean; reviewBeforeImages: boolean;
};
export const createStoryDraft = (): StoryDraft => ({ topic: '', audience: 'ผู้ชมทั่วไป', notes: '',
  tone: 'อบอุ่น', visualStyle: 'ภาพยนตร์', ending: 'จบสมบูรณ์', scenes: '6', seconds: '45',
  subtitles: true, reviewBeforeImages: false });

// UI feedback only. The future Story API must independently validate its own contract.
export function validateStoryStep(draft: StoryDraft, step: number): string | null {
  if (step === 0 && !draft.topic.trim()) return 'ใส่หัวข้อหรือเรื่องย่อก่อน ไปขั้นถัดไปได้เมื่อมีเรื่องที่จะเล่าครับ';
  if (step === 0 && draft.topic.length > 2000) return 'หัวข้อหรือเรื่องย่อต้องไม่เกิน 2,000 ตัวอักษร';
  if (step === 2) {
    const scenes = Number(draft.scenes), seconds = Number(draft.seconds);
    if (!Number.isInteger(scenes) || scenes < 1 || scenes > 12) return 'ระบุจำนวนฉากเป็นจำนวนเต็มตั้งแต่ 1 ถึง 12 ฉาก';
    if (!Number.isInteger(seconds) || seconds < 30 || seconds > 60) return 'ระบุความยาวเป้าหมายตั้งแต่ 30 ถึง 60 วินาที';
  }
  return null;
}
