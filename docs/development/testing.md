# Testing

ใช้ `.venv/Scripts/python.exe tools/check.py --scope <scope>` เลือกเฉพาะส่วนที่แก้และสัญญาที่ได้รับผล
แต่ละ run แสดง wall time และบันทึกผล JSON แยกไฟล์ใน `build/checks/` ซึ่งไม่เข้า Git

| เปลี่ยนส่วนไหน | Scope | สิ่งที่ตรวจ |
|---|---|---|
| กติกาล้วน ไม่เปิด API/DB | unit | tests/unit ทั้งหมด |
| ปิด desktop รอ save ACK | unit-close | duplicate close, save failure และ late callback หลัง timeout |
| Permission/token policy ล้วน | unit-auth | auth policy ไม่เปิด API/DB |
| Validation/error catalog ล้วน | unit-input | schema validation |
| Lock, migration, startup failure | contracts | integration ด้วย temporary SQLite/ไฟล์ |
| Authentication/permission ผ่าน HTTP | auth | role matrix + API boundary |
| API shape, trace, export, log | api-core | route contracts อย่างเดียว |
| API, auth, export, log | api | ASGI requests และฐานข้อมูลจริงใน sandbox |
| แบบร่างและสิทธิ์ | story-api | incomplete save, restart, idempotency, revision conflict และ privacy |
| สำรอง/อัปเกรด DB | migration | WAL backup, rollback DDL/data, unknown version และ offline checks |
| Pairing/ไฟล์แนบ | pairing | nonce/revoke/scoped token, DPAPI, interrupted import และ native framing |
| Native framing/hello | bridge-contract | malformed/oversize/origin/version และ subprocess stdout |
| Extension protocol/background | extension-unit | WXT/Vitest, sender, timeout และ reconnect |
| Build Extension | build-extension | WXT prepare, TypeScript และ MV3 output |
| Popup ใน browser จริง | extension-smoke | Chromium profile แยก; ต้อง build Extension ก่อน |
| สถานะงาน, receipt, retry, cancel | workflow | simulator + นาฬิกาจำลอง |
| อายุและการกู้ worker | runtime | ปิด child process จริงแล้วตรวจการกู้คืน |
| ตัวเปิด Dev ไม่มี console (Windows) | desktop | เปิด VBS + pythonw + WebView จริงในข้อมูลชั่วคราว ตรวจ dashboard/console และปิดหน้าต่างทดสอบ |
| กติกาปุ่ม UI | ui | Vitest |
| TypeScript โดยไม่บิลด์หน้าเว็บ | typecheck | tsc -b |
| หน้าจอเชื่อม API | e2e | Playwright + API + worker จริง |
| เปลี่ยนหลายระบบ / ส่งมอบรุ่น | all | lint + backend + UI/build/E2E + Extension unit/build/smoke |
| MD อย่างเดียว | ไม่มี runtime scope | ตรวจลิงก์ ขนาด และ `git diff --check` |
| Test runner/ตัวเลือกชุดเทส | tooling | mapping, deduplication และ Git changes |

Offline doctor ใช้ scope `offline`; ทั้ง backend โดยไม่เปิด browser ใช้ scope `backend`
เมื่อแก้บั๊ก เพิ่ม behavioral test ที่ขอบเขตนั้น พร้อมเคสซ้ำ/เวลา/crash ที่เกี่ยวข้อง
ใช้ injected clock แทนการรอจริง ยกเว้น process/browser integration
ไม่เรียกผู้ให้บริการจริงในเทสปกติ
Scope api รวม `test_auth.py`: role matrix ทุก route, token, bypass, forged role และ production guard

เลือกหนึ่งเคส: `python tools/check.py --scope auth --match viewer`
เลือกหลายชุด: `python tools/check.py --scope unit-auth api-core` รวม pytest เป็น process เดียวและตัดชุดซ้ำ
เลือกตามไฟล์: `python tools/check.py --changed --dry-run` ดูแผนก่อน แล้วเอา --dry-run ออกเพื่อรัน
กติกา selector/CI: [Test selection](test-selection.md)

## งบเวลาทดสอบ

ตั้งเป้า unit/workflow/API ไม่เกิน 10 วินาทีต่อชุด และ foundation all ไม่เกิน 60 วินาที
หลังติดตั้ง dependencies แล้ว ตัวเลขนี้เป็นเป้าหมายสำหรับ feedback ในเครื่อง
ไม่รวม CI provisioning, EXE build หรือการสร้างสื่อจริงในอนาคต
ผลที่วัดแล้วอยู่ใน [รายงานรุ่น](../delivery/verification-0.1.0.md)

ใช้ scope เล็กที่สุดที่ครอบคลุมงาน ไม่รัน all ซ้ำเมื่อแก้แค่เอกสารหรือ fixture
ถ้า all เสร็จแล้วมี failure ให้แก้และรันเฉพาะ test IDs กับ contract ที่ได้รับผล
รายงานผล all เดิมตามจริง ไม่เปลี่ยนผลเก่าเป็นผ่านเพราะ subset ผ่าน

## Browser และ static checks

บิลด์ UI ก่อน E2E เมื่อ source UI เปลี่ยนหรือยังไม่มี dist; backend-only ใช้ UI build เดิมได้
CI เครื่องใหม่จะ build เฉพาะเมื่อแผนต้องใช้ browser; ไม่บิลด์ EXE ใน routine checks
SETUP ติดตั้ง Chromium; E2E ใช้ temporary data ไม่ใช้ browser profile ของลูกค้า
Trace เมื่อ fail และ screenshot อยู่ใน `frontend/test-results/` ซึ่งไม่เข้า Git
TypeScript ตรวจผ่าน `npm run build`; Python ใช้ `python -m ruff check backend tests tools desktop_entry.py`
Ruff ทั้ง repo (~0.2–0.3 วินาที) เป็นขั้นแรกของทุก run ที่เลือก Python scope ไม่ใช่เฉพาะ all; รันครั้งเดียวแม้รวมหลาย scopes
Scope ที่ไม่ใช่ Python (ui, typecheck, extension-*, desktop) ไม่ lint; JSON report มี lint เป็น entry `{scope: 'lint', seconds, exit_code}`
ลำดับขั้นมาจาก `selected_steps()` ใน check.py; เทสอยู่ [test_check_lint.py](../../tests/test_check_lint.py) ยังไม่อยู่ใน scope tooling ให้รัน pytest ตรง
Starlette รุ่นปัจจุบันมี TestClient/httpx deprecation warning ที่บันทึกไว้ในรายงาน

Source: [check.py](../../tools/check.py), [pytest config](../../pyproject.toml),
[Playwright config](../../frontend/playwright.config.ts), [CI](../../.github/workflows/checks.yml)
เทส EXE/เครื่องลูกค้า: [Packaging](../delivery/packaging.md)

Native EXE integration: `python tools/pairing_smoke.py` หลัง build helper; profile/backend/HKCU host แยกจากผู้ใช้

Native close integration: `python tools/desktop_close_smoke.py` เปิด WebView ในข้อมูลชั่วคราว แล้วปิดก่อน debounce และตรวจ DB
