import { expect, it, vi } from 'vitest';
import { ApiError } from '../../api';
import { startStoryJob } from './story-job';
import type { Transport } from './persistence';

const id = 'b6dd00f6-1d87-436c-adc2-94f62b56f5f6';
const key = 'same-idempotency-key';

it('does not create a job when the draft flush fails or has no saved id', async () => {
  const send = vi.fn() as Transport;
  expect(await startStoryJob({ flush: async () => false, identity: () => ({ id, revision: 2 }), send, key }))
    .toEqual({ ok: false, code: 'DRAFT_NOT_SAVED' });
  expect(await startStoryJob({ flush: async () => true, identity: () => ({ revision: 0 }), send, key }))
    .toEqual({ ok: false, code: 'DRAFT_NOT_SAVED' });
  expect(send).not.toHaveBeenCalled();
});

it('creates a simulated job from the flushed revision and reuses its key on repeated clicks', async () => {
  const sendMock = vi.fn(async (_path: string, _init?: RequestInit) => ({ id: 'job-1' }));
  const send = sendMock as Transport;
  const flush = vi.fn(async () => true);
  const options = { flush, identity: () => ({ id, revision: 4 }), send, key };
  expect(await startStoryJob(options)).toEqual({ ok: true, job: { id: 'job-1' } });
  expect(await startStoryJob(options)).toEqual({ ok: true, job: { id: 'job-1' } });
  expect(flush).toHaveBeenCalledTimes(2);
  expect(send).toHaveBeenCalledTimes(2);
  for (const [, init] of sendMock.mock.calls) {
    expect(init).toMatchObject({ method: 'POST', headers: { 'Idempotency-Key': key },
      body: JSON.stringify({ draft_id: id, expected_revision: 4, mode: 'simulation' }) });
  }
});

it.each(['DRAFT_REVISION_CONFLICT', 'STORY_DRAFT_INVALID'])('returns the server code and trace for %s', async code => {
  const send = vi.fn(async () => { throw new ApiError(code, 'server message', 'trace-1', 409); }) as Transport;
  expect(await startStoryJob({ flush: async () => true, identity: () => ({ id, revision: 3 }), send, key }))
    .toEqual({ ok: false, code, message: 'server message', traceId: 'trace-1' });
});

it('uses the revision after an asynchronous flush to choose the key', async () => {
  let revision = 1;
  const send = vi.fn(async () => ({ id: 'job-2' })) as Transport;
  const selectedKey = vi.fn(() => `revision-${revision}`);
  await startStoryJob({ flush: async () => { revision = 2; return true; },
    identity: () => ({ id, revision }), send, key: selectedKey });
  expect(send).toHaveBeenCalledWith('/stories', expect.objectContaining({ headers: { 'Idempotency-Key': 'revision-2' } }));
});
