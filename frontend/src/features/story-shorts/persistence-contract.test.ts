import { readFileSync } from 'node:fs';
import { afterEach, expect, it, vi } from 'vitest';
import { choices, fieldGroups, visible, type StoredAsset, type StoryDraft } from './fields';
import { createStoryDraft, validateStoryStep } from './draft';
import { DraftStore, type DraftIssue, type Transport } from './persistence';
import { ApiError } from '../../api';
import { issueNotice, issueSummary } from './StoryShorts';

type Spec = {
  kind: string; initial: unknown; maxLength?: number; options?: string[]; min?: number; max?: number; step?: number;
  required?: boolean; when?: { field: string; equals: string | boolean }; maxLines?: number; maxCountOf?: string;
  optionsUpTo?: { field: string; fixed: string[] };
};
// The backend registry is the source of truth; the UI schema must not drift from it.
const registry: Record<string, Spec> = JSON.parse(readFileSync(new URL('../../../../backend/smartflow/draft_fields.json', import.meta.url), 'utf8'));
const fields = fieldGroups.flatMap(group => group.fields);
const active = (spec: Spec, draft: StoryDraft) => !spec.when || draft[spec.when.field] === spec.when.equals;
/** The initial draft plus one draft per value each checkbox or static select can take. */
const probes: StoryDraft[] = [createStoryDraft(), ...Object.entries(registry).flatMap(([id, spec]) =>
  (spec.kind === 'checkbox' ? [true, false] : spec.options || []).map(value => ({ ...createStoryDraft(), [id]: value })))];
const asset = (n: number): StoredAsset => ({ id: `asset-${n}`, name: `track-${n}.mp3`, size: 1 });
afterEach(() => { vi.useRealTimers(); });

it('draft persistence contract covers every UI field without dropping hidden settings', () => {
  expect(Object.keys(registry).sort()).toEqual(fields.map(field => field.id).sort());
  for (const field of fields) {
    expect(registry[field.id].kind).toBe(field.kind);
    expect(registry[field.id].initial).toEqual(field.initial);
    if (field.maxLength) expect(registry[field.id].maxLength).toBe(field.maxLength);
  }
});

it('UI options, min, max and step match the backend registry', () => {
  for (const field of fields) {
    const spec = registry[field.id];
    if (spec.options) expect(choices(field, createStoryDraft()).map(([key]) => key), field.id).toEqual(spec.options);
    else expect(typeof field.options === 'function' || !field.options, field.id).toBe(true);
    expect({ min: field.min, max: field.max, step: field.step }, field.id).toEqual({ min: spec.min, max: spec.max, step: spec.step });
  }
});

it('UI required and conditional rules match the backend registry', () => {
  for (const field of fields) {
    const spec = registry[field.id];
    expect(Boolean(field.required), field.id).toBe(Boolean(spec.required));
    if (!spec.required && !spec.when) continue;
    for (const draft of probes) expect(visible(field, draft) && !field.disabled, `${field.id} ${JSON.stringify(spec.when)}`).toBe(active(spec, draft));
  }
});

it('UI cross-field limits match the backend registry', () => {
  const limit = registry.batchTopics.maxLines!;
  const batch = (count: number) => ({ ...createStoryDraft(), creationMode: 'batch',
    batchTopics: Array.from({ length: count }, (_, n) => `topic ${n}`).join('\n') });
  expect(validateStoryStep(batch(limit), 0)).toBeNull();
  expect(validateStoryStep(batch(limit + 1), 0)).not.toBeNull();

  const files = registry.musicCount.maxCountOf!;
  const music = { ...createStoryDraft(), [registry.musicCount.when!.field]: true, [files]: [asset(1), asset(2)] };
  expect(validateStoryStep({ ...music, musicCount: '2' }, 3)).toBeNull();
  expect(validateStoryStep({ ...music, musicCount: '3' }, 3)).not.toBeNull();

  const source = registry.coverScene.optionsUpTo!, cover = fields.find(field => field.id === 'coverScene')!;
  // Same table as SCENE_OPTION_COUNTS in tests/unit/test_draft_rules.py: both sides must parse these alike.
  const counts: Record<string, number> = { '0': 0, '1': 1, '8': 8, '15': 15, '40': 15, x: 0, '': 0, ' 8 ': 8, '8.9': 8,
    '1e1': 10, '1e999': 15, Infinity: 15, '-Infinity': 0, '0x8': 8, '1_0': 0, '１０': 0 };
  for (const [scenes, count] of Object.entries(counts)) {
    expect(choices(cover, { ...createStoryDraft(), [source.field]: scenes }).map(([key]) => key), scenes)
      .toEqual([...source.fixed, ...Array.from({ length: count }, (_, n) => String(n + 1))]);
  }
  // A count the UI cannot parse never trips the music limit, on either side.
  expect(validateStoryStep({ ...music, musicCount: '1_0' }, 3)).not.toMatch(/ไม่เกินจำนวนไฟล์/);
});

