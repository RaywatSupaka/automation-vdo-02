import { describe, expect, it } from 'vitest';
import type { Permission } from './api';
import { canOpen, keepIfEqual, permittedView, pollPlan, rememberView, restoreView, stableHealth, storyAccess, VIEW_STORAGE_KEY, viewStorage, workerLabel,
  views } from './navigation';

const owner: Permission[] = ['session:read', 'jobs:read', 'jobs:create', 'jobs:command', 'diagnostics:read',
  'support:export', 'browser:manage', 'stories:drafts:read', 'stories:drafts:write'];
const viewer: Permission[] = ['session:read', 'schema:read', 'jobs:read', 'stories:drafts:read'];
const support: Permission[] = ['session:read', 'schema:read', 'diagnostics:read', 'support:export'];
const operator: Permission[] = ['session:read', 'schema:read', 'jobs:read', 'jobs:create', 'jobs:command',
  'stories:drafts:read', 'stories:drafts:write'];

function memoryStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return { getItem: (key: string) => data.get(key) ?? null, setItem: (key: string, value: string) => { data.set(key, value); }, data };
}
const blocked = {
  getItem: (): string | null => { throw new Error('SecurityError'); },
  setItem: () => { throw new Error('QuotaExceededError'); },
};

describe('view restore', () => {
  it('restores the stored view after a reload and remembers changes', () => {
    const storage = memoryStorage({ [VIEW_STORAGE_KEY]: 'story' });
    expect(restoreView(storage)).toBe('story');
    rememberView(storage, 'logs');
    expect(storage.data.get(VIEW_STORAGE_KEY)).toBe('logs');
    expect(restoreView(storage)).toBe('logs');
  });
  it('falls back to jobs for unknown, missing or blocked storage without throwing', () => {
    expect(restoreView(memoryStorage({ [VIEW_STORAGE_KEY]: 'token=leak' }))).toBe('jobs');
    expect(restoreView(memoryStorage())).toBe('jobs');
    expect(restoreView(null)).toBe('jobs');
    expect(restoreView(blocked)).toBe('jobs');
    expect(() => rememberView(blocked, 'story')).not.toThrow();
    expect(() => rememberView(null, 'story')).not.toThrow();
  });
  it('treats an unavailable storage accessor as no storage', () => {
    expect(viewStorage()).toBeNull(); // Node test runtime has no window, like a blocked accessor.
  });
  it('redirects a stored view the session is not allowed to open', () => {
    const stored = restoreView(memoryStorage({ [VIEW_STORAGE_KEY]: 'story' }));
    expect(permittedView(stored, support)).toBe('database');
    expect(permittedView('browser', viewer)).toBe('jobs');
    expect(permittedView('database', viewer)).toBe('jobs');
    expect(permittedView('story', viewer)).toBe('story');
    expect(permittedView('jobs', ['stories:drafts:read'])).toBe('story');
  });
  it('keeps a stable fallback when nothing is allowed instead of flip-flopping each poll', () => {
    expect(permittedView('jobs', [])).toBe('jobs');
    expect(permittedView(permittedView('database', []), [])).toBe('jobs');
  });
});

