# Story drafts + Extension: coordinated implementation plan

สถานะ: P2 ทำแล้วใน source Dev; P3 งานจำลองผ่าน Extension อยู่ใน source แล้ว (commit cc717a8) แต่ยังมีงานค้างด้านล่าง
Integration handoff P4 ยังต้องทำต่อ
หลักฐาน: [P2 verification](../delivery/verification-autosave-pairing.md)
ทำสองสายงานใน milestone เดียวกัน โดยใช้ contract ร่วม ไม่รอให้ Story workflow ครบก่อนเริ่ม Extension
Framework ตามแผนเดิม: React/TypeScript + FastAPI/SQLite; Extension ใช้ WXT/TypeScript/MV3 + React popup และ Python native host
ตรวจและล็อก dependency versions ตอนเริ่ม implementation; ไม่คัดลอก runtime ของโปรเจกต์เก่า

## ลำดับส่งตรวจ

| รอบ | สาย Story draft | สาย Extension | สิ่งที่ตรวจได้เมื่อจบรอบ |
|---|---|---|---|
| P0 Contracts | Schema ครบทุกช่อง, incomplete draft, assets, revisions, permissions/errors | Envelope/version, pairing, agent permissions, disconnect และ fake command | ตัวอย่าง request/response และ schema/permission tests; ทั้งสองฝั่งใช้สัญญาเดียวกัน |
| P1 Storage + skeleton | Backup/integrity/recovery สำหรับ migration; draft API และ metadata ด้วย fixture DB | WXT skeleton, popup สถานะ, native framing และ fake transport | ยิง draft API แล้วอ่านกลับได้; build Extension และ protocol unit ผ่าน |
| P2 Autosave + pairing | Autosave, import ไฟล์, resume wizard, conflict feedback และ close flush | Native host บน Windows, pairing nonce, scoped credential, revoke, version check | ปิด–เปิดแอปแล้วข้อมูล/ขั้น/ไฟล์กลับมา; Extension จับคู่จริงใน profile ทดสอบได้ |
| P3 Recovery + simulated job | Snapshot draft เป็น revision; readiness/heartbeat, operation receipt และ diagnostic projection | Claim/preflight/dispatch grant/events, restart/reconnect และ fake provider adapter | งานจำลองจาก draft ผ่านแอป–host–Extension–backend; crash/ACK หายไม่ส่งซ้ำ |
| P4 Integration handoff | สถานะงาน/ข้อผิดพลาด/ผลจำลองและการอ่าน log/DB ผ่านสิทธิ์ที่ถูกต้อง | App/helper/Extension version pairing, dev activation และคำแนะนำเฉพาะเมื่อ blocked | ตรวจ end-to-end ด้วย fixture และรายงานหลักฐานแต่ละชั้น; พร้อมวาง live pilot |

แต่ละรอบแยก commit ของ contract/backend/UI/Extension เท่าที่ review ได้ ไม่รวมทุกอย่างเป็นก้อนเดียว
ไม่จำเป็นต้องเปลี่ยน UI ทุก commit; เมื่อเปลี่ยน UX/UI ต้อง build และปิด–เปิด desktop ตาม [Setup](../development/setup.md)

## งานค้างของ P3

ต้องปิดก่อนนับ P3 ว่าผ่านเกณฑ์ "crash/ACK หายไม่ส่งซ้ำ" และก่อนเริ่ม P4

- Worker: `stories.maintain()` ไม่มี error handling; SQLite busy ครั้งเดียวทำ worker ตายและกินโควตา restart 3 ครั้ง
- `sync()` ซ้ำจาก connection เดิมระหว่าง lease ยังไม่หมด เปลี่ยนงานปกติเป็น `needs_review` โดยไม่มี error code
- งานที่ส่งไม่แน่ใจและผูกกับ pairing ที่ถูก revoke จะค้างถาวร; ให้ย้ายเจ้าของเพื่อ inspect เท่านั้น ห้ามให้ grant ใหม่
- `create()` hash ไฟล์แนบ (สูงสุด 500MB) ขณะถือ `BEGIN IMMEDIATE`; autosave อาจรอจน busy timeout
- งานที่เกิน deadline/observation ใน `sync()` บล็อกงานถัดไปของ pairing เดียวกัน
- Alarm ของ Extension ทุก 30 วินาที แต่ช่วง connected มี 15 วินาที สถานะจึงกะพริบ
- `create()` ควรปฏิเสธเมื่อ `completeness()` ไม่ว่าง ไม่ใช่ตรวจแค่ `issues()` และ topic
- Readiness/heartbeat ของ worker (F2) ยังไม่มี; `worker_alive` ยังหมายถึง process อยู่เท่านั้น
- Diagnostics read-only ยังไม่ project ตาราง `story_operations`/`operation_receipts`
- เอกสาร [Story data/API](story-data-api.md), [Extension protocol](extension-protocol.md),
  [Storage](../architecture/storage.md), [API](../operations/api.md) และ [Security](../operations/security.md) ยังไม่ตรงกับ P3 ที่ implement

