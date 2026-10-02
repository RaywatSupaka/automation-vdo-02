# Storage

ใช้ SQLite + SQLAlchemy 2 และ Alembic migration `0001`
ข้อมูลแยกจากโฟลเดอร์ติดตั้ง; ตำแหน่งตามโหมดอยู่ใน [Setup](../development/setup.md)

| ตาราง | หน้าที่ |
|---|---|
| jobs | ข้อมูลงาน สถานะ ขั้นตอน retry counters และ artifact reference |
| receipts | รหัสคำขอ สถานะการส่ง และผลที่ต้องเก็บต่อ |
| events | ลำดับเหตุการณ์และเหตุผลที่สัมพันธ์กับ job/trace |
| simulated_requests | จำลองการรับคำขอภายนอก ใช้ตรวจ sends ในเทส |
| alembic_version | schema revision |

## Transaction และไฟล์

เปิด WAL, foreign keys, busy timeout และ FULL synchronous
ใช้ `BEGIN IMMEDIATE` สำหรับ write transaction เพื่อจัดลำดับ claims และคำสั่งซ้ำข้าม process
ไม่ถือ transaction ระหว่างรอ external operation
สถานะและ events commit ร่วมกัน หลัง commit จึง mirror เหตุการณ์ไป log

ไฟล์สื่ออยู่ภายนอก SQLite; เขียน temporary file ของงาน, flush/fsync แล้ว atomic replace
รุ่น 0.1.0 บันทึก text checkpoint ที่ระบุว่าเป็น simulation เท่านั้น
ไม่ใช่หลักฐานว่ามีรูปหรือวิดีโอจาก AI จริง

## ข้อจำกัดปัจจุบัน

ยังไม่มี automated migration backup/restore หรือ DB event pruning
Migration จากรุ่นที่ไม่รู้จักต้อง fail ไม่ reset ฐานข้อมูล
ก่อนส่ง upgrade ให้ลูกค้าต้องเพิ่ม backup, integrity verification และ compatibility policy
งานเหล่านี้อยู่ใน [foundation plan](../planning/foundation.md)

Source: [models.py](../../backend/smartflow/models.py), [db.py](../../backend/smartflow/db.py),
[migration 0001](../../backend/smartflow/migrations/versions/0001_foundation.py)
เทส: [test_contracts.py](../../tests/test_contracts.py), [test_offline.py](../../tests/test_offline.py)
การอ่าน DB เพื่อวิเคราะห์: [Diagnostics](../operations/diagnostics.md)
