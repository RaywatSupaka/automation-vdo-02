import { afterEach, expect, it, vi } from 'vitest';
import { statusText, watchStoryJob, type StoryView } from './story-status';
import type { Transport } from './persistence';

const view = (status: string, error_code: string | null = null): StoryView => ({
  job_id: 'job-1', status, error_code, result: null, simulation: true, trace_id: 'trace-1',
});
afterEach(() => { vi.useRealTimers(); });

it('labels every Story status and keeps simulation explicit', () => {
  const catalog = { BROWSER_RETRY_EXHAUSTED: { message: 'ครบเวลารอ Extension' } };
  expect(statusText(view('queued'))).toBe('รอเริ่มงานจำลอง');
  expect(statusText(view('waiting', 'EXTENSION_DISCONNECTED'))).toBe('รอ Extension: เปิด Chrome และตรวจการเชื่อมต่อ');
  expect(statusText(view('waiting', 'BROWSER_RETRY_EXHAUSTED'), catalog)).toBe('รอดำเนินงานจำลอง: ครบเวลารอ Extension');
  expect(statusText(view('running'))).toBe('Extension กำลังทำงานจำลอง');
  expect(statusText(view('needs_review'))).toBe('ไม่แน่ใจว่าส่งแล้วหรือยัง ตรวจผลเดิมก่อน');
  expect(statusText(view('completed'))).toBe('เสร็จ (จำลอง)');
  expect(statusText(view('failed', 'BROWSER_RETRY_EXHAUSTED'), catalog)).toBe('ไม่สำเร็จ: ครบเวลารอ Extension');
  expect(statusText(view('cancelled'))).toBe('ยกเลิกแล้ว');
  expect(statusText(view('failed', 'UNKNOWN_CODE'))).toBe('ไม่สำเร็จ: UNKNOWN_CODE');
});

it('polls sequentially every 1500 ms and stops after a terminal status', async () => {
  vi.useFakeTimers();
  const sendMock = vi.fn(async () => sendMock.mock.calls.length === 1 ? view('waiting') : view('completed'));
  const received = vi.fn();
  const stop = watchStoryJob('job-1', sendMock as Transport, received, vi.fn());
  await vi.advanceTimersByTimeAsync(0);
  expect(received).toHaveBeenCalledWith(view('waiting'));
  expect(sendMock).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(1500);
  expect(received).toHaveBeenLastCalledWith(view('completed'));
  await vi.advanceTimersByTimeAsync(4500);
  expect(sendMock).toHaveBeenCalledTimes(2);
  stop();
});

it('cancels pending polling on unmount and bounds transient read failures', async () => {
  vi.useFakeTimers();
  const sendMock = vi.fn(async () => { throw new Error('offline'); });
  const failed = vi.fn();
  const stop = watchStoryJob('job-1', sendMock as Transport, vi.fn(), failed);
  await vi.advanceTimersByTimeAsync(3000);
  expect(sendMock).toHaveBeenCalledTimes(3);
  expect(failed).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(3000);
  expect(sendMock).toHaveBeenCalledTimes(3);
  stop();

  const pending = vi.fn(async () => view('waiting'));
  const cleanup = watchStoryJob('job-2', pending as Transport, vi.fn(), vi.fn());
  await vi.advanceTimersByTimeAsync(0);
  cleanup();
  await vi.advanceTimersByTimeAsync(3000);
  expect(pending).toHaveBeenCalledTimes(1);
});
