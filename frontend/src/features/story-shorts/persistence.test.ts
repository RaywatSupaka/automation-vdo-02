import { expect, it, vi, afterEach } from 'vitest';
import { DraftStore, rejected, transport, type Transport } from './persistence';
import { createStoryDraft } from './draft';
import { ApiError } from '../../api';

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
const id = 'b6dd00f6-1d87-436c-adc2-94f62b56f5f6';
type Call = { path: string; method: string; key?: string; body?: string };
/** Records every request; the handler answers or throws like the transport would. */
function server(handler: (call: Call) => unknown) {
  const calls: Call[] = [];
  const send = vi.fn(async (path: string, init?: RequestInit) => {
    const headers = (init?.headers || {}) as Record<string, string>;
    const call = { path, method: init?.method || 'GET', key: headers['Idempotency-Key'],
      body: typeof init?.body === 'string' ? init.body : undefined };
    calls.push(call);
    return handler(call);
  }) as unknown as Transport;
  return { send, calls, patches: () => calls.filter(call => call.method === 'PATCH') };
}
const body = (call: Call) => JSON.parse(call.body!);
/** Fires the debounce, then waits until the save it started has settled. */
async function debounced(store: DraftStore) {
  await vi.advanceTimersByTimeAsync(350);
  await vi.waitFor(() => expect(store.value.state).not.toBe('saving'));
}

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
  expect(await store.flush()).toBe(false); expect(vi.mocked(send).mock.calls.length).toBe(count);
  store.update({ ...createStoryDraft(), topic: 'still local' });
  expect(store.value.state).toBe('conflict'); expect(await store.flush()).toBe(false);
  expect(vi.mocked(send).mock.calls.length).toBe(count); store.stop();
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

it.each(['DRAFT_ASSET_MISSING', 'DRAFT_ASSET_INVALID', 'IDEMPOTENCY_CONFLICT', 'INPUT_INVALID'])(
  'drops a save rejected with %s and saves the next debounced edit with a new key',
  async code => {
    vi.useFakeTimers();
    let reject = true;
    const { send, patches } = server(call => {
      if (call.method === 'GET') return [];
      if (call.method === 'POST') return { id, revision: 1 };
      if (reject) { reject = false; throw new ApiError(code, 'rejected', 'trace-rejected', 422); }
      return { id, revision: 2 };
    });
    const store = new DraftStore(send, () => {}, () => {}); await store.load();
    store.update({ ...createStoryDraft(), topic: 'rejected value' });
    await debounced(store);
    expect(store.value.state).toBe('error'); expect(store.value.error).toContain(code);
    expect(patches()).toHaveLength(1); // A rejection is final for that request: no immediate retry.
    await vi.advanceTimersByTimeAsync(60000);
    expect(patches()).toHaveLength(1); // No edit, no request: failures never re-arm the debounce.
    store.update({ ...createStoryDraft(), topic: 'fixed' });
    store.update({ ...createStoryDraft(), topic: 'fixed again' });
    expect(store.value).toMatchObject({ state: 'saving', error: '' });
    await debounced(store);
    expect(patches()).toHaveLength(2); // One request for the debounced burst of edits.
    const [stale, fresh] = patches();
    expect(fresh.key).not.toBe(stale.key);
    expect(body(fresh)).toMatchObject({ expected_revision: 1, config: { topic: 'fixed again' } });
    expect(store.value.state).toBe('saved'); expect(store.revision).toBe(2); store.stop();
  });

it('saves an edit made while the in-flight save was being rejected through its own debounce', async () => {
  vi.useFakeTimers();
  let reject!: () => void, first = true;
  const { send, patches } = server(call => {
    if (call.method === 'GET') return [];
    if (call.method === 'POST') return { id, revision: 1 };
    if (!first) return { id, revision: 2 };
    first = false;
    return new Promise((_resolve, fail) => { reject = () => fail(new ApiError('DRAFT_ASSET_INVALID', 'invalid', 'trace', 422)); });
  });
  const store = new DraftStore(send, () => {}, () => {}); await store.load();
  store.update({ ...createStoryDraft(), topic: 'in flight' });
  await vi.advanceTimersByTimeAsync(350);
  await vi.waitFor(() => expect(patches()).toHaveLength(1));
  store.update({ ...createStoryDraft(), topic: 'typed meanwhile' });
  reject();
  await vi.waitFor(() => expect(store.value.state).toBe('error'));
  await debounced(store);
  expect(patches()).toHaveLength(2);
  expect(patches()[1].key).not.toBe(patches()[0].key);
  expect(body(patches()[1])).toMatchObject({ expected_revision: 1, config: { topic: 'typed meanwhile' } });
  expect(store.value.state).toBe('saved'); store.stop();
});

