import { useEffect, useRef, useState } from 'react';
import { Activity, ArrowRight, Box, CheckCircle2, ChevronRight, CircleDot, Database,
  Download, FileText, Layers3, Plus, RefreshCw, Search, ShieldCheck, X } from 'lucide-react';
import { api, ApiError, downloadBundle, takeToken, type Health, type Job, type JobEvent,
  type Permission, type Session } from './api';
import { actions, statusLabels } from './status';
import { BrandIcon } from './components/BrandIcon';
import { StoryShorts } from './features/story-shorts/StoryShorts';
import { BrowserPairing } from './features/BrowserPairing';

const scenarios = [
  ['success', 'ทำงานสำเร็จ', 'สร้างและบันทึก checkpoint'],
  ['unknown_send', 'ยังไม่ยืนยันการส่ง', 'ตรวจผลเดิมได้ โดยไม่ส่งซ้ำ'],
  ['save_failure', 'บันทึกไฟล์ไม่สำเร็จ', 'ทำต่อเฉพาะขั้นตอนบันทึก'],
  ['transient', 'ไม่พร้อมชั่วคราว', 'ลองใหม่แบบจำกัดก่อนส่ง'],
  ['auth_required', 'ต้องเข้าสู่ระบบ', 'หยุดพร้อมบอกสาเหตุ'],
  ['pending', 'ผลลัพธ์ยังไม่มา', 'สังเกตครบเวลาแล้วพักงาน'],
];

