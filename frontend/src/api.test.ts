import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, ApiError, REQUEST_TIMEOUT_MS } from './api';

beforeEach(() => {
  vi.stubGlobal('location', { hash: '', pathname: '/' });
  vi.stubGlobal('sessionStorage', { getItem: () => 'fixture-session', setItem: () => {} });
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
const reply = (response: Response) => { const fetch = vi.fn().mockResolvedValue(response); vi.stubGlobal('fetch', fetch); return fetch; };
const failure = (response: Response) => { reply(response); return api('/jobs').catch((error: unknown) => error); };

it('bounds every request with the shared timeout and still honours a caller abort', async () => {
  const timeout = vi.spyOn(AbortSignal, 'timeout');
  const fetch = vi.fn(async (_url: string, _init: RequestInit) => new Response('[]', { status: 200 }));
  vi.stubGlobal('fetch', fetch);
  expect(await api('/jobs')).toEqual([]);
  expect(timeout).toHaveBeenCalledWith(REQUEST_TIMEOUT_MS); expect(REQUEST_TIMEOUT_MS).toBe(60000);
  const caller = new AbortController();
  await api('/jobs', { signal: caller.signal });
  const signal = fetch.mock.calls[1][1].signal!;
  expect(signal.aborted).toBe(false); caller.abort(); expect(signal.aborted).toBe(true);
  expect((fetch.mock.calls[0][1].headers as Record<string, string>).Authorization).toBe('Bearer fixture-session');
});

it.each([
  ['a plain-text 500', new Response('Internal Server Error', { status: 500, headers: { 'X-Trace-ID': 'trace-500' } }), ['HTTP_500', 'trace-500']],
  ['an empty 503', new Response(null, { status: 503 }), ['HTTP_503', '']],
  ['JSON without an error code', new Response('{"detail":"Method Not Allowed"}', { status: 405 }), ['HTTP_405', '']],
  ['an unreadable success body', new Response('<html>', { status: 200, headers: { 'X-Trace-ID': 'trace-200' } }), ['HTTP_200', 'trace-200']],
])('reports %s as a stable HTTP code with the trace header', async (_name, response, [code, trace]) => {
  const error = await failure(response);
  expect(error).toBeInstanceOf(ApiError);
  expect(error).toMatchObject({ code, traceId: trace, status: response.status, message: 'เชื่อมต่อไม่สำเร็จ' });
});

it('keeps the structured code, message and body trace of an AppError response', async () => {
  const error = await failure(new Response(JSON.stringify({ error: { code: 'PERMISSION_DENIED', message: 'denied',
    trace_id: 'trace-body' } }), { status: 403, headers: { 'X-Trace-ID': 'trace-header' } }));
  expect(error).toMatchObject({ code: 'PERMISSION_DENIED', message: 'denied', traceId: 'trace-body', status: 403 });
});
