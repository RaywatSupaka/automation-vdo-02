import { chatgptModels, geminiModels, structures, subtitleAnimations, subtitleThemes, visualStyles } from './catalog';

export type StoredAsset = { id: string; name: string; size: number; missing?: boolean; sha256?: string };
export type DraftValue = string | boolean | (File | StoredAsset)[];
export type StoryDraft = Record<string, DraftValue>;
export type Option = readonly [string, string];
export type Field = {
  id: string; label: string; kind: 'text' | 'textarea' | 'number' | 'range' | 'select' | 'checkbox' | 'file' | 'color';
  initial: DraftValue; required?: boolean; options?: readonly Option[] | ((d: StoryDraft) => readonly Option[]);
  when?: (d: StoryDraft) => boolean; min?: number; max?: number; step?: number; maxLength?: number;
  help?: string; accept?: string; multiple?: boolean; maxFiles?: number; disabled?: boolean;
};
export type FieldGroup = { id: string; step: number; title: string; open?: boolean; help?: string; fields: Field[] };
const on = (id: string) => (d: StoryDraft) => d[id] === true;
const is = (id: string, value: string) => (d: StoryDraft) => d[id] === value;
const options = (...labels: string[]): Option[] => labels.map(label => [label, label]);
const select = (id: string, label: string, choices: Field['options'], initial: string, extra: Partial<Field> = {}): Field => ({ id, label, kind: 'select', options: choices, initial, ...extra });
const text = (id: string, label: string, extra: Partial<Field> = {}): Field => ({ id, label, kind: 'text', initial: '', maxLength: 1000, ...extra });
const toggle = (id: string, label: string, initial = false): Field => ({ id, label, kind: 'checkbox', initial });
const number = (id: string, label: string, initial: string, min: number, max: number, extra: Partial<Field> = {}): Field => ({ id, label, kind: 'number', initial, min, max, step: 1, ...extra });
const file = (id: string, label: string, accept: string, extra: Partial<Field> = {}): Field => ({ id, label, kind: 'file', initial: [], accept, help: 'นำเข้าสำเนาไว้ในเครื่องพร้อมแบบร่าง · ไม่ส่งไฟล์ไปบริการภายนอก', ...extra });
const imageTypes = '.png,.jpg,.jpeg,.webp';
const videoTypes = '.mp4,.mov,.mkv,.webm,.m4v,.avi';
const audioTypes = '.mp3,.wav,.m4a,.aac,.ogg';
const current: Option = ['', 'ใช้ค่าปัจจุบันบนเว็บ · ยังไม่ตรวจบัญชี'];
const flowModels = options('Omni 1.1 Flash', 'Veo 3.1 - Lite', 'Veo 3.1 - Fast', 'Veo 3.1 - Quality', 'Veo 3.1 - Lite [Lower Priority]');