function time(value: number) {
  return new Date(value * 1000).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function App() {
  const [connected, setConnected] = useState(() => !!takeToken());
  const [authEpoch, setAuthEpoch] = useState(0);
  const [token, setToken] = useState('');
  const [view, setView] = useState('jobs');
  const [health, setHealth] = useState<Health | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [message, setMessage] = useState('');
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(false);
  const [title, setTitle] = useState('');
  const [scenario, setScenario] = useState('success');
  const [busy, setBusy] = useState(false);
  const [database, setDatabase] = useState<unknown[]>([]);
  const [logs, setLogs] = useState<unknown[]>([]);
  const [table, setTable] = useState('jobs');
  const commandKey = useRef(crypto.randomUUID());
  const job = jobs.find(j => j.id === selected);
  const can = (permission: Permission) => session?.permissions.includes(permission) ?? false;

  function showError(error: unknown) {
    if (error instanceof ApiError && error.code === 'UNAUTHORIZED') {
      sessionStorage.removeItem('smartflow-session');
      setConnected(false); setSession(null); setHealth(null); setJobs([]); setEvents([]);
      setDatabase([]); setLogs([]); setSelected(null); setModal(false);
    }
    setMessage(error instanceof ApiError ? `${error.code} · ${error.message} · Trace: ${error.traceId}`
      : error instanceof Error ? error.message : 'เกิดข้อผิดพลาดในการเชื่อมต่อ');
  }

  useEffect(() => {
    const changed = () => {
      if (!new URLSearchParams(location.hash.slice(1)).has('token')) return;
      takeToken();
      setSession(null); setHealth(null); setJobs([]); setEvents([]); setDatabase([]); setLogs([]);
      setSelected(null); setModal(false); setMessage(''); setView('jobs');
      setConnected(true); setAuthEpoch(value => value + 1);
    };
    window.addEventListener('hashchange', changed);
    return () => window.removeEventListener('hashchange', changed);
  }, []);
  useEffect(() => { commandKey.current = crypto.randomUUID(); }, [title, scenario]);
  useEffect(() => {
    const lost = () => showError(new ApiError('UNAUTHORIZED', 'สิทธิ์ของ session หมดอายุ', ''));
    window.addEventListener('smartflow-auth-lost', lost);
    return () => window.removeEventListener('smartflow-auth-lost', lost);
  }, []);

  useEffect(() => {
    if (!connected) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      const requestToken = takeToken();
      try {
        const [nextHealth, nextSession] = await Promise.all([api<Health>('/health'), api<Session>('/session')]);
        const readable = nextSession.permissions.includes('jobs:read');
        const inspectable = nextSession.permissions.includes('diagnostics:read');
        const nextJobs = readable ? await api<Job[]>('/jobs') : [];
        const nextEvents = readable && selected ? await api<JobEvent[]>(`/jobs/${selected}/events`) : [];
        const extra = inspectable && view === 'database' ? await api<unknown[]>(`/diagnostics/database/${table}`)
          : inspectable && view === 'logs' ? await api<unknown[]>('/diagnostics/logs') : [];
        if (!stopped && requestToken === takeToken()) {
          setSession(nextSession);
          if (!readable && view === 'jobs') setView('database');
          if (!inspectable && (view === 'database' || view === 'logs')) setView('jobs');
          if (view === 'browser' && !nextSession.permissions.includes('browser:manage')) setView(readable ? 'jobs' : 'database');
          if (view === 'story' && !nextSession.permissions.includes('jobs:create')) setView(readable ? 'jobs' : 'database');
          setHealth(nextHealth); setJobs(nextJobs); setEvents(nextEvents);
          if (view === 'database') setDatabase(extra);
          if (view === 'logs') setLogs(extra);
        }
      } catch (error) { if (!stopped && requestToken === takeToken()) showError(error); }
      finally { if (!stopped) timer = setTimeout(refresh, 1500); }
    }
    void refresh();
    return () => { stopped = true; clearTimeout(timer); };
  }, [connected, selected, view, table, authEpoch]);

  async function createJob(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('');
    try {
      const created = await api<Job>('/jobs', { method: 'POST',
        headers: { 'Idempotency-Key': commandKey.current }, body: JSON.stringify({ title, scenario }) });
      setJobs(current => [created, ...current.filter(j => j.id !== created.id)]);
      setSelected(created.id); setView('jobs'); setModal(false); setTitle('');
    } catch (error) { showError(error); }
    finally { setBusy(false); }
  }

  async function command(action: string) {
    if (!job) return;
    setBusy(true); setMessage('');
    try {
      const updated = await api<Job>(`/jobs/${job.id}/commands/${action}`, { method: 'POST' });
      setJobs(current => current.map(j => j.id === updated.id ? updated : j));
    } catch (error) { showError(error); }
    finally { setBusy(false); }
  }

  if (!connected) return <main className="connection"><div className="connection-card">
    <img className="connection-brand" src="/assets/brand/smartflow-icon.png" alt="SmartFlow AI"/><h1>SmartFlow Next</h1>
    <p>เชื่อมต่อกับโปรแกรมในเครื่องเพื่อดูและจัดการงาน</p>
    {message && <p role="alert">{message}</p>}
    <form onSubmit={event => { event.preventDefault(); sessionStorage.setItem('smartflow-session', token); setConnected(true); }}>
      <label htmlFor="token">Session token สำหรับนักพัฒนา</label>
      <input id="token" type="password" value={token} onChange={e => setToken(e.target.value)} required/>
      <button className="primary">เชื่อมต่อ <ArrowRight size={16}/></button>
    </form><small>เปิดผ่าน SmartFlow Next.exe เพื่อเชื่อมต่ออัตโนมัติ</small>
  </div></main>;

  const available = job ? actions(job.status, job.receipt?.state) : null;
  const filtered = jobs.filter(j => `${j.title} ${j.id}`.toLowerCase().includes(search.toLowerCase()));
  return <div className="shell" data-testid="dashboard">
    <aside className="sidebar">
      <div className="brand"><picture><source media="(max-width: 760px)" srcSet="/assets/brand/smartflow-icon.png"/><img src="/assets/brand/smartflow-logo.png" alt="SmartFlow AI"/></picture></div>
      <div className="workspace"><span className="workspace-icon">S</span><div>พื้นที่ทำงานของฉัน<small>บนเครื่องนี้</small></div><ChevronRight size={16}/></div>
      <p className="nav-label">WORKSPACE</p>
      <nav aria-label="เมนูหลัก">
        {can('browser:manage') && <button className={view === 'browser' ? 'active' : ''} onClick={() => setView('browser')}><ShieldCheck size={19}/>เชื่อมต่อ Extension</button>}
        {[['jobs', 'งานอัตโนมัติ', Box], ['database', 'ตรวจฐานข้อมูล', Database], ['logs', 'บันทึกระบบ', FileText]].map(([key, text, Icon]) => {
          if (!can(key === 'jobs' ? 'jobs:read' : 'diagnostics:read')) return null;
          const Component = Icon as typeof Box;
          return <button key={key as string} className={view === key ? 'active' : ''} onClick={() => setView(key as string)}>
            <Component size={19}/>{text as string}{view === key && <span className="nav-dot"/>}
          </button>;
        })}
        {can('jobs:create') && <button aria-label="เรื่องเล่า Shorts" title="เรื่องเล่า Shorts" className={view === 'story' ? 'active' : ''} onClick={() => setView('story')}><BrandIcon name="story" size={19}/>เรื่องเล่า Shorts{view === 'story' && <span className="nav-dot"/>}</button>}
      </nav>
      <div className="sidebar-bottom"><ShieldCheck size={23}/><strong>ตรวจสอบได้ทุกขั้นตอน</strong>
        <p>สถานะงานและ checkpoint<br/>บันทึกไว้ในเครื่องของคุณ</p>
        <div className="version">FOUNDATION <span>v{health?.version || '0.1.0'}</span></div>
      </div>
    </aside>

    <main className={`main ${view === 'story' ? 'story-main' : ''}`}>
      <header className="topbar"><span>พื้นที่ทำงาน <ChevronRight size={14}/> {view === 'browser' ? 'เชื่อมต่อ Extension' : view === 'story' ? 'เรื่องเล่า Shorts' : view === 'jobs' ? 'งานอัตโนมัติ' : view === 'database' ? 'ฐานข้อมูล' : 'บันทึกระบบ'}</span>
        <span className="connection-status"><i className={health?.worker_alive ? 'online' : ''}/>{health?.worker_alive ? 'ตัวประมวลผลพร้อม' : 'ยังไม่พบตัวประมวลผล'}</span>
      </header>
      <div className="story-host" hidden={view !== 'story'}>{can('jobs:create') && <StoryShorts/>}</div>
      {view === 'browser' && can('browser:manage') && <div className="content"><BrowserPairing/></div>}
      <div className="content" hidden={view === 'story' || view === 'browser'}>
        <div className="page-heading"><div><p className="eyebrow">YOUR AUTOMATION, IN FOCUS</p>
          <h1>{view === 'jobs' ? 'ทุกงาน อยู่ในสายตา' : view === 'database' ? 'ตรวจสอบข้อมูลของระบบ' : 'ลำดับเหตุการณ์ของระบบ'}</h1>
          <p className="subtitle">{view === 'jobs' ? 'สร้างงาน ติดตามผล และทำต่อจากจุดที่บันทึกไว้' : 'ข้อมูลสำหรับวิเคราะห์ปัญหา พร้อมรหัสอ้างอิงที่ติดตามได้'}</p></div>
          {can('jobs:create') && <button className="primary" onClick={() => setModal(true)}><Plus size={18}/>สร้างงานทดสอบ</button>}
        </div>
        <div className="notice"><div className="notice-icon"><Activity size={18}/></div><div><strong>พื้นที่ทดลองระบบอัตโนมัติ</strong>
          <span>รุ่นนี้ใช้ผู้ให้บริการจำลอง เพื่อทดสอบคิวและการกู้คืน ยังไม่เชื่อม AI หรือสร้างวิดีโอจริง</span></div><span className="pill">SIMULATION</span></div>
        {session?.auth_mode === 'dev_bypass' && <p className="inspect-note" data-testid="dev-auth-notice">โหมดพัฒนา · ใช้ตัวตนจำลองและยังตรวจสิทธิ์ทุกคำสั่ง</p>}
        {message && <div className="error-banner" role="alert"><span>{message}</span><button aria-label="ปิดข้อความ" onClick={() => setMessage('')}><X size={16}/></button></div>}

        {view === 'jobs' ? <>
          <section className="stats" aria-label="ภาพรวมงาน">
            {[['งานทั้งหมด', jobs.length, Layers3, 'neutral'], ['กำลังดำเนินการ', jobs.filter(j => ['queued', 'running', 'waiting'].includes(j.status)).length, Activity, 'blue'],
              ['สำเร็จแล้ว', health?.job_counts.completed || 0, CheckCircle2, 'green'],
              ['ต้องดูแล', (health?.job_counts.failed || 0) + (health?.job_counts.needs_review || 0), CircleDot, 'orange']].map(([label, count, Icon, color]) => {
                const Component = Icon as typeof Box;
                return <article className="stat" key={label as string}><span className={`stat-icon ${color}`}><Component size={20}/></span><div><span>{label as string}</span><strong>{count as number}</strong></div></article>;
              })}
          </section>
          <div className="work-grid">
            <section className="panel jobs-panel"><div className="panel-heading"><h2>รายการงาน <span>{jobs.length}</span></h2>
              <label className="search"><Search size={16}/><input aria-label="ค้นหางาน" placeholder="ค้นหาชื่อหรือรหัสงาน" value={search} onChange={e => setSearch(e.target.value)}/></label></div>
              <div className="table-wrap"><table><thead><tr><th>ชื่องาน</th><th>สถานะ</th><th>เวลา</th></tr></thead><tbody>
                {filtered.map(item => <tr key={item.id} className={selected === item.id ? 'selected' : ''}>
                  <td><button className="job-select" onClick={() => setSelected(item.id)}><span className="job-icon"><Box size={17}/></span><span><strong>{item.title}</strong><small>{item.id.slice(0, 8)} · Simulator</small></span></button></td>
                  <td><span className={`status ${item.status}`}>{statusLabels[item.status]}</span></td><td className="muted">{time(item.created_at)}</td>
                </tr>)}
              </tbody></table></div>
              {!filtered.length && <div className="empty"><div className="empty-icon"><Box size={32}/></div><h3>ยังไม่มีงานในรายการ</h3>{can('jobs:create') && <><p>ลองสร้างงานเพื่อดูการทำงานตั้งแต่เริ่ม<br/>จนถึงการบันทึก checkpoint</p><button className="text-button" onClick={() => setModal(true)}>สร้างงานทดสอบ <ArrowRight size={16}/></button></>}</div>}
              <footer className="panel-footer"><span><i className="online"/>อัปเดตสถานะอัตโนมัติ</span><span>แสดงล่าสุดสูงสุด 100 งาน</span></footer>
            </section>
            <section className="panel detail-panel"><div className="panel-heading"><h2>ติดตามงาน</h2><Activity size={18}/></div>
              {job ? <div className="job-detail"><span className={`status ${job.status}`}>{statusLabels[job.status]}</span><h3>{job.title}</h3>
                <dl><dt>รหัสงาน</dt><dd className="mono">{job.id}</dd><dt>ขั้นตอน / สถานะคำขอ</dt><dd>{job.stage} / {job.receipt?.state || 'ยังไม่ส่ง'}</dd><dt>Trace ID</dt><dd className="mono">{job.trace_id}</dd></dl>
                {job.error && <div className="job-error"><strong>{job.error.code}</strong><p>{job.error.message}</p><small>ขั้นตอนต่อไป: {job.error.recovery}</small></div>}
                <div className="job-actions">
                  {can('jobs:command') && available?.resume && <button disabled={busy} onClick={() => command('resume')}><RefreshCw size={15}/>ทำต่อ</button>}
                  {can('jobs:command') && available?.reconcile && <button disabled={busy} onClick={() => command('reconcile')}><Search size={15}/>ตรวจผลเดิม</button>}
                  {can('jobs:command') && available?.cancel && <button disabled={busy} onClick={() => command('cancel')}>ยกเลิกงาน</button>}
                  {can('support:export') && <button onClick={() => downloadBundle(job.id).catch(showError)}><Download size={15}/>ข้อมูลวิเคราะห์</button>}
                </div>
                <h4>ลำดับเหตุการณ์</h4><ol className="timeline">{events.map(event => <li key={event.id}><i/><div><strong>{event.name}</strong><small>{time(event.at)} · {event.stage}</small>{event.code && <code>{event.code}</code>}</div></li>)}</ol>
              </div> : <div className="empty detail-empty"><Activity size={30}/><h3>เห็นที่มาของทุกสถานะ</h3><p>เลือกงานเพื่อดูขั้นตอน<br/>checkpoint และเหตุการณ์ที่เกิดขึ้น</p></div>}
            </section>
          </div>
        </> : <section className="panel inspect-panel"><div className="panel-heading"><h2>{view === 'database' ? 'ข้อมูลสถานะ · อ่านอย่างเดียว' : 'Structured log · ล่าสุด'}</h2>
          {view === 'database' && <select aria-label="ตารางฐานข้อมูล" value={table} onChange={e => setTable(e.target.value)}><option>jobs</option><option>receipts</option><option>events</option></select>}</div>
          <p className="inspect-note">แสดงเฉพาะข้อมูลสำหรับวิเคราะห์ ไม่แสดง token เนื้อหาคำขอ หรือผลลัพธ์ส่วนตัว</p>
          <pre>{JSON.stringify(view === 'database' ? database : logs, null, 2)}</pre></section>}
        <div className="bottom-note"><ShieldCheck size={15}/> บันทึกในเครื่อง · ตรวจสอบย้อนกลับได้ · ทำต่อจาก checkpoint</div>
      </div>
    </main>
    {modal && can('jobs:create') && <div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="create-heading">
      <div className="panel-heading"><h2 id="create-heading">สร้างงานทดสอบ</h2><button aria-label="ปิดหน้าต่าง" disabled={busy} onClick={() => setModal(false)}><X size={20}/></button></div>
      <form onSubmit={createJob}><label htmlFor="job-title">ชื่องาน</label><input autoFocus id="job-title" value={title} onChange={e => setTitle(e.target.value)} placeholder="เช่น ทดสอบการทำงานต่อจาก checkpoint" maxLength={120} required/>
        <label htmlFor="scenario">สถานการณ์จำลอง</label><select id="scenario" value={scenario} onChange={e => setScenario(e.target.value)}>{scenarios.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select>
        <p className="scenario-help">{scenarios.find(s => s[0] === scenario)?.[2]}</p><div className="modal-footer"><button type="button" disabled={busy} onClick={() => setModal(false)}>กลับ</button><button className="primary" disabled={busy || !title.trim()}>{busy ? 'กำลังสร้าง…' : 'เริ่มงานจำลอง'}<ArrowRight size={16}/></button></div>
      </form></section></div>}
  </div>;
}