it.each([
  ['a lost connection', () => new TypeError('network ACK lost')],
  ['a timeout', () => new DOMException('timed out', 'TimeoutError')],
  ['INTERNAL_ERROR', () => new ApiError('INTERNAL_ERROR', 'internal', 'trace-internal', 500)],
  ['DRAFT_SAVE_FAILED', () => new ApiError('DRAFT_SAVE_FAILED', 'failed', 'trace-failed', 500)],
  ['a non-JSON 502', () => new ApiError('HTTP_502', 'proxy', 'trace-proxy', 502)],
  ['an unreadable success body', () => new ApiError('HTTP_200', 'unreadable', 'trace-ok', 200)],
])('replays the identical request after %s before saving a later edit', async (_name, failure) => {
  vi.useFakeTimers();
  let failures = 3, revision = 1;
  const { send, patches } = server(call => {
    if (call.method === 'GET') return [];
    if (call.method === 'POST') return { id, revision: 1 };
    if (failures-- > 0) throw failure();
    return { id, revision: ++revision };
  });
  const store = new DraftStore(send, () => {}, () => {}); await store.load();
  store.update({ ...createStoryDraft(), topic: 'maybe committed' });
  expect(await store.flush()).toBe(false);
  expect(store.value.state).toBe('error');
  expect(patches()).toHaveLength(3); // Bounded attempts within one flush.
  await vi.advanceTimersByTimeAsync(60000); expect(patches()).toHaveLength(3);
  store.update({ ...createStoryDraft(), topic: 'later edit' });
  await debounced(store);
  const sent = patches();
  expect(sent).toHaveLength(5);
  for (const replay of sent.slice(1, 4)) expect([replay.key, replay.body]).toEqual([sent[0].key, sent[0].body]);
  expect(sent[4].key).not.toBe(sent[0].key);
  expect(body(sent[4])).toMatchObject({ expected_revision: 2, config: { topic: 'later edit' } });
  expect(store.value.state).toBe('saved'); expect(store.revision).toBe(3); store.stop();
});

it('close flush after a rejection never resends the rejected request', async () => {
  let rejections = 2;
  const { send, patches } = server(call => {
    if (call.method === 'GET') return [];
    if (call.method === 'POST') return { id, revision: 1 };
    if (rejections-- > 0) throw new ApiError('DRAFT_ASSET_MISSING', 'missing', 'trace-missing', 409);
    return { id, revision: 2 };
  });
  const store = new DraftStore(send, () => {}, () => {}); await store.load();
  store.update({ ...createStoryDraft(), topic: 'stale' });
  expect(await store.flush()).toBe(false);
  expect(await store.flush()).toBe(false); // Retry without an edit: one fresh request, not the frozen one.
  store.update({ ...createStoryDraft(), topic: 'edited' });
  expect(await store.flush()).toBe(true); // window.smartflowFlush on close.
  const [stale, retried, saved] = patches();
  expect(patches()).toHaveLength(3);
  expect(new Set([stale.key, retried.key, saved.key]).size).toBe(3);
  expect(body(retried)).toMatchObject({ expected_revision: 1, config: { topic: 'stale' } });
  expect(body(saved)).toMatchObject({ expected_revision: 1, config: { topic: 'edited' } });
  expect(await store.flush()).toBe(true); expect(patches()).toHaveLength(3); // Nothing left unsaved.
  store.stop();
});

it('shows PERMISSION_DENIED with its trace without ending the session; UNAUTHORIZED still does', async () => {
  const authLost = vi.fn(); let denied = true;
  const { send, calls } = server(call => {
    if (call.method === 'GET') return [];
    if (call.method === 'POST' && denied) throw new ApiError('PERMISSION_DENIED', 'no permission', 'trace-denied', 403);
    if (call.method === 'POST') return { id, revision: 1 };
    throw new ApiError('UNAUTHORIZED', 'expired', 'trace-auth', 401);
  });
  const store = new DraftStore(send, () => {}, authLost); await store.load();
  store.update({ ...createStoryDraft(), topic: 'kept' });
  expect(await store.flush()).toBe(false);
  expect(authLost).not.toHaveBeenCalled();
  expect(store.value).toMatchObject({ state: 'error', draft: { topic: 'kept' } });
  expect(store.value.error).toContain('PERMISSION_DENIED'); expect(store.value.error).toContain('trace-denied');
  denied = false;
  store.update({ ...createStoryDraft(), topic: 'kept' });
  expect(store.value.state).toBe('saving'); // Still accepting edits.
  expect(await store.flush()).toBe(false);
  const posts = calls.filter(call => call.method === 'POST');
  expect(posts).toHaveLength(2); expect(posts[1].key).not.toBe(posts[0].key); // Rejected create is not replayed.
  expect(authLost).toHaveBeenCalledTimes(1);
});

