import { expect, it, vi, afterEach } from 'vitest';
import { DraftStore, type Transport } from './persistence';
import { createStoryDraft } from './draft';
import { ApiError } from '../../api';

afterEach(() => vi.useRealTimers());
const id = 'b6dd00f6-1d87-436c-adc2-94f62b56f5f6';
it('coalesces edits and retries an uncertain save with the same key and body', async () => {
  const calls: RequestInit[] = []; let once = true;
  const send = vi.fn(async (path: string, init?: RequestInit) => {
    if (!init) return [];
    if (init.method === 'POST') return { id, revision: 1 };
    calls.push(init);
    if (once) { once = false; throw new TypeError('network ACK lost'); }
    return { id, revision: 2 };
  }) as Transport;
  const store = new DraftStore(send, () => {}, () => {}); await store.load();
  store.update({ ...createStoryDraft(), topic: 'first' });
  store.update({ ...createStoryDraft(), topic: 'latest' });
  expect(await store.flush()).toBe(true);
  expect(calls).toHaveLength(2);
  expect(calls[0].headers).toEqual(calls[1].headers);
  expect(calls[0].body).toBe(calls[1].body);
  expect(JSON.parse(calls[1].body as string).config.topic).toBe('latest'); store.stop();
});
it('preserves local work on conflict and never advances until explicitly resolved', async () => {
  const send = vi.fn(async (_path: string, init?: RequestInit) => {
    if (!init) return [];
    if (init.method === 'POST') return { id, revision: 1 };
    throw new ApiError('DRAFT_REVISION_CONFLICT', 'conflict', 'trace');
  }) as Transport;
  const store = new DraftStore(send, () => {}, () => {}); await store.load();
  store.update({ ...createStoryDraft(), topic: 'keep me' });
  expect(await store.flush()).toBe(false);
  expect(store.value.state).toBe('conflict'); expect(store.value.draft.topic).toBe('keep me');
  const count = vi.mocked(send).mock.calls.length;
  expect(await store.flush()).toBe(false); expect(vi.mocked(send).mock.calls.length).toBe(count); store.stop();
});
it('does not replace a failed initial load with an empty saved draft', async () => {
  const send = vi.fn(async () => { throw new TypeError('offline'); }) as Transport;
  const store = new DraftStore(send, () => {}, () => {}); await store.load();
  expect(store.value.state).toBe('load_error');
  store.update({ ...createStoryDraft(), topic: 'cannot edit before load' });
  expect(store.value.draft.topic).toBe(''); expect(send).toHaveBeenCalledTimes(1); store.stop();
});
it('does not publish late responses after the originating session is closed', async () => {
  let resolve!: (value: unknown) => void;
  const send = vi.fn(() => new Promise(r => { resolve = r; })) as Transport;
  const notify = vi.fn(); const store = new DraftStore(send, notify, () => {});
  const pending = store.load(); store.stop(); notify.mockClear(); resolve([]); await pending;
  expect(notify).not.toHaveBeenCalled();
});
