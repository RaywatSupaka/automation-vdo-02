# Story draft persistence

ทำแล้ว: schema 95 ช่อง, API, Autosave/restore, ไฟล์แนบ, close flush และ migration `0003`; เริ่มงานจำลองจาก revision ที่บันทึกแล้ว
ยังไม่ทำ: provider จริง, การสร้างสื่อจริง และระบบจัดการแบบร่างหลายรายการใน UI
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
UI เปิดแบบร่างล่าสุดจาก API เมื่อเปิดโปรแกรมใหม่ และตรวจขั้นที่ผ่านแล้วใหม่จากค่าจริง
ขั้นตรวจรายละเอียดเรียก `flush()` ก่อนส่ง `POST /api/stories` พร้อม draft ID, expected revision, mode `simulation`
และ Idempotency-Key เดิมเมื่อ retry; revision เปลี่ยนจึงใช้ key ใหม่ ถ้าบันทึกไม่สำเร็จจะไม่เรียก start API
ปุ่มเริ่มงานปิดเมื่อ server issues ยังมีอยู่; backend ตรวจซ้ำและบังคับสิทธิ์ `jobs:create`

## Issues และไฟล์ใน config

Response ของ POST/PATCH/GET มี `issues` เรียงตาม: `issues()` ค่ารายช่อง, `completeness()`, แล้ว `DRAFT_ASSET_MISSING`
`DraftIssue.code`: VALUE_OUT_OF_RANGE, OPTION_INVALID, DRAFT_ASSET_MISSING, FIELD_REQUIRED
แบบร่างไม่ครบยังบันทึกได้ (201/200) เช่นแบบร่างใหม่มี topic FIELD_REQUIRED; replay key เดิมคืน issues เดิมที่เก็บไว้
กติกา required/conditional อยู่ใน registry: `required`, `when` {field, equals}, `maxLines`, `maxCountOf`, `optionsUpTo`
`completeness()` รายงานช่องบังคับที่ active แต่ว่าง, batchTopics เกิน 10 บรรทัด, musicCount เกินจำนวน musicFiles
และ coverScene นอก `auto`/1..min(15, scenes); รายงานอย่างเดียว ไม่บล็อกการบันทึก
ตัวเลขใน completeness อ่านด้วย `number()` ตามกติกา JavaScript `Number()` ให้ตรง UI (ASCII, 0x/0o/0b, Infinity, ว่าง = 0)
Job start ตรวจ `issues()` และ `completeness()` รวมทั้ง assets ก่อนสร้าง snapshot งานจำลอง; แบบร่างที่ยังมี issue เริ่มงานไม่ได้
ไฟล์ใน config เก็บเป็น asset ID; ID ซ้ำใน field เดียว, ไม่รู้จัก, ของ draft อื่น หรือนำเข้าให้ field อื่น คืน DRAFT_ASSET_INVALID (422)
อ้างอิงไฟล์ที่หาย/เสียใหม่ คืน DRAFT_ASSET_MISSING (409); ไฟล์ที่ config เดิมอ้างอยู่แล้วหายไม่บล็อก edits อื่น แต่ขึ้นใน issues ฟิลด์ละครั้ง
เอาไฟล์ที่หายออกแล้วใส่กลับถือเป็นการอ้างอิงใหม่และถูกปฏิเสธ; replay ยังคืน response เดิมแม้ไฟล์หายภายหลัง

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
Tests: [draft API](../../tests/test_drafts.py), [migration](../../tests/test_migration_safety.py),
[draft rules](../../tests/unit/test_draft_rules.py) (ตาราง scenes `SCENE_OPTION_COUNTS` ใช้ร่วมกับ
[UI parity](../../frontend/src/features/story-shorts/persistence-contract.test.ts) ที่ตรวจ options/min/max/step/required/when/cross-field)
Scopes: `story-api`, `migration`, `auth`; [verification](../delivery/verification-draft-extension-foundation.md)

## Autosave และปิดหน้าต่าง

