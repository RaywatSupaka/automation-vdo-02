import type { Permission, WorkerState } from './api';

/** Fallback order matters: a disallowed view lands on the first allowed one, so polls never flip-flop. */
export const views = ['jobs', 'database', 'logs', 'story', 'browser'] as const;
export type View = typeof views[number];
export const VIEW_STORAGE_KEY = 'smartflow-view';
const required: Record<View, Permission> = {
  jobs: 'jobs:read', database: 'diagnostics:read', logs: 'diagnostics:read',
  story: 'stories:drafts:read', browser: 'browser:manage',
};
type ViewStorage = Pick<Storage, 'getItem' | 'setItem'>;

export function isView(value: unknown): value is View {
  return typeof value === 'string' && (views as readonly string[]).includes(value);
}

/** The one gate for opening a view: nav buttons and the poll fallback both use it. */
export function canOpen(view: View, permissions: readonly Permission[]): boolean {
  return permissions.includes(required[view]);
}

export function permittedView(view: View, permissions: readonly Permission[]): View {
  if (canOpen(view, permissions)) return view;
  return views.find(candidate => canOpen(candidate, permissions)) ?? 'jobs';
}

export type StoryAccess = { visible: boolean; mount: boolean; readOnly: boolean };

/**
 * Readers see the Story view; only writers mount the autosaving store. The store can write without a user
 * edit (StepWizard moves a saved step back past a now-invalid step and reports it), and a refused write
 * leaves flush() false forever, which would block the desktop close guard. Every session that may write
 * mounts the store, so a missing window.smartflowFlush still means nothing is unsaved.
 */
export function storyAccess(permissions: readonly Permission[]): StoryAccess {
  const visible = canOpen('story', permissions);
  const mount = visible && permissions.includes('stories:drafts:write');
  return { visible, mount, readOnly: visible && !mount };
}

/** Per-tab convenience only. Never the URL fragment: takeToken() owns #token. */
export function viewStorage(): ViewStorage | null {
  try { return window.sessionStorage; } catch { return null; }
}

/** Permission fallback is applied by the first session poll via pollPlan(). */
export function restoreView(storage: ViewStorage | null): View {
  try {
    const stored = storage?.getItem(VIEW_STORAGE_KEY);
    return isView(stored) ? stored : 'jobs';
  } catch { return 'jobs'; }
}

export function rememberView(storage: ViewStorage | null, view: View) {
  try { storage?.setItem(VIEW_STORAGE_KEY, view); } catch { /* blocked storage keeps the in-memory view */ }
}

export type PollPlan = { view: View; jobs: boolean; events: boolean; diagnostics: 'database' | 'logs' | null;
  clearJobs: boolean; clearDiagnostics: boolean };

/** /health and /session are always polled; view data only while that view is active and allowed. */
export function pollPlan(view: View, permissions: readonly Permission[], selected: string | null): PollPlan {
  const target = permittedView(view, permissions);
  const settled = target === view; // A redirect re-runs the poll for the new view at once.
  const readable = permissions.includes('jobs:read');
  const inspectable = permissions.includes('diagnostics:read');
  const jobs = settled && view === 'jobs' && readable;
  return { view: target, jobs, events: jobs && !!selected,
    diagnostics: settled && inspectable && (view === 'database' || view === 'logs') ? view : null,
    clearJobs: !readable, clearDiagnostics: !inspectable };
}

/** Topbar label for the worker: process alive is not the same as a loop that is making progress. */
export function workerLabel(state: WorkerState | undefined): { text: string; online: boolean } {
  switch (state) {
    case 'ready': return { text: 'ตัวประมวลผลพร้อม', online: true };
    case 'starting': return { text: 'ตัวประมวลผลกำลังเริ่ม', online: false };
    case 'late': return { text: 'ตัวประมวลผลตอบช้า', online: false };
    case 'stalled': return { text: 'ตัวประมวลผลไม่ตอบสนอง กำลังเริ่มใหม่', online: false };
    default: return { text: 'ยังไม่พบตัวประมวลผล', online: false };
  }
}

/** Health without the per-poll heartbeat age, so an unchanged state does not re-render every poll. */
export function stableHealth<T extends { worker_heartbeat_age?: unknown }>(health: T): Omit<T, 'worker_heartbeat_age'> {
  const { worker_heartbeat_age: _age, ...rest } = health;
  return rest;
}

/** Keep the previous reference when a poll returns identical data, so React skips the re-render. */
export function keepIfEqual<T>(current: T, next: T): T {
  return JSON.stringify(current) === JSON.stringify(next) ? current : next;
}
