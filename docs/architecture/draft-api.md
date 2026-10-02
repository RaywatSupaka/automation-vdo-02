# Story draft persistence

ทำแล้ว: schema 95 ช่อง, API, Autosave/restore, ไฟล์แนบ, close flush และ migration `0003`
ยังไม่ทำ: snapshot ไปเป็นงาน, provider dispatch และระบบจัดการแบบร่างหลายรายการใน UI
เป้าหมายรอบถัดไป: [Persistence plan](../planning/draft-persistence.md)

## Contract

- POST `/api/story-drafts`: สร้างแบบร่าง; `Idempotency-Key` ยาว 8–80 ตัวอักษร `[a-zA-Z0-9_-]`
- GET `/api/story-drafts`: metadata เท่านั้น; limit 1–100, offset >= 0, เรียง updated_at แล้ว ID
- GET `/api/story-drafts/{id}`: ข้อมูล config, revision, active_step และ validation issues
- PATCH `/api/story-drafts/{id}`: ส่ง config snapshot ทั้งชุด พร้อม `expected_revision` และ key ใหม่ต่อการแก้ไข
- GET `/api/diagnostics/drafts`: metadata ไม่มีเนื้อหา สำหรับ AI/support ตามสิทธิ์
- GET `/api/diagnostics/drafts/{id}/events`: audit ไม่มีเนื้อหา; after >= 0, limit 1–100

ตัวอย่างสร้างผ่าน HTTP client ที่มี Bearer token:

```json
{"schema_version":1,"active_step":0,"config":{"topic":"","storyText":"แนวทางที่ยังเขียนไม่เสร็จ"}}
```

Config ที่ขาด field ใช้ default จาก registry; PATCH เป็น snapshot ไม่ใช่ merge รายช่อง
กรอกไม่ครบหรือค่าระหว่างพิมพ์ เช่น scenes `-` บันทึกได้พร้อม issue; ไม่ใช่การอนุมัติให้เริ่มงาน
ชนิดข้อมูลผิด/field ไม่รู้จัก/ข้อความเกินขนาดถูกปฏิเสธ; version 1 และขั้น 0–4 เท่านั้น
คงค่าที่ซ่อนตามเงื่อนไขด้วย และไม่สร้าง jobs/receipts จากการบันทึกแบบร่าง
ไฟล์ใน config เก็บเป็น asset ID; server ตรวจว่าเป็นของ draft และ field เดียวกัน พร้อมใช้งานจริง
UI เปิดแบบร่างล่าสุดจาก API เมื่อเปิดโปรแกรมใหม่ และตรวจขั้นที่ผ่านแล้วใหม่จากค่าจริง

## Concurrency และข้อมูล

แต่ละ write ใช้ transaction เดียวสำหรับ draft, command receipt และ event
Key เดิม/payload เดิมคืน response เดิมรวม revision เดิม; caller ต้องไม่ตีความ retry ACK เก่าว่าเป็น revision ล่าสุด
Key เดิม/payload ต่างคืน `IDEMPOTENCY_CONFLICT`; expected revision เก่าคืน `DRAFT_REVISION_CONFLICT`
อ่าน GET ล่าสุดหลัง conflict แล้วให้ผู้ใช้ตัดสินใจ ไม่ overwrite โดยไม่รู้ตัว
Owner scope ปัจจุบันเป็น local workspace ต่อ data directory; token เปลี่ยนไม่ทำให้ draft หาย
Service ตรวจ scope อีกชั้น; ยังไม่ใช่ multi-account ownership ตาม [Security](../operations/security.md)
Owner/operator ได้ read/write; viewer ได้ read; support ได้เฉพาะ diagnostics
ทุก endpoint มี token/policy แม้ dev bypass; ไม่มี bypass สำหรับ route ใหม่

## Storage และการตรวจ

