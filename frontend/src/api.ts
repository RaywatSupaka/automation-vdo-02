export type Job = {
  id: string; title: string; scenario: string; status: string; stage: string; trace_id: string;
  attempts: number; has_artifact: boolean; created_at: number;
  receipt: { state: string; request_id: string } | null;
  error: { code: string; message: string; recovery: string; trace_id: string } | null;
};
export type JobEvent = { id: number; at: number; name: string; stage: string; code: string | null };
export type Health = { version: string; database: string; schema_revision: string;
  worker_alive: boolean; mode: string; job_counts: Record<string, number>; events: number };
export type Permission = 'session:read' | 'schema:read' | 'jobs:read' | 'jobs:create'
  | 'jobs:command' | 'diagnostics:read' | 'support:export' | 'stories:drafts:read' | 'stories:drafts:write' | 'browser:manage';
export type Session = { actor_id: string; role: 'owner' | 'operator' | 'viewer' | 'support';
  auth_mode: 'local_session' | 'dev_bypass'; permissions: Permission[] };

export function takeToken(): string {
  const fragment = new URLSearchParams(location.hash.slice(1));
  const token = fragment.get('token');
  if (token) {
    sessionStorage.setItem('smartflow-session', token);
    history.replaceState(null, '', location.pathname);
  }
  return sessionStorage.getItem('smartflow-session') || '';
}

/** `status` is the HTTP status of the response that produced the error, or 0 when there was none. */
export class ApiError extends Error {
  constructor(public code: string, message: string, public traceId: string, public status = 0) { super(message); }
}

export const REQUEST_TIMEOUT_MS = 60000;
/** Every API request is bounded; a caller signal can still cancel it earlier. */
export function requestSignal(signal?: AbortSignal | null): AbortSignal {
  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  return signal ? AbortSignal.any([signal, timeout]) : timeout;
}

type ErrorBody = { error?: { code?: unknown; message?: unknown; trace_id?: unknown } };
const text = (value: unknown) => typeof value === 'string' ? value : '';

/**
 * Parses a JSON API response. An error without a structured body, or a success body that cannot be read,
 * becomes `HTTP_<status>` so callers always get a stable code and the trace header when it is present.
 */
export async function readJson<T>(response: Response, fallback: string): Promise<T> {
  let data: unknown, readable = true;
  try { data = JSON.parse(await response.text()); } catch { readable = false; }
  if (response.ok && readable) return data as T;
  const error = readable && data && typeof data === 'object' ? (data as ErrorBody).error : undefined;
  const code = (!response.ok && text(error?.code)) || `HTTP_${response.status}`;
  throw new ApiError(code, text(error?.message) || fallback,
    text(error?.trace_id) || response.headers.get('X-Trace-ID') || '', response.status);
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { ...init, signal: requestSignal(init?.signal), headers: {
    Authorization: `Bearer ${takeToken()}`, 'Content-Type': 'application/json', ...init?.headers,
  } });
  return readJson<T>(response, 'เชื่อมต่อไม่สำเร็จ');
}

export async function downloadBundle(jobId: string) {
  const response = await fetch(`/api/jobs/${jobId}/support-bundle`, {
    headers: { Authorization: `Bearer ${takeToken()}` },
  });
  if (!response.ok) throw new Error('ส่งออกข้อมูลวิเคราะห์ไม่สำเร็จ');
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url; link.download = `smartflow-${jobId.slice(0, 8)}.zip`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
