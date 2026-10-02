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

export class ApiError extends Error {
  constructor(public code: string, message: string, public traceId: string) { super(message); }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { ...init, headers: {
    Authorization: `Bearer ${takeToken()}`, 'Content-Type': 'application/json', ...init?.headers,
  } });
  const data = await response.json();
  if (!response.ok) throw new ApiError(data.error?.code || 'HTTP_ERROR',
    data.error?.message || 'เชื่อมต่อไม่สำเร็จ', data.error?.trace_id || '');
  return data as T;
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
