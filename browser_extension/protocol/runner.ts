import { type WorkData, type WorkTask } from './work';

export interface Storage { get(key: string): Promise<unknown>; set(key: string, value: unknown): Promise<void>; }
export type Ledger = { request_id: string; operation_id: string; revision_id: string; text: string; sends: number };
export interface Provider { inspect(task: WorkTask): Promise<Ledger | undefined>; submit(task: WorkTask, valid: () => boolean): Promise<Ledger>; }
export type WorkCall = (command: Record<string, unknown>) => Promise<WorkData>;

/** Simulation ledger is independent of the agent journal; no external provider is called. */
export class SimulatedProvider implements Provider {
  constructor(private storage: Storage) {}
  async inspect(task: WorkTask) {
    const value = await this.storage.get(`simulation:${task.request_id}`) as Ledger | undefined;
    if (value && (value.request_id !== task.request_id || value.operation_id !== task.operation_id ||
      value.revision_id !== task.revision_id || value.text !== `[SIMULATION ONLY]\n${task.topic}` || value.sends !== 1))
      throw Error('STORY_RESULT_INVALID');
    return value;
  }
  async submit(task: WorkTask, valid: () => boolean) {
    // The fixture provider has a durable deduplication ledger. This does not imply web providers have one.
    const existing = await this.inspect(task); if (existing) return existing;
    const result = { request_id: task.request_id, operation_id: task.operation_id, revision_id: task.revision_id,
      text: `[SIMULATION ONLY]\n${task.topic}`, sends: 1 };
    if (!valid()) throw Error("OPERATION_LEASE_EXPIRED");
    await this.storage.set(`simulation:${task.request_id}`, result);
    return result;
  }
}

export class StoryRunner {
  private active?: Promise<void>;
  constructor(private call: WorkCall, private storage: Storage, private provider: Provider,
    private connection: string, private now = () => Date.now() / 1000) {}
  tick(): Promise<void> {
    if (this.active) return this.active;
    this.active = this.run().finally(() => { this.active = undefined; });
    return this.active;
  }
  private async run() {
    const data = await this.call({ action: 'sync', connection_id: this.connection,
      extension_version: '0.2.0', helper_version: '0.2.0', capability: 'story_simulator_v1' });
    const task = data.task; if (!task) return;
    if (task.connection_id !== this.connection || !task.simulation || task.lease_until <= this.now())
      throw Error('OPERATION_LEASE_EXPIRED');
    const owned = { connection_id: this.connection, operation_id: task.operation_id,
      request_id: task.request_id, lease_epoch: task.lease_epoch };
    const key = `operation:${task.operation_id}`;
    try {
    let result = await this.provider.inspect(task);
    if (!result && task.mode === 'dispatch') {
      // Preflight succeeded. Intent is durable before requesting one-time dispatch authority.
      await this.storage.set(key, { state: 'intent', request_id: task.request_id, revision_id: task.revision_id });
      const grant = await this.call({ action: 'grant', ...owned });
      if (grant.granted && grant.lease_until && grant.lease_until > this.now()) {
        result = await this.provider.submit(task, () => grant.lease_until! > this.now());
      }
      // A lost/negative grant is never retried in this execution. Next sync can only inspect after marker.
    }
    if (!result) {
      if (task.mode === 'inspect') await this.call({ action: 'missing', ...owned });
      return;
    }
    await this.storage.set(key, { state: 'collected', request_id: task.request_id, revision_id: task.revision_id });
    const saved = await this.call({ action: 'result', ...owned, result: result.text });
    if (saved.persisted) await this.storage.set(key, { state: 'persisted', request_id: task.request_id,
      revision_id: task.revision_id, sha256: saved.sha256 });
    } catch (error) {
      if (error instanceof Error && ['EXTENSION_STORAGE_FAILED', 'STORY_RESULT_INVALID'].includes(error.message)) {
        await this.call({ action: 'blocked', ...owned, code: error.message });
        return;
      }
      throw error; // Transport failure is reconciled by the next heartbeat, never by repeating the grant.
    }
  }
}

/** Raw browser storage errors may contain private values. Normalize at the boundary. */
export function safeStorage(storage: Storage): Storage {
  return {
    async get(key) { try { return await storage.get(key); } catch { throw Error('EXTENSION_STORAGE_FAILED'); } },
    async set(key, value) { try { await storage.set(key, value); } catch { throw Error('EXTENSION_STORAGE_FAILED'); } },
  };
}
