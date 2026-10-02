# Testing

ใช้ `.venv/Scripts/python.exe tools/check.py --scope <scope>`
แต่ละ run แสดง wall time และบันทึกผล JSON แยกไฟล์ใน `build/checks/` ซึ่งไม่เข้า Git

| เปลี่ยนส่วนไหน | Scope | สิ่งที่ตรวจ |
|---|---|---|
| Error definitions, validation, lock, migration | unit | contracts + temporary SQLite |
| API, auth, export, log | api | ASGI requests และฐานข้อมูลจริงใน sandbox |
| สถานะงาน, receipt, retry, cancel | workflow | simulator + นาฬิกาจำลอง |
| อายุและการกู้ worker | runtime | ปิด child process จริงแล้วตรวจการกู้คืน |
| กติกาปุ่ม UI | ui | Vitest |
| หน้าจอเชื่อม API | e2e | Playwright + API + worker จริง |
| เปลี่ยนหลายระบบ / ส่งมอบรุ่น | all | lint + backend + UI + build frontend + E2E |
| MD อย่างเดียว | ไม่มี runtime scope | ตรวจลิงก์ ขนาด และ `git diff --check` |

Offline doctor: `.venv/Scripts/python.exe -m pytest tests/test_offline.py`
เมื่อแก้บั๊ก เพิ่ม behavioral test ที่ขอบเขตนั้น พร้อมเคสซ้ำ/เวลา/crash ที่เกี่ยวข้อง
ใช้ injected clock แทนการรอจริง ยกเว้น process/browser integration
ไม่เรียกผู้ให้บริการจริงในเทสปกติ

## งบเวลาทดสอบ

ตั้งเป้า unit/workflow/API ไม่เกิน 10 วินาทีต่อชุด และ foundation all ไม่เกิน 60 วินาที
หลังติดตั้ง dependencies แล้ว ตัวเลขนี้เป็นเป้าหมายสำหรับ feedback ในเครื่อง
ไม่รวม CI provisioning, EXE build หรือการสร้างสื่อจริงในอนาคต
ผลที่วัดแล้วอยู่ใน [รายงานรุ่น](../delivery/verification-0.1.0.md)

ใช้ scope เล็กที่สุดที่ครอบคลุมงาน ไม่รัน all ซ้ำเมื่อแก้แค่เอกสารหรือ fixture
ถ้า all เสร็จแล้วมี failure ให้แก้และรันเฉพาะ test IDs กับ contract ที่ได้รับผล
รายงานผล all เดิมตามจริง ไม่เปลี่ยนผลเก่าเป็นผ่านเพราะ subset ผ่าน

## Browser และ static checks

บิลด์ UI ก่อน E2E: `npm run build` ใน `frontend/` แล้วใช้ `--scope e2e`
SETUP ติดตั้ง Chromium; E2E ใช้ temporary data ไม่ใช้ browser profile ของลูกค้า
Trace เมื่อ fail และ screenshot อยู่ใน `frontend/test-results/` ซึ่งไม่เข้า Git
TypeScript ตรวจผ่าน `npm run build`; Python ใช้ `python -m ruff check backend tests tools desktop_entry.py`
Starlette รุ่นปัจจุบันมี TestClient/httpx deprecation warning ที่บันทึกไว้ในรายงาน

Source: [check.py](../../tools/check.py), [pytest config](../../pyproject.toml),
[Playwright config](../../frontend/playwright.config.ts), [CI](../../.github/workflows/checks.yml)
เทส EXE/เครื่องลูกค้า: [Packaging](../delivery/packaging.md)