it('imports a picked file once and stores a repeated pick once', async () => {
  const asset = '0f7c2a52-8a39-4d55-9a8b-2b8f1c7d3e10';
  const file = new File([new Uint8Array([1, 2, 3])], 'track.mp3');
  const { send, calls, patches } = server(call => {
    if (call.method === 'GET') return [];
    if (call.path.includes('/assets')) return { id: asset, name: 'track.mp3', size: 3 };
    if (call.method === 'POST') return { id, revision: 1 };
    return { id, revision: 2 };
  });
  const store = new DraftStore(send, () => {}, () => {}); await store.load();
  store.update({ ...createStoryDraft(), musicFiles: [file, file] });
  expect(await store.flush()).toBe(true);
  expect(calls.filter(call => call.path.includes('/assets'))).toHaveLength(1);
  expect(body(patches()[0]).config.musicFiles).toEqual([asset]); store.stop();
});

it('stops retrying an uncertain save when the session closes mid-request', async () => {
  let store!: DraftStore;
  const { send, patches } = server(call => {
    if (call.method === 'GET') return [];
    if (call.method === 'POST') return { id, revision: 1 };
    store.stop(); throw new TypeError('connection reset while closing');
  });
  const notify = vi.fn(); store = new DraftStore(send, notify, () => {}); await store.load();
  store.update({ ...createStoryDraft(), topic: 'closing' }); notify.mockClear();
  expect(await store.flush()).toBe(false);
  expect(patches()).toHaveLength(1); expect(notify).toHaveBeenCalledTimes(1); // Only the 'saving' publish.
});

it('transport gives non-JSON and empty error bodies a stable HTTP code and keeps the trace', async () => {
  vi.stubGlobal('location', { hash: '', pathname: '/' });
  vi.stubGlobal('sessionStorage', { getItem: () => 'fixture-session', setItem: () => {} });
  const fetch = vi.fn()
    .mockResolvedValueOnce(new Response('<html>Bad Gateway</html>', { status: 502, headers: { 'X-Trace-ID': 'trace-proxy' } }))
    .mockResolvedValueOnce(new Response('', { status: 404 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: 'DRAFT_ASSET_MISSING', message: 'gone',
      trace_id: 'trace-body' } }), { status: 409, headers: { 'X-Trace-ID': 'trace-header' } }))
    .mockResolvedValueOnce(new Response('{"revision":', { status: 200, headers: { 'X-Trace-ID': 'trace-cut' } }));
  vi.stubGlobal('fetch', fetch);
  const send = transport();
  const errors = [];
  for (let i = 0; i < 4; i++) errors.push(await send('/story-drafts').catch((error: unknown) => error));
  expect(errors.map(e => e instanceof ApiError && [e.code, e.traceId, e.status])).toEqual([
    ['HTTP_502', 'trace-proxy', 502], ['HTTP_404', '', 404], ['DRAFT_ASSET_MISSING', 'trace-body', 409],
    ['HTTP_200', 'trace-cut', 200]]);
  expect(errors.map(rejected)).toEqual([false, true, true, false]); // 5xx and unreadable ACKs may have committed.
  expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer fixture-session');
  expect(fetch.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
});

it('saves other fields once per edit when a picked file is refused, without re-uploading it', async () => {
  vi.useFakeTimers();
  const asset = '0f7c2a52-8a39-4d55-9a8b-2b8f1c7d3e10';
  const bad = new File([new Uint8Array([1, 2, 3])], 'not-audio.mp3'), good = new File([new Uint8Array([4])], 'ok.mp3');
  let revision = 1;
  const { send, calls, patches } = server(call => {
    if (call.method === 'GET') return [];
    if (call.path.includes('/assets')) {
      if (imports().length === 1) throw new ApiError('DRAFT_ASSET_INVALID', 'bad file', 'trace-file', 422);
      return { id: asset, name: 'ok.mp3', size: 1 };
    }
    if (call.method === 'POST') return { id, revision: 1 };
    return { id, revision: ++revision };
  });
  const imports = () => calls.filter(call => call.path.includes('/assets'));
  const store = new DraftStore(send, () => {}, () => {}); await store.load();
  store.update({ ...createStoryDraft(), topic: 'first', musicFiles: [bad] });
  await debounced(store);
  expect(imports()).toHaveLength(1); // A refusal is final for that File: no immediate retry.
  expect(patches()).toHaveLength(1);
  expect(body(patches()[0]).config).toMatchObject({ topic: 'first', musicFiles: [] });
  expect(store.value.state).toBe('error');
  expect(store.value.error).toContain('DRAFT_ASSET_INVALID'); expect(store.value.error).toContain('trace-file');
  store.update({ ...createStoryDraft(), topic: 'second', musicFiles: [bad] });
  await debounced(store);
  expect(imports()).toHaveLength(1); expect(patches()).toHaveLength(2); // Exactly one PATCH, no re-upload.
  expect(body(patches()[1])).toMatchObject({ expected_revision: 2, config: { topic: 'second', musicFiles: [] } });
  expect(store.value.state).toBe('error');
  await vi.advanceTimersByTimeAsync(60000);
  expect(await store.flush()).toBe(false); // Close flush: the refused pick is still unsaved, nothing is sent.
  expect(calls.filter(call => call.method !== 'GET')).toHaveLength(4);
  store.update({ ...createStoryDraft(), topic: 'second', musicFiles: [good] }); // Picking again is a new File.
  await debounced(store);
  expect(imports()).toHaveLength(2); expect(imports()[1].key).not.toBe(imports()[0].key);
  expect(body(patches()[2]).config.musicFiles).toEqual([asset]);
  expect(store.value.state).toBe('saved'); expect(await store.flush()).toBe(true); store.stop();
});

