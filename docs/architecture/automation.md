# Automation lifecycle

Source: [engine.py](../../backend/smartflow/engine.py), [jobs.py](../../backend/smartflow/jobs.py)

## Durable state

- Job: `queued -> running -> completed` หรือ `waiting`, `failed`, `needs_review`, `cancelled`
- Receipt: `prepared -> dispatching -> accepted -> completed`; ผลการส่งไม่แน่ใจเป็น `unknown`
- บันทึก dispatch marker ก่อนเรียก submit ทุกครั้ง
- สร้างงานด้วย Idempotency-Key เดิมและข้อมูลเดิมจะได้งานเดิม; ข้อมูลต่างกันใช้ key เดิมไม่ได้

## การกู้คืนและ retry

| หลักฐาน | การทำต่อที่อนุญาต |
|---|---|
| prepared และยังไม่ส่ง | ทำ preflight แล้วส่งตามขั้นตอน |
| dispatching / unknown หลัง crash | พักตรวจสอบ ห้าม replay |
| accepted | ตรวจคำขอเดิมเพื่อเก็บผล |
| completed receipt แต่ไฟล์ยังไม่พร้อม | บันทึกผลเดิมอีกครั้ง ไม่สร้างผลใหม่ |

Reconciliation เรียก inspect อย่างเดียว ไม่เรียก submit
Availability failure ที่พิสูจน์ว่ายังไม่ส่ง retry ไม่เกิน 3 attempts
การสังเกตผลอัตโนมัติจำกัด 3 ครั้งก่อนพักงานเพื่อทบทวน
บันทึกไฟล์ retry ไม่เกิน 3 attempts โดยคงผลเดิม; หลังหมด budget ผู้ใช้ resume การบันทึกได้
Auth ต้องให้ผู้ใช้ดำเนินการ; การส่งที่ไม่แน่ใจต้องหาหลักฐานก่อนทำต่อ

Cancel หยุดขั้นตอนถัดไป แต่คำขอที่ผ่าน dispatch boundary แล้วอาจจบภายนอกต่อได้
ระบบเก็บ receipt ไว้กับงานที่ยกเลิกเพื่อป้องกันการสร้างซ้ำ
เหตุการณ์และการเปลี่ยนสถานะ commit ด้วยกัน ตาม [Storage](storage.md)

## หลักฐานและข้อจำกัด

ปัจจุบันทดสอบด้วย simulator หนึ่งขั้นตอน ยังไม่มีหลายฉากหรือ provider จริง
Simulator มี durable request table แยกจาก receipt และนับ sends เพื่อจับการส่งซ้ำในเทส
Provider จริงต้องมีการผูกเจ้าของคำขอและ bounded I/O ตาม [Provider adapters](providers.md)

เทส: [test_workflow.py](../../tests/test_workflow.py) / scope `workflow`
Crash ของ process: [test_runtime.py](../../tests/test_runtime.py) / scope `runtime`