export const fieldGroups: FieldGroup[] = [
  { id: 'brief', step: 0, title: 'หัวข้อและรายละเอียดเรื่อง', open: true, fields: [
    select('creationMode', 'จำนวนคลิปที่ต้องการเตรียม', [['single', 'คลิปเดียว'], ['batch', 'หลายคลิป · สูงสุด 10 หัวข้อ']], 'single'),
    text('topic', 'หัวข้อคลิป', { required: true, maxLength: 2000, when: is('creationMode', 'single') }),
    text('batchTopics', 'หัวข้อคลิปในชุด', { kind: 'textarea', required: true, maxLength: 20000, when: is('creationMode', 'batch'), help: 'หนึ่งบรรทัดต่อหนึ่งคลิป สูงสุด 10 คลิป · ใช้การตั้งค่าร่วมกัน ยังไม่เพิ่มคิวจริง' }),
    text('storyText', 'รายละเอียดเรื่องและวิธีเล่าที่ต้องการ', { kind: 'textarea', maxLength: 10000, help: 'แยกจากหัวข้อ เว้นว่างเพื่อให้ AI คิดตามหัวข้อได้ · ใช้ร่วมกันทุกคลิปเมื่อเลือกหลายคลิป' }),
    select('audience', 'เล่าให้ใครฟัง', options('ผู้ชมทั่วไป', 'เด็กและครอบครัว', 'วัยรุ่น', 'วัยทำงาน'), 'ผู้ชมทั่วไป'),
    file('mainImage', 'รูปหลัก / รูปอ้างอิงร่วม', imageTypes),
  ] },
  { id: 'narrative', step: 1, title: 'วิธีเล่าและโครงเรื่อง', open: true, fields: [
    select('speaker', 'ใครเป็นคนพูด', [['narrator', 'ผู้บรรยายเล่าเรื่อง'], ['solo', 'ตัวละครพูดเอง'], ['dialogue', 'ตัวละครสนทนา'], ['visual', 'เล่าเรื่องด้วยภาพ · ไม่มีบทพูด']], 'narrator'),
    select('structure', 'โครงเรื่อง', structures, 'legacy'),
    select('tone', 'โทนเรื่อง', options('ให้ AI เลือกตามเรื่อง', 'ตลก', 'อบอุ่น', 'ดราม่า', 'ลึกลับ', 'สร้างแรงบันดาลใจ'), 'ให้ AI เลือกตามเรื่อง'),
    select('hook', 'เปิดเรื่อง', options('ตามเนื้อเรื่อง', 'เปิดด้วยเหตุการณ์', 'เปิดด้วยคำถาม', 'เปิดด้วยสิ่งผิดปกติ'), 'ตามเนื้อเรื่อง'),
    select('ending', 'ตอนจบ', options('ตามลำดับตอน', 'จบเรื่องสมบูรณ์', 'หักมุม', 'ทิ้งปมให้ติดตาม', 'ทิ้งคำถาม'), 'ตามลำดับตอน'),
    toggle('cta', 'ชวนติดตามท้ายเรื่อง'),
  ] },
  { id: 'visual', step: 1, title: 'แนวภาพและรายละเอียดเพิ่มเติม', open: true, fields: [
    select('visualStyle', 'สไตล์ภาพ', visualStyles, 'auto'),
    text('visualCustom', 'แนวภาพที่กำหนดเอง', { kind: 'textarea', maxLength: 400, required: true, when: is('visualStyle', 'custom'), help: 'ระบุลายเส้น แสง สี หรือบรรยากาศที่ต้องการ' }),
    text('notes', 'รายละเอียดที่ต้องการเน้นหรือหลีกเลี่ยง', { kind: 'textarea', maxLength: 1000 }),
  ] },
  { id: 'providers', step: 2, title: 'ภาพและวิดีโอ', open: true, help: 'รายการจากระบบเดิมสำหรับออกแบบ ยังไม่ตรวจตัวเลือกหรือโควตาบนบัญชีจริง', fields: [
    select('imageProvider', 'สร้างภาพด้วย', [['chatgpt', 'ChatGPT Web'], ['gemini', 'Gemini Web']], 'chatgpt', { required: true }),
    select('chatgptModel', 'โมเดล ChatGPT', chatgptModels, 'auto', { when: is('imageProvider', 'chatgpt'), help: 'ของเดิมใช้โมเดลปัจจุบันอัตโนมัติ; ตัวเลือกอื่นเป็นแบบร่าง ยังไม่เชื่อม Extension' }),
    select('geminiModel', 'โมเดล Gemini', geminiModels, 'long_thinking', { when: is('imageProvider', 'gemini') }),
    select('videoMode', 'เปลี่ยนภาพเป็นวิดีโอด้วย', [['image_motion', 'ภาพเคลื่อนไหวอัตโนมัติในเครื่อง'], ['google_flow', 'Google Flow ทุกฉาก'], ['meta_ai', 'Meta AI ทุกฉาก · ทดลอง']], 'image_motion', { required: true }),
    number('scenes', 'จำนวนฉาก', '10', 6, 15, { required: true, help: 'ตรงกับระบบเดิม 6–15 ฉาก; แนะนำ 8–10 ฉาก' }),
    number('seconds', 'ความยาวเป้าหมาย (วินาที)', '45', 30, 60, { help: 'ตัวเลือกจากฟอร์มใหม่ เว้นว่างได้ · ระยะเวลาจริงขึ้นอยู่กับเสียงและจำนวนฉาก' }),
    toggle('fictionalCharacters', 'ยืนยันว่าบุคคลในภาพเป็นตัวละครสมมติจาก AI ไม่ใช่บุคคลจริง'),
  ] },
  { id: 'flow', step: 2, title: 'รายละเอียด Google Flow', help: 'ตั้งไว้เป็นแบบร่างได้แม้ยังไม่ได้เลือก Flow · ต้องตรวจความสามารถจริงก่อนสร้าง', fields: [
    select('flowModel', 'โมเดลวิดีโอ Flow', [current, ...flowModels], ''),
    select('flowReference', 'รูปแบบอ้างอิง', [current, ['Frames', 'เฟรมต้นจากภาพ'], ['Ingredients', 'องค์ประกอบจากภาพ']], ''),
    select('flowResolution', 'ความละเอียดจาก Flow', [current, ['360p', '360p'], ['720p', '720p']], ''),
    select('flowDuration', 'เวลาต่อฉากจาก Flow', [current, ...options('4s', '6s', '8s', '10s')], ''),
  ] },
  { id: 'motion', step: 2, title: 'การประกอบภาพในเครื่อง', fields: [
    number('motion', 'Motion (%)', '100', 0, 200, { kind: 'range' }),
    number('transition', 'Transition (ms)', '220', 0, 600, { kind: 'range', step: 20 }),
  ] },
  { id: 'cover', step: 2, title: 'ปกคลิป', fields: [
    toggle('aiCover', 'สร้างปกด้วย AI เมื่อคลิปเสร็จ', true),
    select('coverScene', 'ภาพอ้างอิงปก', d => [['auto', 'เลือกภาพอัตโนมัติ'], ...Array.from({ length: Math.max(0, Math.min(15, Number(d.scenes) || 0)) }, (_, i) => [String(i + 1), `ฉากที่ ${i + 1}`] as Option)], 'auto', { when: on('aiCover') }),
    text('coverHeadline', 'ข้อความบนปก', { maxLength: 40, help: 'เว้นว่างให้เลือกจากชื่อเรื่อง · ของเดิมแก้ได้ในหน้าปกหลังสร้าง' }),
    text('coverEmphasis', 'คำบนปกที่ต้องการเน้นสี', { maxLength: 40 }),
    select('coverTheme', 'รูปแบบปก', options('ตัวใหญ่ชัด', 'ลึกลับชวนดู', 'สินค้าเด่น', 'โรแมนติก'), 'ตัวใหญ่ชัด'),
    select('coverPosition', 'ตำแหน่งข้อความปก', options('ด้านบน', 'ตรงกลาง', 'ด้านล่าง'), 'ตรงกลาง'),
  ] },
  { id: 'intro', step: 2, title: 'อินโทร', fields: [
    toggle('introEnabled', 'สุ่มแทรกอินโทรหลังเริ่มเล่าเรื่อง'),
    file('introFile', 'วิดีโออินโทร', videoTypes, { when: on('introEnabled'), required: true, help: 'เลือกไว้ในแบบร่าง · ตำแหน่งแทรกจากระบบเดิมประมาณวินาทีที่ 4–12 ยังไม่เรนเดอร์' }),
  ] },
  { id: 'green', step: 2, title: 'กรีนสกรีน / แสง', fields: [
    toggle('greenEnabled', 'ใส่กรีนสกรีน / แสง (ไม่มีเสียง)'),
    file('greenFiles', 'ไฟล์เอฟเฟกต์ตามลำดับ', videoTypes, { when: on('greenEnabled'), required: true, multiple: true, maxFiles: 3, help: 'เลือก 1–3 ไฟล์ แต่ละไฟล์ไม่เกิน 500 MB · เรียงลำดับด้านล่างได้ ยังไม่ลบพื้นเขียวจริง' }),
    number('greenOpacity', 'ความเข้มเอฟเฟกต์ (%)', '50', 1, 100, { kind: 'range', when: on('greenEnabled') }),
    select('greenFit', 'จัดภาพเอฟเฟกต์', options('แสดงครบภาพ ไม่ยืด', 'เต็มเฟรม ตัดส่วนเกิน'), 'แสดงครบภาพ ไม่ยืด', { when: on('greenEnabled') }),
  ] },
  { id: 'logo', step: 2, title: 'โลโก้บนวิดีโอ', fields: [
    toggle('logoEnabled', 'ใส่โลโก้บนวิดีโอ'),
    file('logoFile', 'รูปโลโก้', imageTypes, { when: on('logoEnabled'), required: true }),
    number('logoOpacity', 'ความทึบโลโก้ (%)', '100', 5, 100, { kind: 'range', when: on('logoEnabled') }),
    number('logoSize', 'ขนาดโลโก้ (%)', '15', 3, 60, { kind: 'range', when: on('logoEnabled') }),
    select('logoPosition', 'ตำแหน่งโลโก้', options('บนซ้าย', 'บนกลาง', 'บนขวา', 'กลางซ้าย', 'กึ่งกลาง', 'กลางขวา', 'ล่างซ้าย', 'ล่างกลาง', 'ล่างขวา', 'กำหนดพิกัดเอง'), 'บนขวา', { when: on('logoEnabled') }),
    number('logoMargin', 'ระยะขอบโลโก้ (px)', '24', 0, 120, { when: on('logoEnabled') }),
    number('logoX', 'กึ่งกลางแนวนอน (%)', '50', 0, 100, { step: .1, when: on('logoEnabled') }),
    number('logoY', 'กึ่งกลางแนวตั้ง (%)', '50', 0, 100, { step: .1, when: on('logoEnabled') }),
  ] },
  { id: 'voice', step: 3, title: 'เสียงหลักและ SmartSub', open: true, fields: [
    select('audioMode', 'เสียงหลัก', [['api', 'เสียงพากย์ API SmartSub'], ['flow_original', 'เสียงต้นฉบับจากคลิป'], ['none', 'ไม่ใช้เสียงหลัก']], 'api'),
    select('voice', 'เสียงจากระบบ API', [['', 'ยังไม่เชื่อมต่อ SmartSub / ยังไม่โหลดรายชื่อเสียง']], '', { disabled: true, when: is('audioMode', 'api') }),
    file('voiceReference', 'ไฟล์เสียงอ้างอิง 5–30 วินาที', audioTypes, { when: is('audioMode', 'api'), help: 'เลือกไว้ในแบบร่าง ยังไม่อัปโหลดหรือสร้างเสียงอ้างอิง และยังไม่ตรวจความยาวไฟล์' }),
    text('voiceReferenceId', 'reference_id ของเสียง', { when: is('audioMode', 'api'), help: 'รหัสอ้างอิงเสียงที่มีอยู่ ไม่ใช่ API Key; ยังไม่ตรวจสอบกับบริการ' }),
    select('voiceLanguage', 'ภาษาเสียงพากย์', options('th', 'en', 'ja', 'zh'), 'th', { when: is('audioMode', 'api') }),
    select('voiceEmotion', 'อารมณ์เสียง', options('Normal (มาตรฐาน)'), 'Normal (มาตรฐาน)', { disabled: true, when: is('audioMode', 'api') }),
    number('voiceSpeed', 'ความเร็วเสียง', '1', 1, 1, { disabled: true, when: is('audioMode', 'api') }),
    number('voiceSilence', 'เว้นท้ายเสียง (วินาที)', '0', 0, 3, { step: .1, when: is('audioMode', 'api') }),
    select('voiceFormat', 'ชนิดไฟล์เสียง', options('mp3', 'wav', 'mp4'), 'mp3', { when: is('audioMode', 'api') }),
    text('voiceScript', 'บทพูดสำหรับเสียง (ถ้าต้องการกำหนดเอง)', { kind: 'textarea', maxLength: 10000, when: is('audioMode', 'api') }),
    toggle('keepVideoAudio', 'เก็บเสียงต้นฉบับไว้ผสมกับเสียงพากย์'),
    number('videoAudioVolume', 'ระดับเสียงต้นฉบับจากคลิป (%)', '35', 0, 100, { kind: 'range' }),
    toggle('allowSilent', 'ยอมรับช่วงเงียบหากฉากไม่มีเสียง'),
  ] },
  { id: 'subtitles', step: 3, title: 'คำบรรยายและรูปแบบซับ', fields: [
    toggle('subtitles', 'ซับภาษาไทย', true),
    select('subtitleLanguage', 'ภาษาคำบรรยาย', options('th', 'en'), 'th', { when: on('subtitles') }),
    number('subtitleSyllables', 'พยางค์ต่อช่วง', '3', 1, 5, { when: on('subtitles') }),
    select('subtitleTheme', 'ธีมซับ', subtitleThemes, 'standard', { when: on('subtitles') }),
    select('subtitleAnimation', 'แอนิเมชันซับ', subtitleAnimations, 'none', { when: on('subtitles') }),
    text('subtitleFont', 'ชื่อฟอนต์ที่ต้องการ', { initial: 'Kanit-Bold', when: on('subtitles'), help: 'ชื่อเป็นแบบร่าง ยังไม่ได้ตรวจฟอนต์ที่ติดตั้งหรือเรนเดอร์พรีวิว' }),
    file('subtitleFontFile', 'ไฟล์ฟอนต์เพิ่มเติม', '.ttf,.otf', { when: on('subtitles') }),
    number('subtitleSize', 'ขนาดซับ', '28', 14, 72, { kind: 'range', when: on('subtitles') }),
    number('subtitleMarkGap', 'ช่องไฟสระ–วรรณยุกต์', '14', 0, 20, { kind: 'range', when: on('subtitles') }),
    number('subtitleOutline', 'เส้นขอบซับ', '2', 0, 8, { kind: 'range', when: on('subtitles') }),
    number('subtitleY', 'สูง–ต่ำของซับ (%)', '80', 5, 95, { kind: 'range', when: on('subtitles') }),
    ...[['subtitleTextColor', 'สีข้อความซับ', '#ffffff'], ['subtitleHighlight', 'สีไฮไลต์ซับ', '#facc15'], ['subtitleOutlineColor', 'สีขอบซับ', '#000000'], ['subtitleBackgroundColor', 'สีพื้นหลังซับ', '#000000']].map(([id,label,initial]): Field => ({ id, label, initial, kind: 'color', when: on('subtitles') })),
    { ...toggle('subtitleBackground', 'แสดงพื้นหลังข้อความซับ', true), when: on('subtitles') },
    number('subtitleBackgroundOpacity', 'ความทึบพื้นหลังซับ (%)', '100', 0, 100, { kind: 'range', when: d => d.subtitles === true && d.subtitleBackground === true }),
  ] },
  { id: 'music', step: 3, title: 'เพลงพื้นหลัง', fields: [
    toggle('musicEnabled', 'ใส่เพลงพื้นหลัง'),
    file('musicFiles', 'เลือกเพลงที่จะสุ่มลงคลิป', audioTypes, { when: on('musicEnabled'), required: true, multiple: true }),
    number('musicCount', 'จำนวนเพลงต่อคลิป', '1', 1, 100, { when: on('musicEnabled'), help: 'ไม่เกินจำนวนไฟล์ที่เลือก' }),
    number('musicVolume', 'ระดับเพลง (%)', '15', 3, 35, { kind: 'range', when: on('musicEnabled') }),
    number('musicSegment', 'ท่อนเพลงยาวไม่เกิน (วินาที)', '10', 8, 12, { when: on('musicEnabled') }),
    number('musicDuck', 'ช่วงมีเสียงพูด ลดเพลงเหลือ (%)', '35', 20, 65, { kind: 'range', when: on('musicEnabled') }),
  ] },
  { id: 'sfx', step: 3, title: 'เอฟเฟกต์เสียงเน้นข้อความ', fields: [
    toggle('sfxEnabled', 'ใส่เอฟเฟกต์เสียง'),
    select('sfxMode', 'รูปแบบเอฟเฟกต์เสียง', options('อัตโนมัติ • เว้นจังหวะ', 'สุ่มเสียงทุกจุด', 'เลือกเสียงเดียว'), 'อัตโนมัติ • เว้นจังหวะ', { when: on('sfxEnabled') }),
    file('sfxFiles', 'ไฟล์เอฟเฟกต์เสียง', audioTypes, { when: on('sfxEnabled'), required: true, multiple: true }),
    number('sfxVolume', 'ระดับเอฟเฟกต์เสียง (%)', '25', 5, 60, { kind: 'range', when: on('sfxEnabled') }),
    number('sfxInterval', 'เว้นเอฟเฟกต์อย่างน้อย (วินาที)', '6', 4, 15, { when: on('sfxEnabled') }),
    number('sfxCount', 'จำนวนเอฟเฟกต์สูงสุด', '6', 1, 12, { when: on('sfxEnabled') }),
  ] },
  { id: 'generated-music', step: 3, title: 'ดนตรีจาก AI', fields: [
    toggle('generatedMusic', 'เพิ่มดนตรีคลอบางฉากด้วย AI'),
    select('generatedMusicMood', 'อารมณ์เพลง AI', options('ให้ AI เลือกตามเรื่อง', 'อบอุ่น', 'สดใส', 'ลุ้นเบา ๆ', 'ซึ้ง'), 'ให้ AI เลือกตามเรื่อง', { when: on('generatedMusic') }),
    select('generatedMusicFrequency', 'ความถี่ดนตรี AI', options('น้อย', 'พอดี · ประมาณ 30%'), 'พอดี · ประมาณ 30%', { when: on('generatedMusic') }),
  ] },
  { id: 'automation', step: 3, title: 'การทำงานอัตโนมัติ', fields: [
    toggle('reviewBeforeImages', 'พักให้ตรวจบทก่อนสร้างภาพ'),
    toggle('queueOnly', 'เก็บเข้าคิวไว้ก่อน — ค่อยกดเริ่มที่หน้าคิว'),
  ] },
];

export function choices(field: Field, draft: StoryDraft): readonly Option[] {
  return typeof field.options === 'function' ? field.options(draft) : field.options || [];
}
export function visible(field: Field, draft: StoryDraft) { return !field.when || field.when(draft); }
