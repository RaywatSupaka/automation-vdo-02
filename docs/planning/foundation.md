# Foundation work plan

**เริ่มจากโครงสร้างพื้นฐานก่อนต่อ provider จริง**
รายการด้านล่างคือแผนที่ยังไม่ implement ยกเว้นงานเอกสารที่ระบุว่าทำแล้ว
ความสามารถปัจจุบันดู [Status](../delivery/status.md); ผลเทสเก่าไม่ใช่หลักฐานว่าแผนนี้เสร็จ

## ลำดับงาน

| ลำดับ | งาน | เกณฑ์เสร็จ |
|---|---|---|
| F0 — ทำแล้ว | แยกเอกสารและ index | อ่านเฉพาะหัวข้อได้ ลิงก์ไม่เสีย ไม่รวม history ไว้ไฟล์กลาง |
| F1 — ถัดไป | API, error และ trace contracts | AI อ่าน schema ของ input/output/error ได้ครบ และตามเหตุของคำสั่งถึงงานได้ |
| F2 | Worker readiness และการตรวจงานค้าง | แยก process alive/ready/progress; timeout และ recovery มี budget และไม่ replay send |
| F3 | ฐานข้อมูลและการอัปเกรด | สำรองก่อน migration, ตรวจ integrity, กู้ได้เมื่อ upgrade ล้มเหลวโดยข้อมูลไม่หาย |
| F4 | Diagnostics สำหรับเครื่องลูกค้า | เก็บหลักฐานครบเมื่อเริ่มโปรแกรมไม่ได้ export ได้และพิสูจน์การกรองข้อมูลส่วนตัว |
| F5 | Packaging และ clean Windows | ติดตั้ง เปิด ทำงานต่อ อัปเกรด และถอนติดตั้งตามนโยบายข้อมูลที่ระบุไว้ได้ |
| F6 | Provider pilot หนึ่งราย | งานหนึ่งขั้นตอนจบจริง ผ่าน retry/crash/duplicate cases และตรวจผลที่บันทึก |

ลำดับ F1–F5 ทำให้ฐานพร้อมสำหรับ provider pilot; ไม่ต้องเพิ่มหลาย provider หรือหลาย workflow พร้อมกัน
แต่ละ F เป็นงานแยกที่ส่งตรวจได้ ไม่ใช่คำสั่งให้แก้ทุกระบบในครั้งเดียว

## งานถัดไปที่เสนอ: F1

Source ที่ต้องแตะ: [API](../../backend/smartflow/api.py),
[Errors](../../backend/smartflow/errors.py), [Jobs](../../backend/smartflow/jobs.py),
[Frontend API client](../../frontend/src/api.ts)

- ประกาศ Pydantic response models ให้ครบ job, health, events, diagnostics และ error envelope
- ให้ OpenAPI ระบุผลสำเร็จและผลผิดพลาดตาม route; regenerate schema จาก source
- รักษา job trace และเชื่อม trace ของคำสั่ง resume/cancel/reconcile กับเหตุการณ์ในงาน
- ระบุ pagination/order และความหมายของ retry ใน API contract ให้ชัด
- แยก validation, not-found, conflict และ internal error ให้ตรงกับหลักฐาน
- เพิ่ม contract tests สำหรับรูปแบบผลลัพธ์ ความเข้ากันได้ของ client และไม่มีข้อมูลลับใน error

การตรวจ F1: scope `api`, `unit`; เพิ่ม `workflow` เฉพาะเมื่อเปลี่ยนพฤติกรรมคำสั่ง
ตรวจ TypeScript เมื่อ client เปลี่ยน; ใช้ E2E เฉพาะเส้นทาง UI ที่ได้รับผล
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
