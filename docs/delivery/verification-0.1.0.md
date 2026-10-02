# Foundation 0.1.0 verification

หลักฐานตรวจในเครื่องวันที่ 2026-10-02; รายงานนี้เป็น snapshot ไม่ใช่คำสั่งให้รันซ้ำ

## Source and browser

- `tools/check.py --scope all` ผ่าน: backend 32 tests ใน 4.57s, Vitest 2 tests,
  Playwright E2E 2 tests ใน 8.6s
- Wall time ของคำสั่งรวม lint, process startup และ UI build: **50.25s**
- Final lint ผ่าน; browser rerun หลังแก้ UI: 2 tests ผ่านใน 13.5s
- มี Starlette TestClient/httpx deprecation warning 1 รายการ ไม่มี test failure ใน full check ที่เสร็จ

## ข้อผิดพลาดที่พบระหว่างสร้างฐาน

- Worker ที่ถูก kill ขณะใช้ shared multiprocessing Event ทำให้ shutdown ค้าง
  แก้เป็น disposable pipe และ local Event; actual process-termination regression ผ่าน
- Vitest เคย discover Playwright files; แก้ขอบเขต discovery ของ unit tests แล้ว

## Packaged Windows

- `tools/build.py` สร้าง portable Windows x64 จาก clean source commit `5847f79`
- `tools/packaged_smoke.py` ผ่าน: compiled UI, authenticated API, worker process จริง,
  restart ที่คง simulator send เพียงครั้งเดียว, automatic save recovery และ native WebView2
- ใช้ isolated data ใน path ภาษาไทย และปิด process ที่เทสสร้างเอง
- EXE SHA-256: `88a78062c2b4f9b8ad9adeb35bcc5c794c053432406c932f67b60823276e1c3a`

## ยังไม่ยืนยัน

Clean Windows/client installation, installer/signing, real providers และ GitHub CI completion
MD-only commits หลัง `5847f79` ไม่เปลี่ยน binary ที่ตรวจนี้
ผลเทสและไฟล์ไบนารีในเครื่องไม่เข้า Git; ดู [Packaging](packaging.md) สำหรับวิธีตรวจ
