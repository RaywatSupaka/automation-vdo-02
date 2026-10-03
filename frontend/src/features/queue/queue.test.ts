import { describe, expect, it } from 'vitest';
import { eventLabel, queueActions, queueLabel, splitQueue, type QueueItem } from './queue';

const item = (status: string, extra: Partial<QueueItem> = {}): QueueItem => ({
  job_id: status, kind: 'story', title: status, status, stage: 'prepare', error_code: null, receipt_state: 'prepared',
  queue_position: null, simulation: true, created_at: 1, updated_at: 1, ...extra,
});

describe('queue labels', () => {
  it('describes position and the one actionable waiting reason', () => {
    expect(queueLabel(item('queued', { queue_position: 0 }))).toBe('ถัดไป');
    expect(queueLabel(item('queued', { queue_position: 2 }))).toBe('รออีก 2 งาน');
    expect(queueLabel(item('waiting', { error_code: 'EXTENSION_DISCONNECTED' }))).toContain('รอ Extension');
    expect(queueLabel(item('running'))).toBe('กำลังทำงาน');
    expect(queueLabel(item('completed'))).toBe('เสร็จ (จำลอง)');
    expect(queueLabel(item('failed', { error_code: 'BROWSER_RETRY_EXHAUSTED' }))).toContain('BROWSER_RETRY_EXHAUSTED');
  });
  it('offers only commands the state allows; uncertain sends are never resumed', () => {
    expect(queueActions(item('needs_review'))).toEqual(['reconcile', 'cancel']);
    expect(queueActions(item('failed'))).toEqual(['resume']);
    expect(queueActions(item('queued'))).toEqual(['cancel']);
    expect(queueActions(item('running'))).toEqual([]);
    expect(queueActions(item('completed'))).toEqual([]);
  });
  it('splits active from finished work and filters by feature', () => {
    const items = [item('running'), item('completed'), item('queued', { kind: 'automation' })];
    expect(splitQueue(items, 'story')).toEqual({ active: [items[0]], recent: [items[1]] });
    expect(splitQueue(items).active).toHaveLength(2);
  });
  it('labels known events and keeps unknown names visible', () => {
    expect(eventLabel({ id: 1, at: 0, name: 'story.dispatch_marked', stage: 'generate', code: null })).toContain('หนึ่งครั้ง');
    expect(eventLabel({ id: 2, at: 0, name: 'job.created', stage: 'prepare', code: null })).toBe('job.created');
  });
});
