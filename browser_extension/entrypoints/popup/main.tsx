import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { browser } from 'wxt/browser';
import type { BridgeStatus } from '../../protocol';
import './style.css';

const labels: Record<BridgeStatus, string> = {
  disconnected: 'ยังไม่เชื่อมต่อ helper', checking: 'กำลังตรวจการเชื่อมต่อ…',
  unpaired: 'พบ helper แล้ว · ยังไม่จับคู่', protocol_error: 'รุ่นหรือข้อความจาก helper ไม่ตรงกัน',
};
function Popup() {
  const [state, setState] = useState<BridgeStatus>('disconnected');
  return <main><span className="brand">SMARTFLOW NEXT</span><h1>การเชื่อมต่อโปรแกรม</h1>
    <p role="status">{labels[state]}</p><button disabled={state === 'checking'} onClick={async () => {
      setState('checking');
      try { const result = await browser.runtime.sendMessage({ kind: 'probe' });
        setState(result?.state in labels ? result.state : 'protocol_error'); }
      catch { setState('disconnected'); }
    }}>ตรวจการเชื่อมต่อ</button>
    <p className="note">รุ่นพัฒนา 0.1.0 · โครงสร้าง Extension ใหม่<br/>ยังไม่เปิดจับคู่หรือสั่ง ChatGPT สร้างงาน</p>
  </main>;
}
createRoot(document.getElementById('root')!).render(<Popup/>);
