import { describe, expect, it, vi } from 'vitest';
import { StoryRunner, SimulatedProvider, safeStorage, type Storage } from './runner';
import { type WorkTask, type WorkData, requestWork } from './work';

function fixture() {
  const values = new Map<string, unknown>();
  const storage: Storage = { get: async key => values.get(key), set: async (key, value) => { values.set(key, value); } };
  const task: WorkTask = { operation_id: crypto.randomUUID(), request_id: crypto.randomUUID(),
    job_id: crypto.randomUUID(), revision_id: crypto.randomUUID(), connection_id: crypto.randomUUID(),
    trace_id: 'trace', lease_epoch: 1, lease_until: 90, mode: 'dispatch', simulation: true, topic: 'PRIVATE' };
  const calls: string[] = [];
  let marked = false, finished = false, loseGrant = false, loseResult = false;
  const call = vi.fn(async (command: Record<string, unknown>) => {
    calls.push(String(command.action));
    const data: WorkData = { task: null, granted: false, lease_until: null, persisted: false, sha256: null };
    if (command.action === 'sync') data.task = finished ? null : { ...task, mode: marked ? 'inspect' : 'dispatch' };
    if (command.action === 'grant') { data.granted = !marked; marked = true; data.lease_until = 90;
      if (loseGrant) { loseGrant = false; throw Error('EXTENSION_DISCONNECTED'); } }
    if (command.action === 'result') { finished = true; data.persisted = true; data.sha256 = 'a'.repeat(64);
      if (loseResult) { loseResult = false; throw Error('EXTENSION_DISCONNECTED'); } }
    return data;
  });
  const provider = new SimulatedProvider(storage);
  const submit = vi.spyOn(provider, 'submit');
  const runner = () => new StoryRunner(call, storage, provider, task.connection_id, () => 10);
  return { values, storage, task, call, calls, provider, submit, runner,
    loseGrant: () => { loseGrant = true; }, loseResult: () => { loseResult = true; } };
}

describe('durable simulated Story runner', () => {
  it('coalesces concurrent ticks and persists exactly one simulated send', async () => {
    const f = fixture(), runner = f.runner();
    await Promise.all([runner.tick(), runner.tick(), runner.tick()]);
    expect(f.calls).toEqual(['sync', 'grant', 'result']);
    expect(f.submit).toHaveBeenCalledTimes(1);
    expect(f.values.get(`operation:${f.task.operation_id}`)).toMatchObject({ state: 'persisted' });
  });
  it('lost grant ACK only inspects after worker restart; never submits', async () => {
    const f = fixture(); f.loseGrant();
    await expect(f.runner().tick()).rejects.toThrow('EXTENSION_DISCONNECTED');
    await f.runner().tick();
    expect(f.calls).toEqual(['sync', 'grant', 'sync', 'missing']); expect(f.submit).not.toHaveBeenCalled();
  });
  it('lost result ACK never repeats an already persisted send', async () => {
    const f = fixture(); f.loseResult();
    await expect(f.runner().tick()).rejects.toThrow(); await f.runner().tick();
    expect(f.submit).toHaveBeenCalledTimes(1); expect(f.calls.filter(x => x === 'grant')).toHaveLength(1);
  });
  it('reconciles a provider result after crash before backend receives it', async () => {
    const f = fixture();
    await f.call({ action: 'grant' }); await f.provider.submit(f.task, () => true); f.submit.mockClear();
    await f.runner().tick(); expect(f.submit).not.toHaveBeenCalled(); expect(f.calls.at(-1)).toBe('result');
  });
  it('checks lease again after asynchronous provider preflight', async () => {
    const f = fixture();
    await expect(f.provider.submit(f.task, () => false)).rejects.toThrow('OPERATION_LEASE_EXPIRED');
    expect(f.values.size).toBe(0);
  });
  it('reports sanitized storage failure without requesting grant', async () => {
    const f = fixture(); const storage = safeStorage({ ...f.storage, get: async () => { throw Error('PRIVATE PATH'); } });
    await new StoryRunner(f.call, storage, new SimulatedProvider(storage), f.task.connection_id, () => 10).tick();
    expect(f.calls).toEqual(['sync', 'blocked']); expect(f.call.mock.calls.at(-1)?.[0].code).toBe('EXTENSION_STORAGE_FAILED');
  });
  it('reports invalid ledger and never overwrites evidence', async () => {
    const f = fixture(); f.values.set(`simulation:${f.task.request_id}`, { text: 'OTHER JOB' });
    await f.runner().tick(); expect(f.calls).toEqual(['sync', 'blocked']); expect(f.submit).not.toHaveBeenCalled();
    expect(f.values.get(`simulation:${f.task.request_id}`)).toEqual({ text: 'OTHER JOB' });
  });
  it('rejects native work responses from a different correlation or helper', async () => {
    await expect(requestWork(async () => ({ protocol_version: 1, message_id: crypto.randomUUID(),
      kind: 'work.result', helper_version: '0.2.0', ok: true, data: {} }), { action: 'sync' })).rejects.toThrow('PROTOCOL_INVALID');
  });
});
