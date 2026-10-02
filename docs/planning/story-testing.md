# Story Shorts: focused verification plan

**ชื่อ scopes/เคสด้านล่างเป็นแผน ยังเรียกใช้ไม่ได้จน implementation เพิ่ม runner mappings**
ใช้ [Test selection](../development/test-selection.md) และเพิ่ม mapping พร้อมแต่ละ module
Unit tests ปกติไม่เรียก ChatGPT, ไม่คิดค่า TTS และไม่เปิด Chrome/EXE

## เลือกเทสตามขอบเขตที่แก้

| Scope ที่เสนอ | ตรวจอะไร | เมื่อใด |
|---|---|---|
| story-unit | schema, dependency fingerprint, revision invalidation, duration budget | เปลี่ยน business rules |
| story-api | typed response, validation, idempotency, allow/deny ทุก route | เปลี่ยน API/permissions |
| story-workflow | per-operation receipt, crash recovery, cancel, stale callbacks | เปลี่ยนคิว/ขั้นตอน |
| extension-unit | WXT/Vitest, restart state, sender validation, DOM fixtures | เปลี่ยน adapter/background |
| bridge-contract | framing/schema, pairing/auth, version, grant/ACK/dedup | เปลี่ยน protocol/native host |
| story-render | วิดีโอ fixture 2–3 ฉากสั้น ๆ, ซับ/เสียง/ffprobe/เฟรมแต่ละฉาก | เปลี่ยน render/timing |
| extension-smoke | Chrome ใหม่ใน profile ทดสอบ, helper handshake, lifecycle | เปลี่ยน browser/native integration |
| story-live | หนึ่งบท/หนึ่งภาพก่อนหลายฉาก; provider บัญชีทดสอบที่เลือกไว้ | activate adapter หรือ provider UI เปลี่ยน |

ตั้งเป้า pure unit เป็นวินาทีและ integration ขนาดเล็กต่ำกว่าหนึ่งนาที แล้ววัดจริงบนเครื่อง
ตัวเลขนี้เป็นเป้าหมาย ไม่ใช่ผล benchmark; รายงานเวลา setup/build/provider รอแยกจาก test execution
ไม่ run browser/live/full suite ทุกครั้งที่แก้ field, prompt template หรือเอกสาร
หากเปลี่ยน auth/protocol ที่กระทบทุก provider ให้เพิ่ม affected contracts ตามความเสี่ยงจริง

## เคสที่ต้องมีตั้งแต่แต่ละ boundary ถูกเพิ่ม

1. Request เดิมซ้ำได้ job/operation เดิม; key เดิมต่าง payload ได้ conflict
2. Planner ส่ง JSON เสีย/ฉากขาด/ID ซ้ำ/ข้อความเกินขนาด ต้องไม่เข้าสู่ image dispatch
3. Crash ก่อน/หลัง dispatch marker และ ACK หาย: send counter ไม่เพิ่มเพราะ resume
4. Accepted image กลับมาช้า, service worker restart, lease หมด: collect ผลเดิม ไม่มี submit ซ้ำ
5. Tab ถูก navigate หรือมี draft คนละงาน: ไม่มี destructive cleanup และมี exact blocker
6. มี attachment ฉากก่อน, Stop indicator ค้าง, duplicate result: ไม่ผูกผลผิด scene
7. Artifact persist ล้มเหลว/ส่ง chunks ซ้ำ: retry เก็บ bytes เดิม, hash ตรง, advance ครั้งเดียว
8. TTS accepted แล้ว poll ล้มเหลว: ใช้ external request เดิม ไม่สร้างงานเสียงคิดเครดิตซ้ำ
9. เปลี่ยน narration ฉากเดียว: invalidate เสียง/timing/render ที่เกี่ยว โดยเก็บภาพที่ยังใช้ได้
10. Cancel และ stale callback แข่งกัน: ไม่เปิดขั้นถัดไป แต่คง receipt/หลักฐานผลเดิม
11. Viewer/support/agent/invalid token เรียก route เกินสิทธิ์ไม่ได้; forged role/job/lease ไม่ผ่าน
12. Logs/support bundle ไม่มี prompt, title, token, user path, provider output หรือ media
13. MP4 decode ได้ ทุกฉากมีเฟรม เสียง/ซับสัมพันธ์กับเวลาจริง และไม่ข้ามฉากโดยเงียบ

Fixtures เป็นข้อมูลสังเคราะห์ที่เขียนใหม่; ไม่ commit HTML บัญชีจริง งานลูกค้า หรือ cookies
ใช้ fake clocks/events กับ unit/workflow; ไม่รอ timeout จริงหลายนาทีเพื่อพิสูจน์เงื่อนไข
Permission/DOM/native framing tests ไม่ใช้ mock success เพียงอย่างเดียว ต้องมี reject/failure variants

## หลักฐานเมื่อส่งมอบ

แยก unit/fixture, source integration, packaged app/helper/Extension, installed activation,
clean Windows และ real provider output เป็นคนละช่อง; ระบุช่องที่ยังไม่ตรวจ
Live pilot ต้องตรวจว่าไม่มีงานจริงใช้อยู่ ไม่ reload browser/Extension เก่า และไม่ใช้ live account ใน CI
Full suite ใช้เมื่อ release handoff หรือเปลี่ยนข้ามหลายระบบตามกติกาโปรเจกต์
แต่ละ milestone มีผลเล็กที่ตรวจได้ตาม [Story Shorts](story-shorts.md)
