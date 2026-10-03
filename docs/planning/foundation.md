# Foundation work plan

**เริ่มจากโครงสร้างพื้นฐานก่อนต่อ provider จริง**
รายการที่ไม่ได้ระบุว่าทำแล้วเป็นแผนที่ยังไม่ implement
ความสามารถปัจจุบันดู [Status](../delivery/status.md); ผลเทสเก่าไม่ใช่หลักฐานว่าแผนนี้เสร็จ

## ลำดับงาน

| ลำดับ | งาน | เกณฑ์เสร็จ |
|---|---|---|
| F0 — ทำแล้ว | แยกเอกสารและ index | อ่านเฉพาะหัวข้อได้ ลิงก์ไม่เสีย ไม่รวม history ไว้ไฟล์กลาง |
| F1 — ทำแล้ว | API, error และ trace contracts | Typed responses, OpenAPI, pagination และ command trace; ตรวจด้วย API/workflow/E2E |
| Auth foundation — ทำแล้ว | Session + permissions คู่กับทุก feature | Token ทุก route, deny เมื่อไม่มี policy, role matrix, dev identity bypass ใช้ใน Prod/EXE ไม่ได้; ยังไม่มี account/license |
| F2 — ทำแล้วใน source | Worker readiness และการตรวจงานค้าง | alive/ready/stalled จาก heartbeat, restart ใน budget ไม่ replay send; ยังไม่ตรวจใน EXE ([Runtime](../architecture/runtime.md)) |
| F3 — บางส่วน | ฐานข้อมูลและการอัปเกรด | WAL backup/integrity/transaction rollback ทำแล้ว; ยังต้อง clean Windows upgrade และ restore UX |
| F4 | Diagnostics สำหรับเครื่องลูกค้า | เก็บหลักฐานครบเมื่อเริ่มโปรแกรมไม่ได้ export ได้และพิสูจน์การกรองข้อมูลส่วนตัว |
| F5 | Packaging และ clean Windows | ติดตั้ง เปิด ทำงานต่อ อัปเกรด และถอนติดตั้งตามนโยบายข้อมูลที่ระบุไว้ได้ |
| F6 | Provider pilot หนึ่งราย | งานหนึ่งขั้นตอนจบจริง ผ่าน retry/crash/duplicate cases และตรวจผลที่บันทึก |

Story domain/API และ Extension mock bridge เริ่มพัฒนาแยกขั้นได้ตาม [Story Shorts](story-shorts.md)
F2 เป็น gate ก่อน live provider automation; F3 เป็น gate ก่อน migration ของข้อมูลจริง
F4/F5 เป็น gate ก่อนส่งให้ลูกค้า ไม่ต้องรอ installer ก่อนทดสอบ source prototype ในเครื่อง dev
F6 เริ่มจาก ChatGPT Web สร้างบทหนึ่งงาน ต่อด้วยภาพหนึ่งฉาก ก่อนขยาย workflow
แต่ละ F เป็นงานแยกที่ส่งตรวจได้ ไม่ใช่คำสั่งให้แก้ทุกระบบในครั้งเดียว

## F1 ที่ทำแล้ว

Source ที่ต้องแตะ: [API](../../backend/smartflow/api.py),
[Errors](../../backend/smartflow/errors.py), [Jobs](../../backend/smartflow/jobs.py),
[Frontend API client](../../frontend/src/api.ts)

- Typed models ครบ job, health, events, diagnostics, log, database projection และ error envelope
- OpenAPI ระบุผลสำเร็จ/error และ ZIP binary; contract test ตรวจ schema ตรงกับ source
- Job trace คงเดิม; command trace เชื่อม resume/cancel/reconcile รวมคำสั่งซ้ำที่ไม่เปลี่ยนสถานะ
- Pagination/order/retry ระบุในเอกสาร API; 404/405 ไม่รายงานเป็น validation อีกต่อไป
- ทดสอบ error, ข้อมูลส่วนตัว, pagination, duplicate commands และ UI เดิมกับ API ใหม่แล้ว

หลักฐาน: [Verification F1](../delivery/verification-f1.md)
F2 heartbeat/stall ทำแล้วใน source; งานถัดไปคือ F3 ส่วนที่เหลือ (clean Windows upgrade และ restore UX)
ไม่รัน full suite หรือสร้าง EXE ทุกครั้งที่แก้ชื่อ field หรือเอกสาร

## เงื่อนไขปิดงานแต่ละ F

1. โค้ดทำงานตาม contract และ test ของขอบเขตนั้นผ่าน
2. เคส failure สำคัญมี regression test ที่ตรวจพฤติกรรม
3. เหตุที่กู้เองได้ต้องกู้แบบมีขอบเขตและตรวจผล; เหตุที่ต้องให้ผู้ใช้ทำมีรหัสและ checkpoint
4. อัปเดตเอกสารเจ้าของเรื่องและสถานะของ F นั้นในไฟล์นี้
5. รายงานเวลาเทสและขอบเขตที่ตรวจจริง แยกจาก installed/client/provider proof

เอกสารอ้างอิง: [API](../operations/api.md), [Errors](../operations/errors.md),
[Runtime](../architecture/runtime.md), [Storage](../architecture/storage.md),
[Diagnostics](../operations/diagnostics.md), [Packaging](../delivery/packaging.md)
