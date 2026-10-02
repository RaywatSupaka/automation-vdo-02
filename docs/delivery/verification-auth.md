# Verification authentication — 2026-10-02

ขอบเขต: local session authentication, permission ต่อ route, UI ตามสิทธิ์ และ dev identity bypass
ตรวจ source Dev; ไม่ใช่การตรวจบัญชีออนไลน์/license หรือ EXE ที่ส่งลูกค้า

| การตรวจ | ผล | เวลา |
|---|---|---|
| `python tools/check.py --scope api` | 33 passed, 1 failed ที่ตัวทดสอบค้น route ของ FastAPI | wall 4.908s |
| `python -m pytest tests/test_auth.py::test_missing_policy_fails_closed_before_handler` หลังแก้ตัวทดสอบ | 1 passed; ไม่แก้ runtime เพื่อให้เทสผ่าน | pytest 0.18s |
| `python tools/check.py --scope api` หลังเพิ่ม app-wide guard และ regression ของ route ที่เพิ่มนอก router | 35 passed | wall 4.848s |
| `npm run build` | TypeScript + Vite ผ่าน | Vite 17.58s ไม่รวม tsc |
| `npm test` | 2 passed | Vitest 1.90s |
| `python tools/check.py --scope e2e` | 4 passed | wall 18.239s |
| `python tools/check.py --scope desktop` | dashboard ขึ้น, console_attached=false | wall 8.680s |
| `python tools/check.py --scope desktop` หลัง app-wide guard และแยก auth environment ของ smoke | dashboard ขึ้น, console_attached=false | wall 5.993s |
| `python -m ruff check backend tests tools desktop_entry.py` | passed | ไม่วัดแยก |

## หลักฐานที่ตรวจ

- Role matrix owner/operator/viewer/support ครบทุก route ใน OpenAPI
- ไม่มี token, token ผิด, scheme ผิด → 401; ไม่มี permission → 403 และ handler ไม่ทำงาน
- เพิ่ม API นอก router เดิมก็ยังถูก guard ระดับแอปตรวจ; HTML shell ยังเปิดได้โดยไม่เผยข้อมูลงาน
- Viewer ใน dev_bypass ยังสร้าง/สั่งงานไม่ได้; ปลอม header/query role ไม่เพิ่มสิทธิ์
- Support token อ่านข้อมูลที่กรองแล้วได้ แต่สั่งงาน/อ่าน title ผ่าน job API ไม่ได้
- Config ไม่รู้จัก, token สั้น/ซ้ำ และ bypass ใน prod/frozen ถูกปฏิเสธก่อนสร้าง DB
- Session response, log, support ZIP และ repr ของ Settings ไม่เผย token
- E2E ตรวจ owner workflow, support UI + forged POST, invalid token กลับหน้าต่อ session และ reconciliation
- Native smoke เปิดผ่าน RUN_DEV.vbs ด้วยข้อมูลชั่วคราวและปิดหน้าต่างทดสอบเอง

ไม่มี full suite ในรอบนี้; ใช้เฉพาะขอบเขต auth/API/UI/launcher ที่เปลี่ยน
รัน API ซ้ำเพราะเพิ่ม guard ระดับแอปซึ่งกระทบ route ทั้งหมด ไม่ใช่เพราะแก้ fixture อย่างเดียว
E2E ตรวจไว้ก่อนย้าย guard ไป app-wide; หลังย้ายตรวจ API ทุก route, public shell และ native smoke แล้ว
ตรวจ Dev เดิมว่าคิวว่างก่อนปิดตามปกติและเปิดใหม่ผ่าน VBS; log ยืนยัน development identity,
`/api/session` และ `/api/health` คืน 200 จากหน้าต่าง pythonw ที่เปิดใหม่
TestClient/httpx deprecation warning เดิมยังอยู่
Source และ browser fixtures ไม่ยืนยัน clean Windows, remote identity หรือ license
รายละเอียดขอบเขตสิทธิ์และข้อจำกัด: [Security](../operations/security.md)
