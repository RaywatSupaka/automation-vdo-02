import { ApiError, readJson, requestSignal, takeToken } from '../../api';
import { createStoryDraft } from './draft';
import { fieldGroups, type StoryDraft, type StoredAsset } from './fields';

/** A server-reported problem with the saved config; reported only, the draft is still saved. */
export type DraftIssue = { field: string; code: string };
export type SavedDraft = { id: string; revision: number; active_step: number; config: Record<string, string | boolean | string[]>; issues: DraftIssue[] };
export type SaveState = 'loading' | 'load_error' | 'saved' | 'saving' | 'error' | 'conflict';
/** `issues` are those of the newest config the server acknowledged; absent until the first load. */
export type Snapshot = { draft: StoryDraft; step: number; state: SaveState; error: string; generation: number; issues?: DraftIssue[] };
type Pending = { path: string; method: string; key: string; body: unknown; version?: number };
export type Transport = <T>(path: string, init?: RequestInit) => Promise<T>;
export function transport(): Transport {
  const token = takeToken(); // Bind requests to the originating session, including retries.
  return async <T>(path: string, init?: RequestInit) => {
    const response = await fetch(`/api${path}`, { ...init, signal: requestSignal(init?.signal), headers: {
      Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...init?.headers,
    } });
    return readJson<T>(response, 'บันทึกไม่สำเร็จ');
  };
}

const ATTEMPTS = 3;
const UNCERTAIN = ['INTERNAL_ERROR', 'DRAFT_SAVE_FAILED'];
/**
 * True when the server rejected the request. For a draft POST/PATCH (one transaction) nothing was committed,
 * so the frozen request must be dropped rather than replayed. Lost connections, timeouts, unreadable bodies,
 * unstructured 5xx/408/429 and the uncertain codes may have committed, so they replay the identical request.
 * An asset import is not one transaction (see imported()), so this says nothing about what it committed.
 */
export function rejected(error: unknown): boolean {
  if (!(error instanceof ApiError) || UNCERTAIN.includes(error.code)) return false;
  if (!error.code.startsWith('HTTP_')) return true; // Structured AppError body.
  return error.status >= 400 && error.status < 500 && error.status !== 408 && error.status !== 429;
}
/** Session-level or transient import errors: the file itself was not refused, so a later save may retry it. */
const NOT_FILE_REFUSAL = ['UNAUTHORIZED', 'PERMISSION_DENIED', 'DRAFT_ASSET_BUSY'];