`story_drafts` เก็บ config/revision, `draft_commands` เก็บ idempotent response, `draft_events` เก็บ audit ที่ไม่มีเนื้อหา
DB และ backups มีข้อมูลส่วนตัวของงาน จึงไม่ส่งออกทั้งไฟล์ใน support bundle และไม่ commit Git
Logs มี draft_id/revision/trace_id แต่ไม่มีหัวข้อ ข้อความ หรือไฟล์แนบ
Schema registry เป็นของ backend; frontend parity test ตรวจว่าทั้ง 95 ช่องถูกครอบคลุม
การเพิ่มช่องต้องอัปเดต registry/schema version ตาม compatibility ไม่คัด registry ใหม่ทับโดยไม่ review
รายละเอียด backup/rollback: [Storage](storage.md)

Source: [contracts](../../backend/smartflow/draft_contracts.py), [registry](../../backend/smartflow/draft_fields.json),
[service](../../backend/smartflow/drafts.py), [routes](../../backend/smartflow/draft_routes.py),
[models](../../backend/smartflow/draft_models.py)
Tests: [draft API](../../tests/test_drafts.py), [migration](../../tests/test_migration_safety.py)
Scopes: `story-api`, `migration`, `auth`; [verification](../delivery/verification-draft-extension-foundation.md)

## Autosave และปิดหน้าต่าง

Debounce 350 ms; มี write เดียวที่กำลังส่ง และรวม edits ล่าสุดหลัง ACK
คำสั่ง/ไฟล์ที่ตอบกลับไม่ถึงลองซ้ำได้สูงสุด 3 ครั้งด้วย key และ payload เดิม
ไม่ retry validation/permission/conflict; แสดง error code และ trace โดยเก็บ edits ไว้
Conflict ต้องเลือกโหลดข้อมูลล่าสุดเอง; ไม่ merge หรือ overwrite เงียบ ๆ
Native close ถูกยกเลิกก่อน รอ flush แบบ async; error/conflict ไม่ปิดหน้าต่าง
Deadline 12 วินาทีแล้วคืนการใช้งาน UI; late callback ไม่สามารถปิดหน้าต่างหลังหมดเวลา
การ kill process/ไฟดับอาจเสีย edits ที่ยังไม่มี ACK; ไม่มีคำรับรองว่า unsaved memory จะอยู่รอด
Session เปลี่ยนล้าง private UI และหยุด store เดิม; คำตอบเก่าไม่เปลี่ยน session ใหม่

## ไฟล์แนบในเครื่อง

- POST `/api/story-drafts/{id}/assets?field=mainImage`: body เป็น bytes; ใช้ Idempotency-Key, X-File-Name (percent encoded), X-File-Size
- GET `/api/story-drafts/{id}/assets`: metadata/สถานะ missing; GET `/.../assets/{asset_id}` ตรวจ SHA-256 ก่อนส่ง bytes
- ตรวจ extension/signature เบื้องต้น, ขนาดจริง และเจ้าของ; ยังไม่ decode ตรวจวิดีโอ/ภาพทั้งไฟล์
- ไม่เกิน 500 MB/ไฟล์, 2 GB/แบบร่าง และ 200 records; ยังไม่มี retention/GC จึงนับไฟล์ที่เลิกอ้างอิงด้วย
- สำเนาอยู่ `draft-assets/<uuid>.bin` ใต้ data directory; ไม่เปลี่ยนต้นฉบับ ไม่เก็บ original path
- จอง ID ใน DB ก่อนเขียน, lock ราย asset, fsync/atomic replace และ audit ใน transaction
- Retry เก็บ ID เดิม; เก็บกวาดเฉพาะ `.part` ของ asset ที่ถือ lock หลัง crash
- ไฟล์หายต้องเลือกแทน; ไม่ลบ reference หรือสร้างงานใหม่เพื่อกลบปัญหา
- UI ไม่ส่งไฟล์ออกไปบริการภายนอก; raw DB/backups/asset directory เป็นข้อมูลส่วนตัว

Source: [persistence store](../../frontend/src/features/story-shorts/persistence.ts),
[assets](../../backend/smartflow/assets.py), [close guard](../../backend/smartflow/desktop_close.py)