const id = 'b6dd00f6-1d87-436c-adc2-94f62b56f5f6';

it('server issues from load and each acknowledged save reach the snapshot', async () => {
  vi.useFakeTimers();
  const loaded: DraftIssue[] = [{ field: 'topic', code: 'FIELD_REQUIRED' }, { field: 'logoFile', code: 'DRAFT_ASSET_MISSING' }];
  const acked: DraftIssue[] = [{ field: 'musicFiles', code: 'FIELD_REQUIRED' }];
  let revision = 1, lostAck = true, reject = false;
  const patches: string[] = [];
  const send = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.startsWith('/story-drafts?')) return [{ id }];
    if (path.endsWith('/assets')) return [];
    if (!init?.method) return { id, revision, active_step: 0, config: createStoryDraft(), issues: loaded };
    patches.push(init.body as string);
    if (reject) throw new ApiError('INPUT_INVALID', 'invalid', 'trace');
    revision++;
    // The first ACK is lost after commit; the identical retry gets the stored response.
    if (lostAck) { lostAck = false; throw new TypeError('network ACK lost'); }
    return { id, revision, active_step: 0, config: createStoryDraft(), issues: acked };
  }) as unknown as Transport;
  const notify = vi.fn();
  const store = new DraftStore(send, notify, () => {});
  expect(store.value.issues).toBeUndefined();
  await store.load();
  expect(store.value.issues).toEqual(loaded);

  store.update({ ...store.value.draft, topic: 'ready', musicEnabled: true });
  expect(store.value.issues).toEqual(loaded); // An unsaved edit never claims the server's verdict.
  expect(await store.flush()).toBe(true);
  expect(patches).toHaveLength(2); expect(patches[0]).toBe(patches[1]);
  expect(store.value.issues).toEqual(acked);
  expect(notify.mock.lastCall![0]).toMatchObject({ state: 'saved', issues: acked }); // What the UI renders.

  reject = true;
  store.update({ ...store.value.draft, topic: 'rejected edit' });
  expect(await store.flush()).toBe(false);
  expect(store.value.issues).toEqual(acked); // A rejected save keeps the last acknowledged issues.
  store.stop();
});

it('summarises server issues in Thai by field label and asks to replace a missing file', () => {
  expect(issueSummary()).toEqual([]);
  expect(issueSummary([
    { field: 'topic', code: 'FIELD_REQUIRED' }, { field: 'musicFiles', code: 'FIELD_REQUIRED' },
    { field: 'logoFile', code: 'DRAFT_ASSET_MISSING' }, { field: 'logoFile', code: 'DRAFT_ASSET_MISSING' },
  ])).toEqual(['ยังไม่ได้ระบุ: หัวข้อคลิป, เลือกเพลงที่จะสุ่มลงคลิป', 'ไฟล์ที่บันทึกไว้หาย กรุณาเลือกไฟล์ใหม่แทน: รูปโลโก้']);
  const many = ['topic', 'scenes', 'videoMode', 'imageProvider', 'musicFiles'].map(field => ({ field, code: 'FIELD_REQUIRED' }));
  expect(issueSummary(many)).toEqual(['ยังไม่ได้ระบุ: หัวข้อคลิป, จำนวนฉาก, เปลี่ยนภาพเป็นวิดีโอด้วย และอีก 2 รายการ']);
});

it('labels server issues as the last-saved verdict while the screen holds unsaved or rejected edits', () => {
  const topic: DraftIssue[] = [{ field: 'topic', code: 'FIELD_REQUIRED' }];
  expect(issueNotice('saved', topic)).toEqual({ lines: ['ยังไม่ได้ระบุ: หัวข้อคลิป'], stale: '' });
  for (const state of ['saving', 'error', 'conflict'] as const) {
    const notice = issueNotice(state, topic);
    expect(notice.lines, state).toEqual(['ยังไม่ได้ระบุ: หัวข้อคลิป']);
    expect(notice.stale, state).toMatch(/บันทึกครั้งล่าสุด/);
  }
  expect(issueNotice('error', [])).toEqual({ lines: [], stale: '' }); // Nothing to label, nothing shown.
  expect(issueNotice('loading')).toEqual({ lines: [], stale: '' });
});