describe('view access', () => {
  it('opens Story on draft read permission, not on jobs:create', () => {
    expect(canOpen('story', viewer)).toBe(true);
    expect(canOpen('story', ['jobs:read', 'jobs:create'])).toBe(false);
    expect(canOpen('story', support)).toBe(false);
  });
  it('gates each nav view on its own permission', () => {
    const open = (permissions: Permission[]) => views.filter(view => canOpen(view, permissions));
    expect(open(owner)).toEqual(['jobs', 'database', 'logs', 'story', 'browser']);
    expect(open(operator)).toEqual(['jobs', 'story']);
    expect(open(viewer)).toEqual(['jobs', 'story']);
    expect(open(support)).toEqual(['database', 'logs']);
    expect(open([])).toEqual([]);
  });
  it('mounts the autosaving store for every session that may write drafts', () => {
    expect(storyAccess(owner)).toEqual({ visible: true, mount: true, readOnly: false });
    expect(storyAccess(operator)).toEqual({ visible: true, mount: true, readOnly: false });
  });
  it('shows a read-only notice instead of mounting a store whose saves would be refused', () => {
    // A mounted store can PATCH without an edit (a saved step moved back), so a viewer would be stuck unsaved.
    expect(storyAccess(viewer)).toEqual({ visible: true, mount: false, readOnly: true });
  });
  it('hides Story and mounts nothing without draft read permission', () => {
    expect(storyAccess(support)).toEqual({ visible: false, mount: false, readOnly: false });
    expect(storyAccess(['stories:drafts:write'])).toEqual({ visible: false, mount: false, readOnly: false });
    expect(storyAccess([])).toEqual({ visible: false, mount: false, readOnly: false });
  });
});

describe('poll plan', () => {
  it('does not fetch jobs or events while Story is active', () => {
    expect(pollPlan('story', owner, 'job-1')).toEqual({ view: 'story', jobs: false, events: false, diagnostics: null,
      clearJobs: false, clearDiagnostics: false });
    expect(pollPlan('browser', owner, 'job-1')).toMatchObject({ jobs: false, events: false, diagnostics: null });
  });
  it('fetches jobs, and events only for a selected job, on the jobs view', () => {
    expect(pollPlan('jobs', owner, null)).toMatchObject({ view: 'jobs', jobs: true, events: false });
    expect(pollPlan('jobs', owner, 'job-1')).toMatchObject({ view: 'jobs', jobs: true, events: true });
  });
  it('fetches only the active diagnostics view', () => {
    expect(pollPlan('database', owner, 'job-1')).toMatchObject({ jobs: false, events: false, diagnostics: 'database' });
    expect(pollPlan('logs', owner, null)).toMatchObject({ diagnostics: 'logs' });
  });
  it('redirects a disallowed view without fetching its data and clears revoked rows', () => {
    expect(pollPlan('jobs', support, 'job-1')).toEqual({ view: 'database', jobs: false, events: false, diagnostics: null,
      clearJobs: true, clearDiagnostics: false });
    expect(pollPlan('story', support, null)).toMatchObject({ view: 'database', diagnostics: null });
    expect(pollPlan('logs', viewer, null)).toMatchObject({ view: 'jobs', jobs: false, diagnostics: null, clearDiagnostics: true });
  });
});

describe('poll results', () => {
  it('keeps the previous reference for a duplicate poll response', () => {
    const current = { worker_alive: true, permissions: ['jobs:read'] };
    expect(keepIfEqual(current, { worker_alive: true, permissions: ['jobs:read'] })).toBe(current);
    const changed = { worker_alive: false, permissions: ['jobs:read'] };
    expect(keepIfEqual(current, changed)).toBe(changed);
    const empty: unknown[] = [];
    expect(keepIfEqual(empty, [])).toBe(empty);
    expect(keepIfEqual<object | null>(null, current)).toBe(current);
  });
});

describe('worker status', () => {
  it('separates a live process from a loop that makes progress', () => {
    expect(workerLabel('ready')).toEqual({ text: 'ตัวประมวลผลพร้อม', online: true });
    for (const state of ['starting', 'late', 'stalled', 'down', undefined] as const) expect(workerLabel(state).online).toBe(false);
    expect(workerLabel('stalled').text).toContain('ไม่ตอบสนอง');
  });
  it('drops the per-poll heartbeat age so an unchanged state keeps its reference', () => {
    const first = stableHealth({ worker_state: 'ready', worker_heartbeat_age: 0.2 });
    const second = stableHealth({ worker_state: 'ready', worker_heartbeat_age: 1.4 });
    expect(keepIfEqual(first, second)).toBe(first);
    expect(keepIfEqual(first, stableHealth({ worker_state: 'late', worker_heartbeat_age: 6 }))).not.toBe(first);
  });
});
