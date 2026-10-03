# Storage

ใช้ SQLite + SQLAlchemy 2 และ Alembic migration `0004`
ข้อมูลแยกจากโฟลเดอร์ติดตั้ง; ตำแหน่งตามโหมดอยู่ใน [Setup](../development/setup.md)

| ตาราง | หน้าที่ |
|---|---|
| jobs | ข้อมูลงาน สถานะ ขั้นตอน retry counters และ artifact reference |
| receipts | รหัสคำขอ สถานะการส่ง และผลที่ต้องเก็บต่อ |
| events | ลำดับเหตุการณ์และเหตุผลที่สัมพันธ์กับ job/trace |
| simulated_requests | จำลองการรับคำขอภายนอก ใช้ตรวจ sends ในเทส |
| alembic_version | schema revision |
| story_drafts | แบบร่าง 95 ช่อง, revision และขั้นปัจจุบัน |
| draft_commands | idempotency hash และ response เดิม |
| draft_events | audit การบันทึก/นำเข้า ไม่มีเนื้อหาเรื่อง |
| draft_assets | เจ้าของ field, display name, checksum, ขนาดและสถานะสำเนาไฟล์ |
| browser_pairings | hashes ของ nonce/token, expiry, state และ last_seen |
| browser_events | audit การจับคู่/เพิกถอน ไม่มี credential |
| story_revisions | snapshot config ของแบบร่างที่เริ่มงาน แก้แบบร่างภายหลังไม่เปลี่ยนงาน (หนึ่งต่อ job) |
| story_operations | owner pairing/connection, lease epoch/expiry และ deadline ของงานจำลอง |
| operation_receipts | request ID, สถานะ prepared→dispatching→accepted→completed/unknown, ผลและ sha256 |
| browser_sessions | connection ปัจจุบันและ last_seen ต่อ pairing |

## Transaction และไฟล์

เปิด WAL, foreign keys, busy timeout และ FULL synchronous
ใช้ `BEGIN IMMEDIATE` สำหรับ write transaction เพื่อจัดลำดับ claims และคำสั่งซ้ำข้าม process
ไม่ถือ transaction ระหว่างรอ external operation
สถานะและ events commit ร่วมกัน หลัง commit จึง mirror เหตุการณ์ไป log

ไฟล์สื่ออยู่ภายนอก SQLite; เขียน temporary file ของงาน, flush/fsync แล้ว atomic replace
รุ่น 0.1.0 บันทึก text checkpoint ที่ระบุว่าเป็น simulation เท่านั้น
ไม่ใช่หลักฐานว่ามีรูปหรือวิดีโอจาก AI จริง

## ข้อจำกัดปัจจุบัน

Migration มี process lock และ BEGIN IMMEDIATE; สำรอง committed WAL ด้วย SQLite backup ก่อน upgrade
ตรวจ integrity ของ backup และฐานหลัง migration พร้อม foreign keys; backup มี deadline 30 วินาที
Schema/data อยู่ใน explicit transaction; เมื่อ upgrade ล้มเหลว rollback กลับโดยไม่ restore ทับฐานที่กำลังเปิด
Backup เก็บใน data directory `backups/`; ไม่สำรองซ้ำเมื่อ schema ตรง head แล้ว
Unknown version/ฐานที่มีตารางแต่ไม่มี version ต้อง fail ไม่ reset และไม่สร้าง schema ทับ
ยังไม่มี backup retention, UI เลือก restore, event pruning หรือ clean-machine upgrade proof
F3 จึงยังไม่ครบทุกส่วน ดู [foundation plan](../planning/foundation.md)
Draft API ที่ใช้ schema นี้: [Draft persistence](draft-api.md)

Source: [models.py](../../backend/smartflow/models.py), [db.py](../../backend/smartflow/db.py),
[migration 0001](../../backend/smartflow/migrations/versions/0001_foundation.py)
และ [migration safety](../../backend/smartflow/migration_safety.py), [migration 0002](../../backend/smartflow/migrations/versions/0002_story_drafts.py)
เทส: [test_contracts.py](../../tests/test_contracts.py), [test_offline.py](../../tests/test_offline.py)
การอ่าน DB เพื่อวิเคราะห์: [Diagnostics](../operations/diagnostics.md)
