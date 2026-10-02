# Story draft persistence: proposed contract

สถานะ: แผน ยังไม่มี draft tables/routes หรือ autosave ใน source
แผนทำคู่กับ Extension: [Coordinated plan](story-extension-milestones.md)
ฟอร์มที่ต้องเก็บครบ: [Story form](../architecture/story-form.md)

## ผลลัพธ์ที่ต้องได้

- กรอกไม่ครบก็บันทึกได้; เปิดโปรแกรมใหม่แล้วได้ข้อมูล ขั้นปัจจุบัน และไฟล์ที่นำเข้าสำเร็จกลับมา
- แสดงกำลังบันทึก/บันทึกแล้ว/บันทึกไม่สำเร็จ โดยอ้างอิง ACK จาก backend
- เปลี่ยนเมนูหรือรีสตาร์ตไม่สร้าง provider operation และไม่เพิ่มงานเข้าคิว
- บันทึกค่า option ที่ยังไม่รองรับได้ แต่ห้ามเริ่มงานด้วย capability ที่ยังไม่พร้อม

## Schema และการแก้ไขชนกัน

`story_drafts`: ID, owner scope, schema version, revision, config, active step, updated time
`draft_assets`: ID, draft owner, safe display name, storage key, size, MIME, hash และสถานะ import
Config เก็บทุกช่องรวมช่องที่ซ่อนไว้; selected file arrays เปลี่ยนเป็น asset IDs
แยก drafts ที่แก้ได้จาก immutable story revisions เมื่อเริ่มงานจริง
Backend ตรวจชนิด/ขนาด/schema ตอน save แต่ยอมรับช่องว่างและค่าระหว่างกรอก
ค่าที่ไม่เข้ากันหรือกรอกไม่ครบคืน validation issues; ตรวจ required/capability อีกครั้งตอนเริ่มงาน
UI ไม่เชื่อ completed flags ที่บันทึกมาโดยตรง ต้องตรวจข้อมูลเมื่อโหลดกลับ

Autosave ใช้ debounce และหนึ่ง write ที่กำลังส่งต่อ draft; รวมการแก้ล่าสุดระหว่างรอ
ทุก write มี expected revision และ idempotency key; key เดิม payload เดิมได้ผลเดิม
ถ้า timeout ให้ใช้ key เดิมตรวจ/ลองคำขอเดิมก่อนส่งการแก้รุ่นใหม่
Revision ไม่ตรงคืน conflict พร้อม revision ปัจจุบัน; ไม่ overwrite หรือ merge ทับข้อมูลเงียบ ๆ
การเก็บ local pending state ต้องแยกตาม session/owner และไม่เปิดข้อมูลหลังสิทธิ์ถูกถอน
ไม่เก็บ token หรือเนื้อหางานใน localStorage/log เพื่อแก้ปัญหา autosave

## API ที่เสนอ

| Route | Permission / contract |
|---|---|
| POST /api/story-drafts | stories:drafts:write; idempotent create |
| GET /api/story-drafts | stories:drafts:read; list metadata และ pagination |
| GET /api/story-drafts/{id} | stories:drafts:read; owner check; config/revision/assets |
| PATCH /api/story-drafts/{id} | stories:drafts:write; expected revision + idempotency key |
| POST /api/story-drafts/{id}/assets | stories:drafts:write; bounded import + idempotency key |
| GET /api/story-drafts/{id}/assets/{asset_id} | stories:drafts:read; ตรวจ ownership ก่อนอ่าน |

Owner/operator อ่านและแก้ได้; viewer อ่านได้ภายใน scope ที่ได้รับ
Support และ Extension agent ไม่มีสิทธิ์อ่าน draft content; diagnostics เป็น projection ที่ตัดเนื้อหาออก
ทุก route มี token, policy และ allow/deny tests; dev bypass ไม่ข้าม permission
API รับ asset IDs ไม่รับ arbitrary path; ไม่ส่ง path จริงกลับ client
สิทธิ์สำหรับ draft เป็นข้อเสนอใหม่ ต้องเพิ่มใน role matrix/OpenAPI ก่อนเปิด UI

## ไฟล์แนบและการปิดโปรแกรม

นำไฟล์เข้า private managed storage ในเครื่อง; สำเร็จหลัง atomic persist และ metadata commit
กำหนด type/size/count/total quotas ฝั่ง backend และไม่ buffer ไฟล์ใหญ่ทั้งไฟล์
Upload ที่ขาดหรือ ACK หายต้องกู้/ตรวจ import เดิม; ไม่สร้าง asset ซ้ำ
ไฟล์หายหรือเสียแสดง asset error และขอเลือกใหม่เฉพาะไฟล์นั้น ไม่ทำหายทั้ง draft
การเอาไฟล์ออกจาก draft ไม่ลบไฟล์ต้นฉบับของผู้ใช้; GC จัดการเฉพาะ temporary/unreferenced managed files ที่พิสูจน์เจ้าของได้
เมื่อปิดตามปกติให้ flush pending changes และรอ ACK แบบมี deadline ก่อนปิด
Save ล้มเหลวหรือ import ยังไม่ครบต้องคงหน้าต่างและแจ้งเหตุ; ห้ามปิดแล้วอ้างว่าบันทึกแล้ว
กรณี process crash รับรองกู้คืนเฉพาะข้อมูลที่ backend ACK แล้ว ไม่อ้างว่า keystroke ล่าสุดถูกบันทึกเสมอ
แบบร่างในหน้าต่างเก่าต้องรักษาไว้ก่อน activation; ไม่ reload เพื่ออัปเกรดแล้วทิ้งค่าที่อยู่ใน memory

## Diagnostics และ gate

Log: draft ID, revision, request/trace ID, stage, reason, elapsed; ไม่มีหัวข้อ ข้อความ filename/path หรือ bytes
Codes ที่เสนอ: DRAFT_REVISION_CONFLICT, DRAFT_SAVE_FAILED, DRAFT_ASSET_INVALID, DRAFT_ASSET_MISSING
แยก invalid input, permission denied, unavailable storage, conflict และ import incomplete
ก่อน migration จริงต้องมี backup ที่รองรับ SQLite WAL, integrity verification และ recovery เมื่อ migration ล้มเหลว
ใช้ฐาน fixture ตรวจ migration ก่อนแตะข้อมูลจริง; ห้าม reset DB เพื่อให้ schema ผ่าน
เกณฑ์ทดสอบและจุดส่งตรวจอยู่ใน [Milestones](story-extension-milestones.md)
