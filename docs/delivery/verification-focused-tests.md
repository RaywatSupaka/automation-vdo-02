# Verification focused checks — 2026-10-02

เปลี่ยน test runner, CI selection, fixture imports และแยก pure unit tests; ไม่แก้ runtime ของโปรแกรม

| คำสั่ง | ผล | Wall time รวมเริ่ม Python |
|---|---|---|
| `python tools/check.py --scope unit-auth` | 7 passed; pytest 0.12s | 1.158s |
| `python tools/check.py --scope unit-auth --match viewer` | 3 passed, 4 deselected; pytest 0.10s | 0.812s |
| `python tools/check.py --scope tooling` | 14 passed รวม repo ชั่วคราวสำหรับ staged/untracked/rename | 1.648s |
| `python tools/check.py --scope unit-input contracts api-core workflow offline` | 42 passed ใน pytest process เดียว | 7.658s |
| `python tools/check.py --changed --dry-run --plan-json build/check-plan.json` | แสดง all เนื่องจาก workflow เปลี่ยน; ไม่รันเทส | ไม่วัด |

ย้าย validation/error catalog ออกจาก test_contracts ไป tests/unit/test_inputs
test_contracts เหลือ integration 3 เคส; tests/unit ไม่เปิด API/DB
conftest โหลด FastAPI/DB เมื่อ fixture ต้องใช้จริง แทนการโหลดทุกครั้งแม้เลือก pure unit
Role/API boundary เดิมยังอยู่ใน tests/test_auth.py; pure unit ไม่ใช้แทน integration ก่อนส่งงานที่แก้ boundary

ตรวจ mapping, รวม scopes ไม่ collect ซ้ำ, case filter, unknown file fallback และ full gate
ตรวจ fixture ที่ย้าย imports ด้วย API/workflow/storage/offline; ไม่มี full suite/UI build/native restart รอบนี้
TestClient/httpx warning เดิมมีเฉพาะชุด integration; pure unit ไม่มี warning นี้
CI workflow ปรับแล้ว แต่เวลาของ GitHub runner/การติดตั้ง dependencies ยังไม่ได้ยืนยันจาก remote run
Scope selection เป็น conservative mapping ระดับไฟล์; ดู [ข้อจำกัด](../development/test-selection.md)