Debounce 350 ms; มี write เดียวที่กำลังส่ง และรวม edits ล่าสุดหลัง ACK
AppError แบบมีโครงสร้างหรือ 4xx ไม่มีโครงสร้าง (ยกเว้น 408/429) = transaction ไม่ commit; ทิ้ง request เดิม
ครั้งถัดไปส่ง snapshot ใหม่ด้วย Idempotency-Key ใหม่และ expected_revision ปัจจุบัน (ยกเว้น conflict)
ACK หาย, timeout, INTERNAL_ERROR/DRAFT_SAVE_FAILED, 5xx/408/429 หรือ body 2xx อ่านไม่ได้ อาจ commit แล้ว
กรณีนั้นส่ง request เดิม (key/body เดิม) ซ้ำ สูงสุด 3 ครั้งต่อ flush ก่อนส่ง snapshot ที่ใหม่กว่า
แก้ไขระหว่างสถานะ error ตั้ง debounce 350 ms ตามปกติ; save ล้มขณะมี edit ใหม่รออยู่ตั้ง debounce ใหม่หนึ่งครั้ง
มีเฉพาะ edit ที่ตั้ง debounce จึงไม่มี retry loop; หลัง transient error จะ replay request เดิมก่อนแล้วค่อยส่ง snapshot ใหม่
ปุ่มลองใหม่และ close flush หลัง rejection ส่ง snapshot ใหม่หนึ่งครั้ง ไม่ส่ง request ที่ถูกปฏิเสธ; ไม่มีค่าค้างก็ไม่ส่งและคืน true
แสดง error เป็น `code · message · Trace: id` และเก็บ edits ไว้; UNAUTHORIZED เท่านั้นที่หยุด store และส่ง `smartflow-auth-lost`
PERMISSION_DENIED แสดง error โดยคง draft ใน UI; Conflict ต้องเลือกโหลดข้อมูลล่าสุดเอง ไม่ merge หรือ overwrite เงียบ ๆ
Server issues แสดงใต้สถานะบันทึก (`issueNotice`); ถ้าสถานะไม่ใช่ saved จะจางลงและบอกว่าเป็นผลบันทึกครั้งล่าสุด
`api()` และ draft transport ใช้ `readJson()`: error body ว่าง/ไม่ใช่ JSON/ไม่มี code เป็น `HTTP_<status>`
Trace มาจาก `error.trace_id` หรือ header `X-Trace-ID`; `ApiError.status` เป็น HTTP status (0 = ไม่มี response)
ทุกคำขอมี timeout 60 วินาที (`REQUEST_TIMEOUT_MS`) รวมกับ signal ของ caller; network/timeout ยังเป็น native exception
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
- หนึ่ง File ที่เลือกใช้ Idempotency-Key เดียวตลอดอายุ ไม่หมุน key หลังถูกปฏิเสธ เพราะ import จอง row ก่อน stream (กัน quota รั่ว)
- Import ที่ถูกปฏิเสธ (ยกเว้น UNAUTHORIZED, PERMISSION_DENIED, DRAFT_ASSET_BUSY) บันทึกไว้ที่ File นั้นและไม่อัปโหลดซ้ำ
- ช่องอื่นยังบันทึกโดยตัดไฟล์นั้นออก; สถานะ error แสดง code/trace และ close flush คืน false จนกว่าจะเอาออกหรือเลือกไฟล์ใหม่
- Client เขียน asset ID ซ้ำใน field เดียวเพียงครั้งเดียว; "ไม่ commit" ข้างต้นใช้กับ POST/PATCH draft เท่านั้น
- `Assets(db, clock=time.time)` รับ clock และส่งต่อให้ Drafts; `at` ของ asset_reserved/asset_saved มาจาก clock นี้
- ไฟล์หายต้องเลือกแทน; ไม่ลบ reference หรือสร้างงานใหม่เพื่อกลบปัญหา
- UI ไม่ส่งไฟล์ออกไปบริการภายนอก; raw DB/backups/asset directory เป็นข้อมูลส่วนตัว

Source: [persistence store](../../frontend/src/features/story-shorts/persistence.ts),
[assets](../../backend/smartflow/assets.py), [close guard](../../backend/smartflow/desktop_close.py), [api client](../../frontend/src/api.ts)
Tests: [persistence](../../frontend/src/features/story-shorts/persistence.test.ts), [api client](../../frontend/src/api.test.ts) scope `ui`;
[asset clock](../../tests/test_asset_clock.py) ยังไม่อยู่ใน focused scope; รันด้วย `python -m pytest` ตรง หรือ scope `backend`
