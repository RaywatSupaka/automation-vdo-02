import { ApiError, takeToken } from '../../api';
import { createStoryDraft } from './draft';
import { fieldGroups, type StoryDraft, type StoredAsset } from './fields';

export type SavedDraft = { id: string; revision: number; active_step: number; config: Record<string, string | boolean | string[]> };
export type SaveState = 'loading' | 'load_error' | 'saved' | 'saving' | 'error' | 'conflict';
export type Snapshot = { draft: StoryDraft; step: number; state: SaveState; error: string; generation: number };
type Pending = { path: string; method: string; key: string; body: unknown; version?: number };
export type Transport = <T>(path: string, init?: RequestInit) => Promise<T>;
export function transport(): Transport {
  const token = takeToken(); // Bind requests to the originating session, including retries.
  return async <T>(path: string, init?: RequestInit) => {
    const response = await fetch(`/api${path}`, { ...init, signal: AbortSignal.timeout(60000), headers: {
      Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...init?.headers,
    } });
    const data = await response.json();
    if (!response.ok) throw new ApiError(data.error?.code || 'HTTP_ERROR', data.error?.message || 'บันทึกไม่สำเร็จ', data.error?.trace_id || '');
    return data as T;
  };
}

/** One write at a time. Lost ACK retries the frozen request before advancing revision. */
export class DraftStore {
  value: Snapshot = { draft: createStoryDraft(), step: 0, state: 'loading', error: '', generation: 0 };
  id?: string;
  revision = 0;
  private pending?: Pending;
  private running?: Promise<boolean>;
  private timer?: ReturnType<typeof setTimeout>;
  private version = 0;
  private acknowledged = 0;
  private stopped = false;
  private files = new WeakMap<File, { key: string; asset?: StoredAsset }>();
  constructor(private send: Transport, private notify: (value: Snapshot) => void, private authLost: () => void) {}
  private publish(extra: Partial<Snapshot> = {}) {
    if (!this.stopped) { this.value = { ...this.value, ...extra }; this.notify(this.value); }
  }
  async load() {
    this.publish({ state: 'loading', error: '' });
    try {
      const rows = await this.send<SavedDraft[]>('/story-drafts?limit=1');
      if (this.stopped) return;
      if (rows.length) {
        const saved = await this.send<SavedDraft>(`/story-drafts/${rows[0].id}`);
        const assets = await this.send<StoredAsset[]>(`/story-drafts/${saved.id}/assets`);
        if (this.stopped) return;
        const draft = { ...createStoryDraft(), ...saved.config } as StoryDraft;
        for (const field of fieldGroups.flatMap(g => g.fields).filter(f => f.kind === 'file')) {
          draft[field.id] = (saved.config[field.id] as string[]).map(id => assets.find(asset => asset.id === id)
            || { id, name: 'ไฟล์ที่ไม่พบ', size: 0, missing: true });
        }
        this.id = saved.id; this.revision = saved.revision;
        this.publish({ draft, step: saved.active_step, generation: this.value.generation + 1 });
      }
      this.pending = undefined; this.version = this.acknowledged = 0;
      this.publish({ state: 'saved', error: '' });
    } catch (error) { this.fail(error); if (!this.stopped) this.publish({ state: 'load_error' }); }
  }
  update(draft: StoryDraft, step = this.value.step) {
    if (this.stopped || ['loading', 'load_error'].includes(this.value.state)) return;
    this.version++;
    this.publish({ draft, step });
    if (this.value.state === 'conflict' || this.value.state === 'error') return;
    this.publish({ state: 'saving' });
    clearTimeout(this.timer); this.timer = setTimeout(() => { void this.flush(); }, 350);
  }
  private fail(error: unknown) {
    if (this.stopped) return;
    if (error instanceof ApiError && ['UNAUTHORIZED', 'PERMISSION_DENIED'].includes(error.code)) {
      this.stop(); this.authLost(); return;
    }
    const conflict = error instanceof ApiError && error.code === 'DRAFT_REVISION_CONFLICT';
    this.publish({ state: conflict ? 'conflict' : 'error', error: error instanceof ApiError
      ? `${error.code} · ${error.message} · Trace: ${error.traceId}` : 'เชื่อมต่อเพื่อบันทึกไม่สำเร็จ ข้อมูลยังอยู่ในหน้านี้' });
  }
  private async command(request: Pending) {
    let last: unknown;
    for (let attempt = 0; attempt < 3 && !this.stopped; attempt++) {
      try { return await this.send<SavedDraft>(request.path, { method: request.method,
        headers: { 'Idempotency-Key': request.key }, body: JSON.stringify(request.body) }); }
      catch (error) {
        last = error;
        if (error instanceof ApiError && !['INTERNAL_ERROR', 'DRAFT_SAVE_FAILED'].includes(error.code)) throw error;
      }
    }
    throw last;
  }
  async flush(): Promise<boolean> {
    clearTimeout(this.timer);
    if (this.stopped || this.value.state === 'conflict') return false;
    if (['loading', 'load_error'].includes(this.value.state)) return this.version === this.acknowledged;
    if (this.running) return this.running;
    this.running = this.saveLoop().finally(() => { this.running = undefined; });
    return this.running;
  }
  private async saveLoop() {
    try {
      this.publish({ state: 'saving', error: '' });
      if (!this.id && this.version > this.acknowledged) {
        this.pending ??= { path: '/story-drafts', method: 'POST', key: crypto.randomUUID(), body: {} };
        const created = await this.command(this.pending);
        if (this.stopped) return false;
        this.id = created.id; this.revision = created.revision; this.pending = undefined;
      }
      while (!this.stopped && this.version > this.acknowledged) {
        const version = this.version, draft = this.value.draft, step = this.value.step;
        // Finish uncertain writes before preparing a newer snapshot.
        if (this.pending) {
          const recovered = await this.command(this.pending);
          if (this.stopped) return false;
          this.revision = recovered.revision; this.acknowledged = this.pending.version ?? this.acknowledged; this.pending = undefined;
          if (this.version === this.acknowledged) continue;
        }
        const config: Record<string, string | boolean | string[]> = {};
        for (const [field, value] of Object.entries(draft)) {
          if (!Array.isArray(value)) { config[field] = value; continue; }
          const ids: string[] = [];
          for (const file of value) {
            if (!(file instanceof File)) { ids.push(file.id); continue; }
            const slot = this.files.get(file) || { key: crypto.randomUUID() };
            this.files.set(file, slot);
            if (!slot.asset) {
              for (let attempt = 0; attempt < 3; attempt++) {
                try {
                  slot.asset = await this.send<StoredAsset>(`/story-drafts/${this.id}/assets?field=${field}`, {
                    method: 'POST', headers: { 'Content-Type': 'application/octet-stream', 'Idempotency-Key': slot.key,
                      'X-File-Name': encodeURIComponent(file.name), 'X-File-Size': String(file.size) }, body: file });
                  break;
                } catch (error) {
                  if (this.stopped || attempt === 2 || (error instanceof ApiError &&
                    !['INTERNAL_ERROR', 'DRAFT_SAVE_FAILED', 'DRAFT_ASSET_BUSY'].includes(error.code))) throw error;
                }
              }
            }
            ids.push(slot.asset!.id);
          }
          config[field] = ids;
        }
        if (this.stopped) return false;
        this.pending = { path: `/story-drafts/${this.id}`, method: 'PATCH', key: crypto.randomUUID(),
          body: { config, active_step: step, expected_revision: this.revision }, version };
        const saved = await this.command(this.pending);
        if (this.stopped) return false;
        this.revision = saved.revision; this.pending = undefined; this.acknowledged = version;
      }
      this.publish({ state: 'saved' }); return !this.stopped;
    } catch (error) { this.fail(error); return false; }
  }
  stop() { this.stopped = true; clearTimeout(this.timer); this.value = { ...this.value, draft: createStoryDraft() }; }
}
