import { useEffect, useState } from 'react';
import { api, ApiError, type JobEvent } from '../../api';
import { eventLabel, KIND_LABEL, queueActions, queueLabel, splitQueue, type QueueItem } from './queue';
import './queue.css';

type StoryResult = { status: string; result: string | null };
type Props = { kind?: QueueItem['kind']; compact?: boolean; canCommand: boolean };
const ACTION_LABEL = { cancel: 'ยกเลิก', reconcile: 'ตรวจผลเดิม', resume: 'ลองใหม่' } as const;

/** One queue view for every feature: unfinished work in FIFO order, then recent results. Poll-only, read model. */
export function QueuePanel({ kind, compact = false, canCommand }: Props) {
  const [items, setItems] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState<string | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [result, setResult] = useState<StoryResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const next = await api<QueueItem[]>(`/queue?recent=${compact ? 5 : 30}`);
        if (!stopped) { setItems(next); setError(''); }
      } catch (failure) {
        if (!stopped) setError(failure instanceof ApiError ? `${failure.code} · Trace: ${failure.traceId}` : 'อ่านคิวงานไม่สำเร็จ');
      } finally { if (!stopped) timer = setTimeout(poll, 1500); }
    }
    void poll();
    return () => { stopped = true; clearTimeout(timer); };
  }, [compact, tick]);

  const selected = items?.find(item => item.job_id === open) || null;
  useEffect(() => {
    if (!selected) { setEvents([]); setResult(null); return; }
    let stopped = false;
    void api<JobEvent[]>(`/jobs/${selected.job_id}/events`).then(rows => { if (!stopped) setEvents(rows); }).catch(() => undefined);
    if (selected.kind === 'story' && selected.status === 'completed') {
      void api<StoryResult>(`/stories/${selected.job_id}`).then(view => { if (!stopped) setResult(view); }).catch(() => undefined);
    } else setResult(null);
    return () => { stopped = true; };
  }, [selected?.job_id, selected?.status, selected?.updated_at]);

  async function command(item: QueueItem, action: keyof typeof ACTION_LABEL) {
    setBusy(true); setError('');
    try { await api(`/jobs/${item.job_id}/commands/${action}`, { method: 'POST' }); setTick(value => value + 1); }
    catch (failure) { setError(failure instanceof ApiError ? `${failure.code} · ${failure.message} · Trace: ${failure.traceId}` : 'ส่งคำสั่งไม่สำเร็จ'); }
    finally { setBusy(false); }
  }

  const { active, recent } = splitQueue(items || [], kind);
  const row = (item: QueueItem) => <li key={item.job_id} className={`queue-item is-${item.status}`}>
    <button type="button" className="queue-row" aria-expanded={open === item.job_id}
      onClick={() => setOpen(current => current === item.job_id ? null : item.job_id)}>
      <span className="queue-title">{item.title || item.job_id.slice(0, 8)}</span>
      {!kind && <span className="queue-kind">{KIND_LABEL[item.kind]}</span>}
      <span className="queue-state" role="status">{queueLabel(item)}</span>
    </button>
    {open === item.job_id && <div className="queue-detail">
      <span className="pill">SIMULATION</span>
      <ol className="queue-timeline" aria-label="ความคืบหน้า">{events.map(event => <li key={event.id}>
        <span>{eventLabel(event)}</span><small>{new Date(event.at * 1000).toLocaleTimeString('th-TH')}{event.code ? ` · ${event.code}` : ''}</small>
      </li>)}</ol>
      {result?.result && <pre className="queue-result">{result.result}</pre>}
      {canCommand && queueActions(item).length > 0 && <div className="queue-actions">{queueActions(item).map(action =>
        <button key={action} type="button" disabled={busy} onClick={() => void command(item, action)}>{ACTION_LABEL[action]}</button>)}</div>}
    </div>}
  </li>;

  return <section className={`queue-panel${compact ? ' is-compact' : ''}`} aria-label="คิวงาน">
    <header><h2>คิวงาน{kind ? ` · ${KIND_LABEL[kind]}` : ''}</h2><span>{active.length} งานที่ยังไม่จบ</span></header>
    {error && <p role="alert" className="queue-error">{error}</p>}
    {items === null ? <p className="queue-empty">กำลังอ่านคิวงาน…</p> : <>
      {active.length === 0 ? <p className="queue-empty">ไม่มีงานค้างในคิว</p> : <ol className="queue-list" aria-label="งานที่ยังไม่จบ">{active.map(row)}</ol>}
      {recent.length > 0 && <><h3>งานล่าสุด</h3><ol className="queue-list" aria-label="งานล่าสุด">{recent.map(row)}</ol></>}
    </>}
  </section>;
}
