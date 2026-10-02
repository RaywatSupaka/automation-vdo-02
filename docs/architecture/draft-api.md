# Story draft API: first implementation

ทำแล้ว: schema 95 ช่อง, draft API, revision/idempotency, audit events และ migration `0002`
ยังไม่ทำ: UI autosave/restore, นำเข้าไฟล์, close flush, snapshot ไปเป็นงาน และ provider dispatch
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
ไฟล์ตอนนี้รับเฉพาะ array ว่าง; asset reference ที่ยังตรวจเจ้าของไม่ได้คืน `DRAFT_ASSET_UNAVAILABLE`
UI ฟอร์มปัจจุบันยังไม่เรียก API นี้ จึงยังหายเมื่อปิด/reload จนกว่าจะต่อ autosave ในรอบถัดไป

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
