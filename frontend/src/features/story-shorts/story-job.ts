import { ApiError } from '../../api';
import type { Transport } from './persistence';

export type StoryJob = { id: string };
export type StartResult = { ok: true; job: StoryJob } | { ok: false; code: string; message?: string; traceId?: string };
type Identity = { id?: string; revision: number };
type StartOptions = { flush: () => Promise<boolean>; identity: () => Identity; send: Transport; key: string | (() => string) };

/** Save the current edit before creating a snapshot; the caller retains the key for uncertain retries. */
export async function startStoryJob({ flush, identity, send, key }: StartOptions): Promise<StartResult> {
  if (!await flush()) return { ok: false, code: 'DRAFT_NOT_SAVED' };
  const { id, revision } = identity();
  if (!id) return { ok: false, code: 'DRAFT_NOT_SAVED' };
  try {
    const job = await send<StoryJob>('/stories', { method: 'POST', headers: { 'Idempotency-Key': typeof key === 'string' ? key : key() },
      body: JSON.stringify({ draft_id: id, expected_revision: revision, mode: 'simulation' }) });
    return { ok: true, job };
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, code: error.code, message: error.message, traceId: error.traceId };
    return { ok: false, code: 'CONNECTION_FAILED' };
  }
}
