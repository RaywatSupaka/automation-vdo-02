# P4 integration handoff: execution plan

แผนนี้เขียนให้ AI agent ทำต่อโดยไม่มีเจ้าของเฝ้าจอ (ประมาณ 2 ชั่วโมง) เริ่มจาก commit `8095921` บน `dev`
อ่าน [AGENTS.md](../../AGENTS.md) และ [Parallel sessions](../development/parallel-work.md) ก่อนเริ่ม
เป้าหมาย P4 อยู่ใน [Coordinated milestones](story-extension-milestones.md)

## สถานะตั้งต้น (ตรวจแล้ว)

- P3 ใน source: `POST/GET /api/stories`, `POST /api/browser/work`, StoryWorkflow, worker heartbeat (F2)
- Extension/helper 0.2.0 build แล้ว ลงทะเบียน `com.smartflow.next.dev` ชี้ `build/native/` และจับคู่กับ Dev DB จริงแล้ว
- Extension ใน Chrome ของเจ้าของ sync ทุก 30 วินาทีแม้ปิด popup; DB Dev อยู่ schema `0004`
- **ยังไม่มีปุ่มเริ่มงานใน UI**: ขั้นสุดท้ายของ wizard แค่ยืนยันใน UI ([StoryShorts.tsx](../../frontend/src/features/story-shorts/StoryShorts.tsx))
- Commit `06a9b98`, `8095921` ยังไม่ push

## กติกาสำหรับรอบนี้

- ทำบน `dev`, commit แยกตามงานด้านล่าง พร้อมผลเทสและเวลาที่วัดได้ใน message; **ห้าม push** เว้นแต่เจ้าของสั่ง
- เป็น session เดียวที่แก้ working tree; ถ้า `git status` มีไฟล์ที่ไม่ได้แก้เองโผล่มา ให้หยุดแก้ไฟล์นั้นและรายงาน
- กฎธุรกิจอยู่ backend; UI แค่เรียก API และแสดงผล ห้ามตัดสินว่าเริ่มงานได้เองนอกจากใช้ issues จาก server
- ผลทั้งหมดเป็น simulation: ทุกจุดที่แสดงผลต้องมีป้าย SIMULATION/จำลอง ห้ามเรียกว่าสื่อจริง
- ห้ามแตะ Extension "SmartFlow AI 0.15.507" ของระบบเดิม และห้ามแก้ registry นอก host `com.smartflow.next.dev`
- ห้ามเพิ่ม migration ในรอบนี้; ถ้าจำเป็นต้องมี ให้หยุดและเขียนเหตุผลไว้ใน status
- ใช้ `ruff format` เฉพาะไฟล์ที่แก้ ไม่ format ทั้งโฟลเดอร์

## งาน (ทำตามลำดับ; T1–T3 คือแกนของ P4)

**T1 ปุ่มเริ่มงานจำลองจากแบบร่าง**
- ขั้นตรวจรายละเอียดเพิ่มปุ่ม "เริ่มงานจำลอง" แสดงเฉพาะเมื่อมี `jobs:create`
- ก่อนส่ง: `await persistence.flush()` ต้องได้ true แล้วใช้ `revision` ล่าสุดเป็น `expected_revision`
- เรียก `POST /api/stories` `{draft_id, expected_revision, mode:"simulation"}` พร้อม `Idempotency-Key` ที่คงที่ต่อการกดหนึ่งครั้ง (retry ใช้ key เดิม)
- ปิดปุ่มเมื่อ server issues มีรายการ; แสดง error ตาม code: `STORY_DRAFT_INVALID`, `DRAFT_REVISION_CONFLICT` (ให้ flush/โหลดใหม่), `STORY_CAPABILITY_UNAVAILABLE` (รองรับเฉพาะคลิปเดียว), `PERMISSION_DENIED`
- แยก logic เป็น helper pure เช่น `frontend/src/features/story-shorts/story-job.ts` พร้อม Vitest: กดซ้ำได้ job เดิม, flush ไม่ผ่านไม่ส่ง, conflict
- เกณฑ์จบ: Vitest + typecheck ผ่าน; backend ไม่ต้องแก้ (route มีแล้ว)

**T2 แสดงสถานะ/ผลของงานจำลอง**
- หลังเริ่มงาน poll `GET /api/stories/{job_id}` ทุก 1.5 วินาทีเฉพาะตอนเปิดหน้า Story; หยุดเมื่อ `completed`/`failed`/`cancelled`
- แสดง status, `error_code` + ข้อความจาก `GET /api/errors`, `receipt_state` และ `result` เมื่อ completed พร้อมป้าย SIMULATION
- `waiting` + `EXTENSION_DISCONNECTED` ให้แนะนำเปิด Chrome/ตรวจการเชื่อมต่อ; `needs_review` ให้ปุ่ม reconcile/cancel ผ่าน `POST /api/jobs/{id}/commands/{action}` (route นี้ส่งต่อให้ StoryWorkflow แล้ว)
- หน้า Jobs: งาน `story_simulated` ต้องแสดงในรายการเดิมได้ ตรวจว่าไม่พังกับ timeline/diagnostics
- เกณฑ์จบ: Vitest ของ mapping สถานะ→ข้อความ; ไม่มี business rule ใหม่ใน UI

