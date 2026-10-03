import type { Transport } from './persistence';

export type StoryView = { job_id: string; status: string; error_code: string | null; result: string | null;
  simulation: true; trace_id: string };
export type ErrorCatalog = Record<string, { message: string }>;
const terminal = new Set(['completed', 'failed', 'cancelled']);

export function statusText(view: StoryView, catalog: ErrorCatalog = {}): string {
  const error = view.error_code ? catalog[view.error_code]?.message || view.error_code : '';
  switch (view.status) {
    case 'queued': return 'รอเริ่มงานจำลอง';
    case 'waiting': return view.error_code === 'EXTENSION_DISCONNECTED'
      ? 'รอ Extension: เปิด Chrome และตรวจการเชื่อมต่อ' : `รอดำเนินงานจำลอง${error ? `: ${error}` : ''}`;
    case 'running': return 'Extension กำลังทำงานจำลอง';
    case 'needs_review': return 'ไม่แน่ใจว่าส่งแล้วหรือยัง ตรวจผลเดิมก่อน';
    case 'completed': return 'เสร็จ (จำลอง)';
    case 'failed': return `ไม่สำเร็จ: ${error || 'ตรวจรหัสงานและลองใหม่'}`;
    case 'cancelled': return 'ยกเลิกแล้ว';
    default: return 'กำลังตรวจสถานะงานจำลอง';
  }
}

/** Poll one job with a bounded local retry. A terminal state or unmount stops the timer. */
export function watchStoryJob(id: string, send: Transport, onView: (view: StoryView) => void,
  onFailure: (error: unknown) => void): () => void {
  let stopped = false, failures = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let request: AbortController | undefined;
  async function refresh() {
    request = new AbortController();
    try {
      const view = await send<StoryView>(`/stories/${id}`, { signal: request.signal });
      if (stopped) return;
      failures = 0; onView(view);
      if (terminal.has(view.status)) return;
    } catch (error) {
      if (stopped) return;
      if (++failures >= 3) { onFailure(error); return; }
    }
    timer = setTimeout(() => { void refresh(); }, 1500);
  }
  void refresh();
  return () => { stopped = true; clearTimeout(timer); request?.abort(); };
}
