# Extension pairing: implemented boundary

WXT 0.21.4 + TypeScript + React + Manifest V3; Extension/helper **0.2.0**, protocol **1**
ทำแล้ว: sender guard, native framing, Windows registration, pairing, DPAPI credential, probe, revoke
และ P3 งานจำลองผ่าน `StoryRunner` (claim/grant/result/inspect) ทาง `POST /api/browser/work`
ยังไม่ทำ: provider content adapter หรือการสร้างบท/ภาพจริง
แผนถัดไป: [Coordinated plan](../planning/story-extension-milestones.md)

## Identity และ permission

- Permission มี `nativeMessaging`, `storage` (ledger ของงานจำลอง) และ `alarms` (heartbeat ทุก 30 วินาที)
  ไม่มี host access/content scripts/clipboard/debugger
- Host `com.smartflow.next.dev`; Extension ID `fdohildaocnlmoaecommlohgpcdhknmb`
- Public manifest key ใช้กำหนด ID คงที่; ไม่มี private signing key ใน repo
- Background รับ probe/pair เฉพาะ popup URL และ ID ของตัวเอง
- Host ตรวจ calling origin แบบ exact match; framed UTF-8 uint32, cap 64 KiB
- `bridge_config.json` กำหนดรุ่น/ID ที่ backend ยอมรับ; native และ Extension ตรวจ protocol เช่นกัน

## Pairing flow

1. Owner เปิด “เชื่อมต่อ Extension” และสร้างรหัสแบบสุ่ม อายุ 120 วินาที
2. ผู้ใช้ใส่รหัสใน popup; host สร้าง agent token และบันทึก pending ด้วย Windows current-user DPAPI ก่อน exchange
3. Host ส่งรหัสกับ token ไป local API; DB เก็บเฉพาะ hashes ไม่เก็บค่า token/nonce
4. Retry exchange เดิมต้องใช้ token เดิม; code เดิมกับ token ต่างถูกปฏิเสธ
5. Pairing ใหม่สำเร็จเพิกถอนอันเก่าของ ID เดียวกัน; owner กดยกเลิกได้ทันที
6. Agent token ได้เฉพาะ `/api/browser/agent`; อ่าน draft/jobs/logs/DB หรือจัดการ pairing ไม่ได้

Owner ใช้ `browser:manage`; code ใช้ `browser:pair`; agent ใช้ `browser:status` และ `browser:work`
Role สองชนิดหลังเป็น internal identity และตั้งเป็น desktop role ไม่ได้
Native host ยึด loopback port ใน config, timeout 4 วินาที, ไม่ใช้ proxy/redirect และไม่รับ arbitrary URL/shell
Popup probe มี deadline 7 วินาที; polling ทุก 5 วินาทีเฉพาะตอน popup เปิด
Desktop แสดง connected เมื่อมีการยืนยันใน 90 วินาทีล่าสุด; ไม่ใช่ readiness ของ ChatGPT
Background ใช้ alarm ทุก 30 วินาทีเรียก sync แม้ปิด popup
Transitions การจับคู่มี `browser_events` ใน transaction; logs มี trace/event โดยไม่มีรหัสหรือ credential
เมื่ออ่านสถานะหรือสร้าง pairing ใหม่ pending ที่เลยเวลาเปลี่ยนเป็น `expired` พร้อม `browser.expired` ใน transaction เดียวกัน; revoke ซ้ำไม่เพิ่ม `browser.revoked`

## Build และติดตั้ง Dev

```powershell
.venv\Scripts\python.exe tools/check.py --scope build-extension
.venv\Scripts\python.exe -m PyInstaller --noconfirm --onedir --console --name SmartFlowNextHost --paths backend --distpath build/native --workpath build/native-work --specpath build native_entry.py
.venv\Scripts\python.exe tools/register_native_host.py --exe build/native/SmartFlowNextHost/SmartFlowNextHost.exe
```

Registration ใช้ HKCU เฉพาะ host ใหม่; ค่าเริ่มต้นปฏิเสธการทับ manifest ของ installation อื่น (exit 2 พร้อมแนะนำ `--replace`) โดยไม่เขียนไฟล์/registry
`--exe <exe> --replace` พิมพ์ path manifest เก่า -> ใหม่ แล้วทับเฉพาะ host-name key ของโปรเจกต์นี้
`--unregister` ลบเฉพาะ key นั้น คงไฟล์ manifest/config ไว้; รันซ้ำแจ้ง not registered และ exit 0
`--replace` ใช้คู่กับ `--unregister` ไม่ได้, `--unregister` ไม่รับ `--exe`, นอกนั้นต้องมี `--exe`; ตรวจก่อนแตะ registry
Helper ใช้ stdio ตาม Chrome protocol; Chrome เป็นผู้เปิด process ไม่มี terminal ที่ลูกค้าต้องเปิดค้าง
Config ข้าง EXE มี port/ID/path ของไฟล์ DPAPI; ไม่มี owner token หรือ provider credential
โหลด `browser_extension/.output/chrome-mv3` ผ่าน Load unpacked ใน Chrome ที่ผู้ใช้เลือก
ย้ายโฟลเดอร์ helper แล้วต้องรัน `--exe <path ใหม่> --replace`; Chrome ไม่หา helper ที่ย้ายเอง
ยังไม่ใช่ installer หรือชุด client-ready; ไม่แก้ identity/profile/Extension ของระบบเดิม

## หลักฐานและการทดสอบ

`pairing`, `auth`, `extension-unit`, `build-extension` ตรวจ contract และสิทธิ์
`extension-smoke` เปิด popup ใน Chromium profile แยก; ไม่ลงทะเบียน host
`python tools/pairing_smoke.py` ใช้ compiled helper, temporary backend/profile และ unique HKCU host
`--story` เพิ่มการรันงานจำลองผ่าน runner จริงใน Extension: snapshot, ส่งครั้งเดียว, result ACK และ privacy
ผลล่าสุด (2026-10-03, helper 0.2.0 จาก commit 943e7b6): pairing ผ่านใน 11.3 วินาที, `--story` ผ่านใน 13.9 วินาที
ทั้งสองรันใน Playwright Chromium profile แยก
ตรวจใน Chrome profile ของผู้ใช้ (2026-10-03): โหลด 0.2.0 แบบ unpacked, จับคู่กับ Dev DB จริงสำเร็จ,
background sync เข้ามาทุก 30.0 วินาทีขณะปิด popup (สังเกต 75 วินาที); ยังไม่ได้รันงาน Story จำลองใน profile นี้
ตรวจ Chrome native exchange, credential ข้าม helper process และ revocation แล้วลบเฉพาะ registry key ของเทส
เทสนี้ไม่ติดตั้ง Extension ใน Chrome profile ของผู้ใช้ และไม่ใช่หลักฐาน provider output

Source: [bridge](../../backend/smartflow/browser_bridge.py), [native client](../../backend/smartflow/native_client.py),
[protocol](../../browser_extension/protocol/index.ts), [registration](../../tools/register_native_host.py)
Tests: [pairing/assets](../../tests/test_assets_pairing.py), [native framing](../../tests/test_native_host.py),
[registration](../../tests/unit/test_register_native_host.py) (fake registry, scope `unit`; ไม่แตะ HKCU จริง)
หลักฐาน: [P2 verification](../delivery/verification-autosave-pairing.md)
