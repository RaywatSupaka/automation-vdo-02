# Diagnostics

ใช้รหัสงานและหลักฐานที่บันทึกจริงเป็นจุดเริ่มวิเคราะห์
รายงานให้แยกสิ่งที่พบ เหตุผลที่สรุปได้ และสิ่งที่ยังพิสูจน์ไม่ได้

## ขั้นตอนเมื่อแจ้งปัญหา

1. อ่าน health และค้นงานจาก job ID
2. เปิด job diagnostic เพื่อดู stage, receipt, error และ events
3. เทียบ trace ID กับ runtime/worker logs ตามช่วงเวลาที่เกิดปัญหา
4. อ่าน DB ผ่าน allowlisted projections ถ้าต้องตรวจ state ที่บันทึกไว้
5. เลือกวิธีกู้คืนจาก receipt ตาม [Automation](../architecture/automation.md)
6. ถ้า API เปิดไม่ได้ ใช้ offline doctor โดยไม่แก้ DB เพื่อให้ดูเหมือนหายเสีย

คำสั่งเมื่อ API เปิดอยู่และ process มี session token:

```powershell
.venv\Scripts\python.exe -m smartflow.cli api --path /api/diagnostics/database/jobs
.venv\Scripts\python.exe -m smartflow.cli api --path /api/diagnostics/logs
```

ตรวจ offline โดยไม่ต้องมี token และไม่สร้างฐานข้อมูลใหม่:

```powershell
.venv\Scripts\python.exe -m smartflow.cli doctor --offline
```

## ข้อมูลและขอบเขต

- DB events เป็นประวัติที่ commit กับสถานะงาน; runtime log เป็นสำเนาหลักฐานและ HTTP/process events
- API ใช้ `logs/runtime.jsonl`; worker ใช้ `logs/worker.jsonl`
- แต่ละไฟล์หมุนที่ 2 MB พร้อม backup 4 ไฟล์ แยก process เพื่อป้องกัน rotation ชนกัน
- Events ใน DB ยังไม่มีการ prune อัตโนมัติ
- Support ZIP รวมสถานะงานและ 200 events ล่าสุด พร้อม flag ถ้าตัดประวัติ
- ไม่รวม title, prompt, provider result, token, user path หรือ raw database
- Internal exception เก็บ class และ filename/function/line; ไม่เก็บ message, source text หรือ locals
- Offline doctor ตรวจ DB แบบ read-only, schema revision, counts, integrity และ log ล่าสุด
- Client support ปัจจุบันเป็น ZIP ที่ผู้ใช้ส่งออกเอง ไม่มีการอัปโหลดหรือ remote access อัตโนมัติ

คำว่า `SEND_ACCEPTANCE_UNKNOWN` หมายถึงยังยืนยันการรับไม่ได้
ห้ามสรุปว่า provider สร้างภาพล้มเหลวหรือเครือข่ายเสียหากไม่มีหลักฐาน

Source: [diagnostics.py](../../backend/smartflow/diagnostics.py),
[observability.py](../../backend/smartflow/observability.py), [offline.py](../../backend/smartflow/offline.py)
เทส: [test_api.py](../../tests/test_api.py), [test_offline.py](../../tests/test_offline.py)