it('retries a busy import with its stable key on the next edit instead of recording it as refused', async () => {
  vi.useFakeTimers();
  const file = new File([new Uint8Array([1])], 'track.mp3');
  let busy = 3;
  const { send, calls, patches } = server(call => {
    if (call.method === 'GET') return [];
    if (call.path.includes('/assets')) {
      if (busy-- > 0) throw new ApiError('DRAFT_ASSET_BUSY', 'busy', 'trace-busy', 409);
      return { id: 'asset-1', name: 'track.mp3', size: 1 };
    }
    if (call.method === 'POST') return { id, revision: 1 };
    return { id, revision: 2 };
  });
  const store = new DraftStore(send, () => {}, () => {}); await store.load();
  store.update({ ...createStoryDraft(), musicFiles: [file] });
  await debounced(store);
  expect(store.value.error).toContain('DRAFT_ASSET_BUSY'); expect(patches()).toHaveLength(0);
  store.update({ ...createStoryDraft(), topic: 'edit', musicFiles: [file] });
  await debounced(store);
  const imports = calls.filter(call => call.path.includes('/assets'));
  expect(imports).toHaveLength(4); expect(new Set(imports.map(call => call.key)).size).toBe(1);
  expect(body(patches()[0]).config.musicFiles).toEqual(['asset-1']); expect(store.value.state).toBe('saved'); store.stop();
});

it.each([
  ['rejected', () => new ApiError('DRAFT_ASSET_INVALID', 'invalid', 'trace', 422), 1],
  ['lost after bounded retries', () => new TypeError('network ACK lost'), 3],
])('saves an edit typed during a slow save whose debounce fired before the save was %s', async (_name, failure, failed) => {
  vi.useFakeTimers();
  let settle!: () => void, failures = failed, revision = 1;
  const { send, patches } = server(call => {
    if (call.method === 'GET') return [];
    if (call.method === 'POST') return { id, revision: 1 };
    if (failures === failed) { failures--; return new Promise((_resolve, fail) => { settle = () => fail(failure()); }); }
    if (failures-- > 0) throw failure();
    return { id, revision: ++revision };
  });
  const store = new DraftStore(send, () => {}, () => {}); await store.load();
  store.update({ ...createStoryDraft(), topic: 'slow' });
  await vi.advanceTimersByTimeAsync(350);
  await vi.waitFor(() => expect(patches()).toHaveLength(1));
  store.update({ ...createStoryDraft(), topic: 'typed meanwhile' });
  await vi.advanceTimersByTimeAsync(1000); // Its debounce fires into the still-running save.
  expect(patches()).toHaveLength(1);
  settle();
  await vi.waitFor(() => expect(store.value.state).toBe('error'));
  expect(patches()).toHaveLength(failed);
  await debounced(store);
  const sent = patches(), fresh = sent[sent.length - 1];
  // A lost ACK replays the identical request first; a rejection was dropped and is never resent.
  expect(sent).toHaveLength(failed === 1 ? 2 : failed + 2);
  for (const replay of sent.slice(1, -1)) expect([replay.key, replay.body]).toEqual([sent[0].key, sent[0].body]);
  expect(fresh.key).not.toBe(sent[0].key);
  expect(body(fresh)).toMatchObject({ config: { topic: 'typed meanwhile' } });
  expect(store.value.state).toBe('saved');
  await vi.advanceTimersByTimeAsync(60000); expect(patches()).toHaveLength(sent.length); store.stop();
});