## Dependencies ที่ต้องเคารพ

- P0 มาก่อนการเชื่อมสองฝั่ง; draft API แยกจาก create job และ provider dispatch
- ส่วน F3 ที่จำเป็นต่อ backup/migration มาก่อนเพิ่ม schema ในฐานข้อมูลจริง
- P1 Extension ทำกับ fake transport ได้ระหว่างงานฐานข้อมูล; ไม่ต้องรอ autosave เสร็จ
- P2 จับคู่ได้ไม่เท่ากับทำงานกับ ChatGPT ได้; content adapter ยังไม่มี live proof
- F2 readiness/recovery และ per-operation receipts ต้องผ่านใน P3 ก่อนเปิด provider จริง
- ส่ง revision/config snapshot ให้ operation; การแก้ draft ภายหลังไม่เปลี่ยนงานที่ dispatch ไปแล้ว
- P4 ใช้ profile/Extension identity/host name ของระบบใหม่; ไม่ reload Extension หรือกระทบงานระบบเก่า

## กติกาความปลอดภัยและ diagnostics ร่วม

Backend เป็นเจ้าของ queue, state, lease และ receipt; popup/content script ไม่ตัดสินความสำเร็จเอง
จับคู่ด้วย nonce อายุสั้นใช้ครั้งเดียวและ Extension ID ที่อนุญาต; เก็บ host credential ด้วย Windows user protection
Agent ได้เฉพาะ claim/events/artifacts ของ operation ที่ได้รับ ไม่มี owner token หรือสิทธิ์อ่าน draft/DB ทั้งหมด
Unknown/accepted send ต้อง inspect/collect คำขอเดิม; ห้าม replay หลัง reconnect แม้ local ACK หาย
Logs มี trace/request/job/operation IDs ตามขั้นที่มีจริง พร้อม stage/reason/attempt/deadline
เนื้อหาเรื่อง prompt token cookies media และ path ส่วนตัวไม่อยู่ใน logs/support bundle
AI ตรวจผ่าน API/CLI, events และ read-only DB projection ที่มีสิทธิ์ ไม่เปิด raw SQL endpoint
ข้อผิดพลาดที่กู้ได้ต้อง retry แบบมี budget; เหตุ login/CAPTCHA หรือ send ไม่แน่ใจต้องเก็บ checkpoint และแจ้งเหตุที่เจาะจง

## แผนเทสให้เร็ว

| ขอบเขต | เคสสำคัญ |
|---|---|
| Draft unit/API | incomplete save, restore ทุก field, conditional fields, idempotency, revision conflict, allow/deny |
| Storage/assets | WAL backup, migration failure recovery, interrupted import, oversize/type/ownership, missing file |
| UI focused | autosave status, edit ระหว่าง save, stale response, restart restore, close-save failure |
| Extension unit | schema/sender validation, version mismatch, framing truncation/oversize, service worker restart |
| Bridge contracts | nonce expiry/reuse, revoke, stale lease, duplicate grant/result, accepted/unknown ไม่ replay |
| Integration | Windows native handshake, fixture job, worker stall/recovery และ artifact ACK หลัง persist |

เพิ่ม scopes/mappings ให้ runner เมื่อสร้าง module; เลือกเฉพาะส่วนที่แก้และ affected contracts
ใช้ fake clock/events สำหรับ timeout; ไม่เปิด Chrome หรือรอ provider ใน unit tests
ตั้งเป้า unit เป็นวินาทีและ integration เล็กต่ำกว่าหนึ่งนาที แล้วรายงานเวลาจริงแยก build/setup
P4 ที่รวมหลายระบบต้องผ่าน release/integration gate ตามขอบเขตจริง; ไม่รัน full suite ซ้ำในทุก commit
การผ่าน fixture, native handshake, packaged activation และ provider output เป็นหลักฐานคนละชั้น

## ขอบเขตหลังแผนนี้

ขั้นถัดไปจึงเปิด live pilot ChatGPT Web: หนึ่งบท → หนึ่งภาพ → หลายฉาก พร้อมตรวจ artifacts จริง
เสียง/ซับ/render, Gemini/Flow/Meta จริง และ installer ลูกค้าเป็น milestone ถัดไป
ฟอร์มเก็บตัวเลือกอนาคตได้ แต่ปุ่มเริ่มงานต้องปฏิเสธ capability ที่ยังไม่พร้อมด้วยเหตุที่ชัดเจน
การส่งชุดลูกค้าต้องจับคู่ main app/helper/Extension และผ่าน clean Windows ก่อนเรียก client-ready

## เอกสารเจ้าของแต่ละเรื่อง

- [Draft persistence](draft-persistence.md): data/save/assets/close contracts
- [Story data/API](story-data-api.md): immutable revisions, operations และ artifacts
- [Extension framework](browser-extension.md): modules, native transport และ installation
- [Extension protocol](extension-protocol.md): grants, receipts, reconnect และ recovery
- [Focused tests](story-testing.md): cases/scopes และ live proof
- [Foundation](foundation.md): F2/F3/F4/F5 gates
