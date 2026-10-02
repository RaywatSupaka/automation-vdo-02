# Verification F1 — 2026-10-02

ขอบเขต: source API/error/trace contracts บน branch dev; provider ยังเป็น simulator
ไม่ใช่การส่งมอบ EXE รุ่นใหม่หรือการทดสอบเครื่องลูกค้า

| คำสั่ง | ผล | Wall time |
|---|---|---|
| `python tools/check.py --scope api` | 17 passed | 3.435s |
| `python tools/check.py --scope workflow` | 17 passed | 2.449s |
| `python tools/check.py --scope unit` | 5 passed (รวม startup error ของตัวเปิดใหม่) | 2.631s |
| `python tools/check.py --scope e2e` | 2 passed | 26.630s |
| `python tools/check.py --scope desktop` | dashboard rendered, console_attached=false | 26.978s |
| `python -m ruff check backend tests tools desktop_entry.py` | passed | ไม่วัดแยก |

API tests ตรวจ response models ทุก projection, schema drift, status/error/trace,
validation ที่ไม่เผยค่า/ชื่อ field ส่วนตัว, pagination เมื่อเวลาเท่ากัน,
คำสั่งซ้ำและ reconciliation ที่คง job trace และส่ง provider เพียงครั้งเดียว
E2E ตรวจสร้างงาน ดู events/DB/logs ส่งออก ZIP และ unknown-send reconciliation ผ่าน UI เดิม
ไม่มีการเปลี่ยน frontend source จึงไม่บิลด์ UI หรือ EXE ซ้ำ
Starlette TestClient/httpx deprecation warning เดิมยังมี; ไม่ทำให้เทสล้มเหลว

## ตัวเปิด Dev ไม่มี console

RUN_DEV.vbs เรียก pythonw; RUN_DEV.bat ส่งต่อไป VBS และไม่ค้างรอโปรแกรม
Native smoke ใช้ temporary data/port แยกและปิดหน้าต่างที่สร้างเองแล้ว
ตรวจฐานข้อมูลของ Dev เดิมว่าคิวว่างก่อนปิดหน้าต่างตามปกติและเปิดใหม่ในโหมดเดิม
ยืนยันหน้าต่าง SmartFlow Next อยู่บน pythonw และ log ของ `/api/health`, `/api/jobs` เป็น 200
Log ยังคงอยู่ในไฟล์; ยังไม่ได้ทดสอบ launcher บน Windows เครื่องอื่น

ผลแต่ละ run เก็บใน `build/checks/` (ไม่เข้า Git)
งานถัดไป: F2 ใน [Foundation plan](../planning/foundation.md)
