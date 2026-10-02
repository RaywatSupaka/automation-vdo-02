# Story Shorts: proposed data and API contracts

**แผน ยังไม่มี tables/routes/permissions ต่อไปนี้ใน source**
เจ้าของ business rules คือ backend service; React และ Extension ไม่เปลี่ยน DB state โดยตรง
ฐานปัจจุบัน: [Storage](../architecture/storage.md), [API](../operations/api.md), [Security](../operations/security.md)

## ข้อมูลและ ownership

| Entity ที่เสนอ | หน้าที่ |
|---|---|
| story_revisions | immutable input/plan/config revision และการตรวจ schema |
| story_scenes | stable scene ID, ordinal, narration, image prompt, target duration และ reference IDs |
| operations | job/revision/scene/kind, operation ID, command ID, lease epoch และ dependencies |
| operation_receipts | หนึ่ง receipt ต่อ external operation; request ID, dispatch/acceptance evidence และสถานะ |
| artifacts | job/revision/scene/operation, kind, hash, MIME, size, duration และตำแหน่งภายใน workspace |

Receipt ปัจจุบันรองรับ workflow หนึ่งขั้น; ต้องเพิ่มระดับ operation ก่อนใช้หลายฉาก
ไม่ overwrite receipt เดิมให้กลายเป็นฉากถัดไป; migration ต้องผ่าน backup/integrity/rollback ของ F3
ตั้ง unique constraints สำหรับ command, receipt และ artifact identity เพื่อป้องกัน callback ซ้ำ
คง job trace เดิม เพิ่ม operation ID และ command trace ใน events/logs

Plan schema มี title, summary, visual_bible และ `scenes[]` ที่มี ID/ordinal/narration/image_prompt/target_seconds
ตรวจ scene count, ordinal, ขนาดข้อความ, duration budget และ reference ownership ก่อน dispatch
ข้อความจาก provider เป็นข้อมูล ไม่ใช่คำสั่งให้เปิดไฟล์ รัน shell หรือเปลี่ยนสิทธิ์
การ parse/validate ที่ล้มเหลวเก็บผลต้นฉบับใน private job storage; ไม่ยิง provider ซ้ำโดยอัตโนมัติ

## API ที่เสนอ

| Route | Permission / หลักการ |
|---|---|
| POST /api/stories | jobs:create; Idempotency-Key; สร้าง job และ input revision |
| GET /api/stories/{id} | jobs:read; scene progress และ artifact metadata |
| POST /api/stories/{id}/revisions | stories:edit; expected revision; conflict เมื่อ revision เปลี่ยน |
| POST /api/stories/{id}/approve | jobs:command; อนุมัติ revision ที่ระบุเท่านั้น |
| POST /api/stories/{id}/scenes/{scene_id}/regenerate | stories:edit; เจตนาสร้างใหม่พร้อม key และ revision |
| GET /api/stories/{id}/artifacts/{artifact_id} | jobs:read; ตรวจเจ้าของและ path จาก DB ไม่รับ arbitrary path |

ใช้ cancel/resume/reconcile ผ่าน job command contract เดิมหลังตรวจ compatibility
Owner/operator ได้ stories:edit; viewer อ่านได้; support ใช้ diagnostic projection ที่ไม่มีบท/ภาพ
ทุก route ต้องประกาศ policy และมี allow/deny tests; dev bypass ยังตรวจ token/permission
เรื่องบัญชีลูกค้า/license แยกจาก local API authentication; ไม่เก็บ admin/owner token ใน Extension

## Revision และการทำต่อ

- เปลี่ยนฉากแล้ว invalidate เฉพาะ descendants ตาม dependency fingerprint
- Fingerprint รวม prompt/reference hashes, provider/model/config และ revision ที่เกี่ยวข้อง
- narration เปลี่ยนต้องคำนวณเสียง/timing/render ใหม่; ไม่ลบภาพเก่าที่ไม่เกี่ยว
- งาน accepted/unknown ของ revision เก่ายังคง receipt แม้ผู้ใช้สร้าง revision ใหม่
- ปฏิเสธ regenerate ขณะที่มี send ไม่ทราบผลของฉากเดียวกันจน reconcile/ผู้ใช้ยืนยันความเสี่ยงอย่างชัดเจน
- Cancel หยุดขั้นถัดไป; เก็บผลที่ provider ส่งกลับของ operation เดิมเพื่อการตรวจสอบ
- สถานะ completed ต้องมี artifact ผ่าน hash/type/duration และ render checks; progress 100% อย่างเดียวไม่พอ

## Diagnostics และ errors ที่จะเพิ่ม

เพิ่ม code เฉพาะ boundary เช่น STORY_PLAN_INVALID, STORY_REVISION_CONFLICT,
TTS_ACCEPTANCE_UNKNOWN, MEDIA_INVALID และ RENDER_FAILED โดยใช้ error envelope เดิม
Event เก็บ stage/scene ID/reason/attempt/deadline; support bundle ไม่รวมบท ภาพ เสียง หรือ provider page
Details สำหรับ AI อ่านผ่าน authenticated diagnostics และ read-only DB projection; ไม่เปิด raw SQL ผ่าน API
Recovery ของ browser อยู่ใน [Extension protocol](extension-protocol.md)
