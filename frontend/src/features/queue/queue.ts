import type { JobEvent } from '../../api';

/** Mirrors GET /api/queue. The backend owns order and position; the UI only labels them. */
export type QueueItem = {
  job_id: string; kind: 'story' | 'automation'; title: string; status: string; stage: string;
  error_code: string | null; receipt_state: string | null; queue_position: number | null;
  simulation: true; created_at: number; updated_at: number;
};

export const ACTIVE = new Set(['queued', 'waiting', 'running', 'needs_review']);
export const KIND_LABEL: Record<QueueItem['kind'], string> = { story: 'เรื่องเล่า Shorts', automation: 'งานอัตโนมัติ' };

/** One short Thai line per item, e.g. "กำลังทำงาน", "รออีก 2 งาน", "เสร็จ (จำลอง)". */
export function queueLabel(item: QueueItem): string {
  switch (item.status) {
    case 'running': return 'กำลังทำงาน';
    case 'waiting': return item.error_code === 'EXTENSION_DISCONNECTED' ? 'รอ Extension: เปิด Chrome และตรวจการเชื่อมต่อ' : 'รอดำเนินการ';
    case 'queued': return !item.queue_position ? 'ถัดไป' : `รออีก ${item.queue_position} งาน`;
    case 'needs_review': return 'ไม่แน่ใจว่าส่งแล้วหรือยัง ตรวจผลเดิมก่อน';
    case 'completed': return 'เสร็จ (จำลอง)';
    case 'failed': return `ไม่สำเร็จ${item.error_code ? ` · ${item.error_code}` : ''}`;
    case 'cancelled': return 'ยกเลิกแล้ว';
    default: return item.status;
  }
}

/** Commands the backend accepts for this state; the server still re-checks every one. */
export function queueActions(item: QueueItem): Array<'cancel' | 'reconcile' | 'resume'> {
  if (item.status === 'needs_review') return ['reconcile', 'cancel'];
  if (item.status === 'failed') return ['resume'];
  if (item.status === 'queued' || item.status === 'waiting') return ['cancel'];
  return [];
}

const EVENT_LABEL: Record<string, string> = {
  'story.snapshot_created': 'เข้าคิว (เก็บแบบร่างฉบับนี้ไว้แล้ว)',
  'story.queue_state': 'สถานะคิวเปลี่ยน',
  'story.connection_wait': 'รอการเชื่อมต่อ Extension',
  'story.claimed': 'Extension รับงาน',
  'story.dispatch_marked': 'ส่งงาน (จำลอง) หนึ่งครั้ง',
  'story.result_collected': 'ได้ผลจำลอง',
  'story.artifact_persisted': 'บันทึกไฟล์ผลแล้ว',
  'story.inspect_missing': 'ตรวจแล้วไม่พบผล',
  'story.ownership_released': 'ปล่อยงานให้ Extension ใหม่ตรวจ',
  'story.retry_exhausted': 'ครบจำนวนครั้งที่ลอง',
  'story.agent_blocked': 'Extension หยุดงาน',
  'story.cancel': 'ยกเลิก', 'story.resume': 'ทำต่อ', 'story.reconcile': 'ตรวจผลเดิม',
};

export function eventLabel(event: JobEvent): string {
  return EVENT_LABEL[event.name] || event.name;
}

export function splitQueue(items: QueueItem[], kind?: QueueItem['kind']) {
  const scoped = kind ? items.filter(item => item.kind === kind) : items;
  return { active: scoped.filter(item => ACTIVE.has(item.status)), recent: scoped.filter(item => !ACTIVE.has(item.status)) };
}