/**
 * One write at a time. A lost ACK retries the frozen request (same key and body) before advancing revision;
 * a rejection drops it so the next save is a fresh snapshot. Only edits arm the debounce, so a failing save
 * never loops: at most one save per debounced change, each with bounded retries. A refused file import is
 * left out of the config, so the other fields still save while the store reports the refusal.
 */
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
  private files = new WeakMap<File, { key: string; asset?: StoredAsset; refused?: ApiError }>();
  constructor(private send: Transport, private notify: (value: Snapshot) => void, private authLost: () => void) {}
  private publish(extra: Partial<Snapshot> = {}) {
    if (!this.stopped) { this.value = { ...this.value, ...extra }; this.notify(this.value); }
  }
  async load() {
    this.publish({ state: 'loading', error: '' });
    try {
      const rows = await this.send<SavedDraft[]>('/story-drafts?limit=1');
      if (this.stopped) return;
      if (rows.length) await this.open(await this.send<SavedDraft>(`/story-drafts/${rows[0].id}`));
      if (this.stopped) return;
      this.pending = undefined; this.version = this.acknowledged = 0;
      this.publish({ state: 'saved', error: '' });
    } catch (error) { this.fail(error); if (!this.stopped) this.publish({ state: 'load_error' }); }
  }
  private async open(saved: SavedDraft, step = saved.active_step) {
    const assets = await this.send<StoredAsset[]>(`/story-drafts/${saved.id}/assets`);
    if (this.stopped) return;
    const draft = { ...createStoryDraft(), ...saved.config } as StoryDraft;
    for (const field of fieldGroups.flatMap(g => g.fields).filter(f => f.kind === 'file')) {
      draft[field.id] = (saved.config[field.id] as string[]).map(id => assets.find(asset => asset.id === id)
        || { id, name: 'ไฟล์ที่ไม่พบ', size: 0, missing: true });
    }
    this.id = saved.id; this.revision = saved.revision;
    this.publish({ draft, step, generation: this.value.generation + 1, issues: saved.issues });
  }
  /** After a job start the server creates the next draft (settings kept, story content reset); open it at step 1.
   *  The same key replays the same draft after a lost ACK; a refused request leaves the current draft open. */
  async next(key: string): Promise<boolean> {
    if (this.stopped || !this.id || !await this.flush()) return false;
    const source = this.id;
    try {
      const created = await this.attempt(() => this.send<SavedDraft>(`/story-drafts/${source}/successor`,
        { method: 'POST', headers: { 'Idempotency-Key': key } }), error => !rejected(error));
      await this.open(created, 0);
      if (this.stopped) return false;
      this.pending = undefined; this.version = this.acknowledged = 0;
      this.publish({ state: 'saved', error: '' });
      return true;
    } catch (error) { this.fail(error); return false; }
  }
  update(draft: StoryDraft, step = this.value.step) {
    if (this.stopped || ['loading', 'load_error'].includes(this.value.state)) return;
    this.version++;
    this.publish({ draft, step });
    if (this.value.state === 'conflict') return;
    // An edit after a failed save may have fixed its cause, so it schedules the normal debounced save.
    this.publish({ state: 'saving', error: '' });
    this.schedule();
  }
  /** Keeps the server's issues for the newest acknowledged write; the loop's final publish carries them. */
  private acknowledge(saved: SavedDraft) { if (!this.stopped) this.value = { ...this.value, issues: saved.issues }; }
  private schedule() { clearTimeout(this.timer); this.timer = setTimeout(() => { void this.flush(); }, 350); }
  private fail(error: unknown) {
    if (this.stopped) return;
    // Only a lost session ends the store; a denied permission is an error the user can read and report.
    if (error instanceof ApiError && error.code === 'UNAUTHORIZED') { this.stop(); this.authLost(); return; }
    const conflict = error instanceof ApiError && error.code === 'DRAFT_REVISION_CONFLICT';
    this.publish({ state: conflict ? 'conflict' : 'error', error: error instanceof ApiError
      ? `${error.code} · ${error.message} · Trace: ${error.traceId}` : 'เชื่อมต่อเพื่อบันทึกไม่สำเร็จ ข้อมูลยังอยู่ในหน้านี้' });
  }
  /** Bounded immediate retries of one idempotent request; a non-retryable error is final for it. */
  private async attempt<T>(request: () => Promise<T>, retryable: (error: unknown) => boolean): Promise<T> {
    for (let attempt = 1; ; attempt++) {
      try { return await request(); }
      catch (error) { if (this.stopped || attempt >= ATTEMPTS || !retryable(error)) throw error; }
    }
  }
  private async command(request: Pending) {
    try {
      return await this.attempt(() => this.send<SavedDraft>(request.path, { method: request.method,
        headers: { 'Idempotency-Key': request.key }, body: JSON.stringify(request.body) }), error => !rejected(error));
    } catch (error) {
      // Nothing was committed, so the next save must be a fresh snapshot with a new key and revision.
      if (rejected(error) && this.pending === request) this.pending = undefined;
      throw error;
    }
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
    let tried = this.version; // Newest edit that a request of this loop has covered.
    try {
      this.publish({ state: 'saving', error: '' });
      if (!this.id && this.version > this.acknowledged) {
        this.pending ??= { path: '/story-drafts', method: 'POST', key: crypto.randomUUID(), body: {} };
        const created = await this.command(this.pending);
        if (this.stopped) return false;
        this.id = created.id; this.revision = created.revision; this.pending = undefined; this.acknowledge(created);
      }
      while (!this.stopped && this.version > this.acknowledged) {
        // Finish an uncertain write before preparing a newer snapshot.
        if (this.pending) {
          const recovered = await this.command(this.pending);
          if (this.stopped) return false;
          this.revision = recovered.revision; this.acknowledged = this.pending.version ?? this.acknowledged; this.pending = undefined;
          this.acknowledge(recovered);
          continue;
        }
        const version = tried = this.version, step = this.value.step;
        const config = await this.config(this.value.draft);
        if (this.stopped) return false;
        this.pending = { path: `/story-drafts/${this.id}`, method: 'PATCH', key: crypto.randomUUID(),
          body: { config, active_step: step, expected_revision: this.revision }, version };
        const saved = await this.command(this.pending);
        if (this.stopped) return false;
        this.revision = saved.revision; this.pending = undefined; this.acknowledged = version; this.acknowledge(saved);
      }
      const refused = this.refused();
      if (refused) { this.fail(refused); return false; } // Other fields saved; the refused pick is not.
      this.publish({ state: 'saved' }); return !this.stopped;
    } catch (error) {
      this.fail(error);
      // An edit typed while this request was failing was never sent, and its debounce already fired into the
      // running loop. Give it one normal debounced save; it needs a newer edit, so failures never loop.
      if (!this.stopped && this.value.state === 'error' && this.version > tried) this.schedule();
      return false;
    }
  }
  /** The refusal of a picked File still in the draft; that File cannot be saved until it is replaced. */
  private refused() {
    for (const value of Object.values(this.value.draft)) {
      if (!Array.isArray(value)) continue;
      for (const file of value) { const refused = file instanceof File && this.files.get(file)?.refused; if (refused) return refused; }
    }
  }
  /** Builds the config the server stores, importing each new File once and leaving refused Files out. */
  private async config(draft: StoryDraft) {
    const config: Record<string, string | boolean | string[]> = {};
    for (const [field, value] of Object.entries(draft)) {
      if (!Array.isArray(value)) { config[field] = value; continue; }
      const ids: string[] = [];
      for (const file of value) {
        const id = file instanceof File ? (await this.imported(field, file))?.id : file.id;
        if (id && !ids.includes(id)) ids.push(id); // The server rejects a repeated id; store the file once.
      }
      config[field] = ids;
    }
    return config;
  }
  /**
   * One stable import key per File, so retries and later saves never import the same pick twice. The key is
   * never rotated, even after a refusal: an import commits a reserved row before streaming and can then be
   * refused, so a new key would leak reservations against the draft quota. A refused File is recorded and
   * never re-uploaded; picking the file again makes a new File and so a new attempt.
   */
  private async imported(field: string, file: File): Promise<StoredAsset | undefined> {
    const slot = this.files.get(file) || { key: crypto.randomUUID() };
    this.files.set(file, slot);
    if (slot.asset || slot.refused) return slot.asset;
    try {
      slot.asset = await this.attempt(() => this.send<StoredAsset>(`/story-drafts/${this.id}/assets?field=${field}`, {
        method: 'POST', headers: { 'Content-Type': 'application/octet-stream', 'Idempotency-Key': slot.key,
          'X-File-Name': encodeURIComponent(file.name), 'X-File-Size': String(file.size) }, body: file }),
      error => !rejected(error) || (error instanceof ApiError && error.code === 'DRAFT_ASSET_BUSY'));
    } catch (error) {
      if (!rejected(error) || !(error instanceof ApiError) || NOT_FILE_REFUSAL.includes(error.code)) throw error;
      slot.refused = error;
    }
    return slot.asset;
  }
  stop() { this.stopped = true; clearTimeout(this.timer); this.value = { ...this.value, draft: createStoryDraft() }; }
}
