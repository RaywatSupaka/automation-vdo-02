# Verification: Autosave + native pairing

Date: 2026-10-03 · branch dev · desktop source 0.1.0 · Extension/helper 0.1.1 · DB 0003
ขอบเขต: Story persistence และการจับคู่ local agent; ไม่ยิงผู้ให้บริการจริง

## ตรวจแล้ว

| คำสั่ง | ผล / wall time |
|---|---|
| `python tools/check.py --scope all` | ผ่านครบ 99.18 s: lint, backend 138, UI unit 26, E2E 11, Extension unit 5, ทั้งสอง build และ popup smoke |
| `python tools/check.py --scope story-api pairing migration auth build-extension` | หลังเพิ่ม transactional audit: backend 75 ผ่าน 13.57 s; Extension typecheck 3.91 s / build 2.21 s |
| `python tools/check.py --scope tooling unit-close extension-smoke` | selector/close 22 ผ่าน 1.31 s; popup smoke 2.32 s |
| `python tools/pairing_smoke.py` | Chrome → compiled helper → sandbox API ผ่าน 18.64 s |
| `python tools/check.py --scope desktop` | RUN_DEV.vbs/pythonw/WebView จริงผ่าน 33.37 s; console_attached=false |
| `python tools/desktop_close_smoke.py` | แก้ input แล้วปิด native ก่อน debounce; เปิด DB พบค่าใหม่ 2.23 s |

Full run อยู่ `build/checks/1790969897808369400.json`; artifacts ไม่เข้า Git
หลังเพิ่ม audit และ test mapping ใช้ affected scopes ตามตาราง ไม่รัน full ซ้ำ
ก่อน full run พบ fixture ผิด (อ่าน config จาก list endpoint) และ session-switch race ใน UI
แก้ fixture ให้ GET รายการเต็ม และป้องกัน late response/clear private UI เมื่อเปลี่ยน session; E2E ผ่านแล้ว
Starlette/httpx TestClient deprecation warning ยังมี; ไม่ใช่ failed test

## พฤติกรรมที่ครอบคลุม

- Autosave coalescing, ACK หายใช้ key/body เดิม, revision conflict เก็บ edits และปิดหน้าต่างไม่ได้
- เปิดใหม่คืนข้อความ ขั้น wizard และไฟล์ที่นำเข้าสำเร็จ; failed load ไม่เขียน draft ว่างทับ
- File signature/ขนาด/path/เจ้าของ, interrupted import, bytes ซ้ำ/ต่าง และ missing/corrupted assets
- Nonce expiry/reuse, wrong Extension ID, restricted token และ revoke
- DPAPI จริงบน Windows; เก็บ pending ก่อน exchange และใช้ token เดิมหลัง ACK หาย
- Native close ยกเลิกก่อน flush; duplicate close, failure และ late callback หลัง timeout
- Pairing audit ถูก commit ร่วมกับ state; retry เดิมไม่เพิ่ม browser.paired event ซ้ำ

## เปิดใช้ในเครื่องพัฒนา

ลงทะเบียน HKCU host ใหม่ `com.smartflow.next.dev` ชี้ compiled helper ใน build/native/SmartFlowNextHost
ไม่แก้ registration/profile/Extension ของระบบเก่า
ตรวจหน้าต่างเดิมแล้วไม่มีงาน: 0 total / 0 running
เจ้าของอนุญาตทิ้งแบบร่างเก่าที่อยู่ใน memory; ปิดตามปกติและเปิดใหม่ด้วย RUN_DEV.vbs ใน Dev mode
ตรวจหน้าต่างใหม่พบเมนูเชื่อมต่อ Extension และ Story ที่แสดง “บันทึกแล้วในเครื่อง” / footer Autosave
ฐาน local อัปเกรดเป็น 0003; ไม่ใช้ UI จาก browser test แทนหลักฐาน activation นี้

## ข้อจำกัดที่ยังต้องทำ

- Chrome integration ใช้ profile และ host name ชั่วคราวของเทส; ไม่ได้ติดตั้ง/จับคู่ใน Chrome profile ของผู้ใช้
- Main EXE เดิมยังไม่รวมการเปลี่ยนนี้; ทดสอบ source Dev และ compiled native helper แยกกัน
- ยังไม่มี provider adapter, background readiness/lease, dispatch, งานจาก draft หรือภาพ/เสียง/วิดีโอจริง
- ยังไม่มี installer/clean-machine proof, draft picker/GC หรือรับรอง recovery ของ edits ที่ยังไม่มี ACK เมื่อไฟดับ

Contract: [Draft API](../architecture/draft-api.md), [Extension](../architecture/extension-foundation.md)
Next: [P3 simulated operation/recovery](../planning/story-extension-milestones.md)
