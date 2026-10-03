import { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { browser } from 'wxt/browser';
import type { BridgeStatus } from '../../protocol';
import './style.css';

const labels: Record<BridgeStatus, string> = {
  disconnected: 'ยังไม่เชื่อมต่อ helper', checking: 'กำลังตรวจการเชื่อมต่อ…',
  unpaired: 'พบ helper แล้ว · ยังไม่จับคู่', protocol_error: 'รุ่นหรือข้อความจาก helper ไม่ตรงกัน',
  paired: 'เชื่อมต่อกับโปรแกรมแล้ว', revoked: 'การจับคู่ถูกยกเลิก', unavailable: 'โปรแกรมยังไม่พร้อมเชื่อมต่อ', pairing_rejected: 'จับคู่ไม่สำเร็จ · ตรวจรุ่นโปรแกรมและรหัสจับคู่',
};
function Popup() {
  const [state, setState] = useState<BridgeStatus>('disconnected');
  const busy = useRef(false);
  const [code, setCode] = useState('');
  useEffect(() => {
    let alive = true;
    const timer = setInterval(async () => { if (busy.current) return; busy.current = true; try { const result = await browser.runtime.sendMessage({ kind: 'probe' });
      if (alive && result?.state in labels) setState(result.state); } catch { if(alive) setState('disconnected'); } finally { busy.current = false; } }, 5000);
    return () => { alive = false; clearInterval(timer); };
  }, []);
  return <main><span className="brand">SMARTFLOW NEXT</span><h1>การเชื่อมต่อโปรแกรม</h1>
    <p role="status">{labels[state]}</p><button disabled={state === 'checking'} onClick={async () => {
      if (busy.current) return; busy.current = true; setState('checking');
      try { const result = await browser.runtime.sendMessage({ kind: 'probe' });
        setState(result?.state in labels ? result.state : 'protocol_error'); }
      catch { setState('disconnected'); } finally { busy.current = false; }
    }}>ตรวจการเชื่อมต่อ</button>
    <label>รหัสจับคู่จากโปรแกรม<input aria-label="รหัสจับคู่" type="password" value={code} onChange={e => setCode(e.target.value.trim())}/></label>
    <button disabled={state === 'checking' || !/^[A-Za-z0-9_-]{43}$/.test(code)} onClick={async () => {
      if (busy.current) return; busy.current = true; setState('checking'); try { const result = await browser.runtime.sendMessage({ kind: 'pair', code });
        setState(result?.state in labels ? result.state : 'protocol_error'); if(result?.state === 'paired') setCode('');
      } catch { setState('disconnected'); } finally { busy.current = false; }
    }}>จับคู่</button>
    <p className="note">รุ่นพัฒนา 0.2.0 · ยังไม่เปิดการสั่ง ChatGPT สร้างงาน</p>
  </main>;
}
createRoot(document.getElementById('root')!).render(<Popup/>);
