# Extension protocol: proposed dispatch and recovery contract

**แผน ยังไม่มี browser-agent endpoints หรือ protocol นี้ใน source**
สืบทอดข้อกำหนด [Automation](../architecture/automation.md); ไม่ลดระดับการป้องกัน accepted/unknown send
Transport/pairing: [Browser extension](browser-extension.md)

## Envelope และสิทธิ์

Message มี protocol_version, message_id, operation_id, command_id, job_id, revision_id,
scene_id เมื่อเกี่ยวข้อง, lease_epoch, trace_id, kind และ typed payload
Backend ออก operation/lease IDs; agent ไม่เลือก job อื่นหรือย้าย artifact ข้ามงานเอง
Provider inputs เป็น private payload; log เก็บเฉพาะ allowlisted metadata และ hashes
กำหนด schema, enum, size limits และ reject unknown privileged commands ที่ protocol boundary

Agent credential มีเฉพาะ browser:claim, browser:events, browser:artifacts ตาม operation lease
ไม่มี jobs:create, global diagnostics, raw database หรือ arbitrary file/shell permission
Claim ผูกกับ paired installation และ provider; callbacks ตรวจ operation, lease epoch และ artifact ownership
Expired lease ปิดสิทธิ์ dispatch ใหม่; ผลเก่าที่มาช้าเข้า read-only reconciliation ตาม command เดิม
เริ่ม pilot ด้วยหนึ่ง active provider operation ต่อ paired browser เพื่อคุม tab/reference ownership

## ลำดับและจุด commit

1. Backend สร้าง operation/receipt prepared และมอบ lease; claim ซ้ำคืน command เดิม
2. Agent ตรวจ tab/document/conversation และ composer/reference manifest โดยยังไม่กดส่ง
3. ก่อนส่ง Agent ขอ dispatch grant; Backend commit dispatch marker และ event ก่อนตอบ grant
4. Grant ผูก agent connection/epoch ใช้ได้ครั้งเดียว; ไม่ออก grant ซ้ำเมื่อ receipt เป็น dispatching ขึ้นไป
5. Agent ที่รับ grant สดส่งได้ครั้งเดียว; หลัง reconnect/restart ให้ inspect เท่านั้นแม้ไม่พบ local ACK
6. Provider acceptance ต้องมีหลักฐานของคำขอนี้; ACK ว่ารับ command ไม่ใช่หลักฐาน provider รับ prompt
7. Agent observe/collect ผลเดิม; Backend ตรวจและบันทึกไฟล์แล้วจึง ACK artifact persisted
8. เมื่อ receipt และ artifact พร้อมจึง advance ขั้นถัดไปใน transaction ของ backend

หาก crash ระหว่าง commit marker กับส่งจริง อาจต้องพักเพราะไม่รู้ผล; ห้ามเดาว่ายังไม่ได้ส่งแล้ว replay
ไม่อ้าง exactly-once กับเว็บภายนอกที่ไม่มี idempotency API; เน้นไม่ส่งซ้ำเมื่อหลักฐานไม่พอ
Grant หมดอายุใช้ส่งไม่ได้; การตรวจ deadline และ connection state ต้องอยู่ก่อน side effect ทันที

## Recovery matrix

| เหตุ | การทำต่อ |
|---|---|
| หลุดก่อน dispatch marker | preflight/claim ใหม่ภายใน retry budget |
| marker แล้ว แต่ ACK หาย | unknown; ตรวจคำขอใน conversation เดิม ไม่ส่ง prompt ซ้ำ |
| provider accepted แล้ว service worker หยุด | reconnect แล้ว inspect/collect ผลเดิม |
| upload/ACK artifact หาย | ส่ง bytes ผลเดิมซ้ำด้วย artifact ID/hash; ไม่ generate ใหม่ |
| lease/tab/document เปลี่ยน | หยุด dispatch; ตรวจ ownership ใหม่ก่อน inspect |
| draft ที่พิสูจน์ว่า operation นี้สร้างก่อน send | bounded cleanup เฉพาะ draft/attachments ที่เป็นเจ้าของ แล้วตรวจซ้ำ |
| draft ของผู้ใช้หรือเจ้าของไม่ชัด | เก็บ checkpoint และแจ้ง blocker; ไม่ล้าง composer |
| page login/CAPTCHA | waiting พร้อมเหตุและคำแนะนำเฉพาะ; ไม่วน retry login |
| result deadline หมด | persist stage/reason; inspect แบบจำกัดจำนวน แล้ว needs_review ถ้ายังไม่ชัด |

Retry budget แยก preflight/observe/artifact; เพิ่ม attempt counter อย่าง durable และไม่มี retry ซ้อนจนไม่จำกัด
ให้ error code เช่น EXTENSION_DISCONNECTED, EXTENSION_VERSION_MISMATCH, PROVIDER_LOGIN_REQUIRED,
COMPOSER_NOT_READY, TAB_OWNERSHIP_CHANGED, SEND_ACCEPTANCE_UNKNOWN และ ARTIFACT_WRITE_FAILED

## Artifact transfer

- ส่งแบบ chunks มี total size, ordinal, content hash และ bounded buffering/backpressure
- ขนาดแต่ละ message ต่ำกว่า transport limits; ทดสอบ oversize/truncation และ duplicate/out-of-order chunks
- Host/Backend กำหนดปลายทางจาก job/artifact IDs; reject path traversal, arbitrary paths และ unapproved URLs
- ตรวจ MIME/decoded media/hash ก่อน atomic persist; invalid bytes ไม่ถือเป็น completion
- หากต้องดาวน์โหลด URL ให้ตรวจ scheme/origin/redirect/size และห้ามไป internal network ตาม URL จากหน้าเว็บ
- ACK หลังไฟล์ persisted; ระบุผลว่า generated/collected/persisted แยกกันเพื่อวิเคราะห์ crash

Focused cases และ live gate: [Story testing](story-testing.md)
