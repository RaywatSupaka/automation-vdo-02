import { useEffect, useState } from 'react';
import { api, ApiError } from '../api';

type Pair = { id: string; extension_id: string; state: string; connected: boolean };
type Info = { extension_id: string; extension_version: string; helper_version: string; pairings: Pair[] };
export function expectedVersions(info: Pick<Info, 'extension_version' | 'helper_version'>) {
  return `Extension ${info.extension_version} · helper ${info.helper_version}`;
}
export function BrowserPairing() {
  const [info, setInfo] = useState<Info | null>(null);
  const [code, setCode] = useState<{ code: string; expires_at: number } | null>(null);
  const [error, setError] = useState('');
  const refresh = async () => { setInfo(await api<Info>('/browser')); };
  const report = (e: unknown) => setError(e instanceof ApiError ? `${e.code} · ${e.message} · Trace: ${e.traceId}` : 'เชื่อมต่อไม่สำเร็จ');
  useEffect(() => { let alive = true; const update = async () => {
    try { const value = await api<Info>('/browser'); if (alive) setInfo(value); } catch(e) { if(alive) report(e); }
  }; void update(); const timer = setInterval(update, 5000); return () => { alive = false; clearInterval(timer); }; }, []);
  return <section className="panel inspect-panel"><div className="panel-heading"><h2>เชื่อมต่อ Extension</h2><span>{info && expectedVersions(info)}</span></div>
    <div style={{ padding: 24 }}><p>ใช้ SmartFlow Next Extension รุ่นใหม่ แล้วนำรหัสด้านล่างไปใส่ใน popup เพื่อจับคู่กับโปรแกรมนี้</p>
      <p>Extension ID: <code>{info?.extension_id}</code></p>
      <p>รุ่นที่โปรแกรมคาดหวัง: {info ? expectedVersions(info) : 'กำลังตรวจสอบ…'}</p>
      <p>หากรุ่นที่ติดตั้งไม่ตรง ให้ build helper รุ่นนี้และ Reload SmartFlow Next Extension ตามคู่มือติดตั้ง</p>
      <p>งาน Story ในรุ่นนี้ให้ผลจำลองเท่านั้น · SIMULATION</p>
      {error && <p role="alert">{error}</p>}
      <button className="primary" disabled={!info} onClick={async () => { try { setError('');
        setCode(await api('/browser/pairings', { method: 'POST', body: JSON.stringify({ extension_id: info!.extension_id }) })); await refresh();
      } catch(e) { report(e); } }}>สร้างรหัสจับคู่</button>
      {code && Date.now() < code.expires_at * 1000 && <div><p>รหัสใช้ครั้งเดียว · หมดอายุภายใน 2 นาที</p>
        <input aria-label="รหัสจับคู่ Extension" value={code.code} readOnly onFocus={e => e.target.select()}/></div>}
      <ul>{info?.pairings.filter(pair => pair.state === 'paired').map(pair => <li key={pair.id}>
        {pair.connected ? 'เชื่อมต่ออยู่' : 'จับคู่แล้ว · ยังไม่พบการเชื่อมต่อ'}{' '}
        <button onClick={async () => { try { await api(`/browser/pairings/${pair.id}/revoke`, { method: 'POST' }); await refresh(); setCode(null); } catch(e) { report(e); } }}>ยกเลิกการจับคู่</button>
      </li>)}</ul>
    </div></section>;
}