**T3 แสดงคู่เวอร์ชันและคำแนะนำเมื่อไม่ตรง**
- หน้า "เชื่อมต่อ Extension" แสดง `extension_version`/`helper_version` ที่ระบบรับ (จาก `GET /api/browser`)
- ถ้า pairing ล่าสุดเจอ `EXTENSION_VERSION_MISMATCH` ให้คำแนะนำเฉพาะ: build helper ตาม [Extension pairing](../architecture/extension-foundation.md) และ Reload Extension
- ถ้าต้องให้ backend เก็บ/ส่งเวอร์ชันที่ Extension รายงานมา ให้เพิ่มใน response เท่านั้น (ไม่มี migration) และ regenerate `contracts/openapi.json`

**T4 E2E ของ flow ใหม่ (Playwright)**
- `frontend/e2e/story-job.spec.ts`: กรอกแบบร่างขั้นต่ำ → เริ่มงาน → เห็น waiting/EXTENSION_DISCONNECTED
- จำลอง agent ในเทสผ่าน API: owner สร้าง pairing → exchange ด้วย token ทดสอบ → `browser/work` sync/grant/result → UI แสดง completed + SIMULATION
- ใช้ข้อมูลชั่วคราวตาม fixture เดิม ห้ามชี้ไป `.smartflow/`

**T5 Test การ restart worker ที่ค้าง (ค้างจาก P3)**
- แยกการตัดสินใจใน `supervise()` ของ [runtime.py](../../backend/smartflow/runtime.py) เป็นฟังก์ชันที่รับ status/process/restarts
- Unit test ด้วย fake process: stalled → terminate + นับ restart, ครบ 3 → `WORKER_UNAVAILABLE`, down → restart
- ห้ามเพิ่ม env/flag สำหรับเทสที่ใช้ได้ใน prod

**T6 เอกสารและหลักฐาน**
- อัปเดต [status](../delivery/status.md), [milestones](story-extension-milestones.md), [Draft API](../architecture/draft-api.md) ส่วนเริ่มงาน และ [Step wizard](../architecture/step-wizard.md)
- สร้าง `docs/delivery/verification-p4.md` (คำสั่ง, เวลา, ผล, หลักฐานแยกชั้น) และลิงก์ใน [index](../index.md)

## การตรวจ

1. ระหว่างทาง: `--scope ui typecheck`, `story-workflow`, `story-api`, `runtime`, `unit` ตามไฟล์ที่แก้ (`--changed --dry-run` ดูแผน)
2. จบงาน: `.venv/Scripts/python.exe tools/check.py --scope all` ต้องผ่านทั้งหมด
3. ปิดเปิด desktop ตาม [Setup](../development/setup.md): ปิดหน้าต่างแบบปกติ (CloseMainWindow) เปิด `RUN_DEV.vbs`
4. **End-to-end ใน Chrome ของเจ้าของ:** เริ่มงานจำลอง 1 งานจากแบบร่างใน UI จริง แล้วรอไม่เกิน 60 วินาที
   ให้ alarm ของ Extension รับงาน; ตรวจผ่าน DB แบบ read-only ว่า job `completed`, `receipt_state` completed
   และ event `story.dispatch_marked` = 1 ครั้ง (ส่งครั้งเดียว) — งานนี้จะอยู่ใน Dev DB ถาวร
5. แยกผลในรายงาน: unit/E2E, desktop activation, real Chrome; ไม่มี EXE/clean Windows/provider จริงในรอบนี้

## หยุดและรายงานเมื่อ

- ต้องเพิ่ม migration, แก้ registry อื่น, ติดตั้ง package ใหม่ หรือ build EXE หลัก
- เทสที่ไม่เกี่ยวกับงานนี้ล้ม หรือ `--scope all` ล้มหลังแก้ 2 รอบ
- Chrome ไม่รับงานภายใน 60 วินาที (อย่าแก้ registry/Extension เอง ให้บันทึกอาการและ log)
- พบไฟล์ที่ถูกแก้โดยคนอื่นใน working tree

สรุปท้ายรอบ: commit ที่ทำ, ผลเทสพร้อมเวลา, สิ่งที่ยังไม่เสร็จ และสิ่งที่ต้องให้เจ้าของตัดสินใจ
