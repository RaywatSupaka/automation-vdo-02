# P4 integration handoff: execution plan

แผนนี้เขียนให้ AI agent ทำต่อเองโดยไม่มีเจ้าของเฝ้าจอ (ประมาณ 2 ชั่วโมง) เริ่มจาก `origin/dev` ล่าสุด
อ่านตามลำดับ: [AGENTS.md](../../AGENTS.md) → [Standard workflow](../development/workflow.md) → ไฟล์นี้ → [คู่มือคำสั่ง](p4-runbook.md) → [เมื่อเจอ error](p4-troubleshooting.md)
ทุกคำสั่งที่ต้องพิมพ์อยู่ในคู่มือคำสั่ง ถ้าเจอ error ให้หาใน p4-troubleshooting.md ก่อนตัดสินใจเอง

## สถานะตั้งต้น (ตรวจแล้ว 2026-10-03)

- P3 ใน source: `POST /api/stories`, `GET /api/stories/{job_id}`, `POST /api/browser/work`, worker heartbeat (F2)
- Extension/helper 0.2.0 จับคู่กับ Dev DB จริงแล้ว; Extension ใน Chrome ของเจ้าของ sync ทุก 30 วินาที
- DB Dev schema `0004`; ไม่มี migration ค้าง
- **ยังไม่มีปุ่มเริ่มงานใน UI**: ขั้นสุดท้ายของ wizard แค่ยืนยันใน UI ([StoryShorts.tsx](../../frontend/src/features/story-shorts/StoryShorts.tsx))
- `useDraft()` ([useDraft.ts](../../frontend/src/features/story-shorts/useDraft.ts)) ยังไม่ส่ง `flush`, draft id และ revision ออกมา

## กติกา (ห้ามฝ่าฝืน)

1. ทำบน branch `dev` เท่านั้น; commit แยกตามงาน T1–T6; **ห้าม push**, ห้าม `git reset/stash/checkout -- <ไฟล์ที่ไม่ได้แก้เอง>`
2. เป็น session เดียวที่แก้ไฟล์; ถ้า `git status` มีไฟล์ที่ไม่ได้แก้เอง → หยุดแก้ไฟล์นั้น เขียนรายงาน
3. กฎธุรกิจอยู่ backend; UI เรียก API และแสดงผลเท่านั้น ห้ามเขียนกฎว่า "เริ่มงานได้หรือไม่" ใน React นอกจากใช้ issues จาก server
4. ผลทุกที่เป็น simulation: แสดงคำว่า "จำลอง" หรือป้าย `SIMULATION` เสมอ ห้ามเรียกว่าคลิป/สื่อจริง
5. ห้ามเพิ่ม migration, ห้ามแก้ registry, ห้าม build EXE หลัก, ห้ามติดตั้ง package ใหม่
6. ห้ามแตะ Extension "SmartFlow AI 0.15.507" (ระบบเดิม) และห้ามปิด Chrome หรือ process ที่ไม่ใช่ของโปรเจกต์
7. `ruff format` เฉพาะไฟล์ที่แก้; ห้ามใช้ `any`, `@ts-ignore`, `# noqa` เพื่อให้ผ่าน
8. ห้ามใช้ sleep จริงในเทส unit ใช้ fake timers/clock; E2E ใช้ `expect(...).toPass()`/`toHaveText` ที่มี timeout
9. ทุก commit message ระบุคำสั่งเทสที่รัน ผล และเวลา (วินาที) ตามจริง ห้ามเขียนว่าผ่านถ้าไม่ได้รัน

## งาน (ทำตามลำดับ; จบหนึ่งข้อ = เทสผ่าน + commit)

**T1 ปุ่มเริ่มงานจำลอง** — ไฟล์: `useDraft.ts`, `StoryShorts.tsx`, ไฟล์ใหม่ `story-job.ts` + `story-job.test.ts`
1. `useDraft()` เพิ่ม `flush: () => ref.current ? ref.current.flush() : Promise.resolve(false)`
   และ `identity: () => ({ id: ref.current?.id, revision: ref.current?.revision ?? 0 })` (DraftStore มี `id`, `revision` อยู่แล้ว)
2. `story-job.ts` ส่งออก `startStoryJob({ flush, identity, send, key })`:
   flush ต้องได้ `true` (ไม่งั้นคืน `{ ok:false, code:'DRAFT_NOT_SAVED' }` โดยไม่เรียก API);
   ไม่มี id → `{ ok:false, code:'DRAFT_NOT_SAVED' }`; แล้ว `send('/stories', { method:'POST', headers:{'Idempotency-Key': key},
   body: JSON.stringify({ draft_id:id, expected_revision:revision, mode:'simulation' }) })`
   ใช้ `transport()` จาก `persistence.ts` เป็น `send`; จับ `ApiError` คืน `{ ok:false, code, message, traceId }`
3. Key: สร้าง `crypto.randomUUID()` ตอนกดครั้งแรก เก็บใน `useRef`; กดซ้ำ/retry ใช้ key เดิม; เปลี่ยน key เมื่อ revision เปลี่ยน
4. ใน `StoryShorts.tsx` ขั้นตรวจรายละเอียด (step สุดท้าย) เพิ่มปุ่ม "เริ่มงานจำลอง" เฉพาะเมื่อมีสิทธิ์ `jobs:create`
   (ส่ง prop `canStart` มาจาก `App.tsx` ผ่าน `storyAccess`/`can('jobs:create')`); ปิดปุ่มเมื่อ `issueSummary(persistence.issues).length > 0`
   หรือกำลังส่ง; แสดงข้อความตาม code จาก T2
5. เทส (Vitest, fake transport): flush false ไม่เรียก API; สำเร็จคืน job; กดสองครั้งใช้ key เดิม;
   `DRAFT_REVISION_CONFLICT`/`STORY_DRAFT_INVALID` คืน code ถูกต้อง
6. ตรวจ: `--scope ui typecheck` แล้ว commit `feat: start simulated Story job from the draft`

**T2 สถานะและผล** — ไฟล์ใหม่ `story-status.ts` + test, แก้ `StoryShorts.tsx`
1. หลังได้ `job.id` เก็บใน state; poll `GET /api/stories/{id}` ทุก 1500 ms ด้วย `setTimeout` (ไม่ใช่ `setInterval`) หยุดเมื่อ
   status เป็น `completed`/`failed`/`cancelled` หรือ component unmount
2. `story-status.ts` ส่งออก `statusText(view)` คืนข้อความไทย: waiting+EXTENSION_DISCONNECTED → "รอ Extension: เปิด Chrome และตรวจการเชื่อมต่อ",
   running → "Extension กำลังทำงานจำลอง", needs_review → "ไม่แน่ใจว่าส่งแล้วหรือยัง ตรวจผลเดิมก่อน", completed → "เสร็จ (จำลอง)",
   failed → "ไม่สำเร็จ: " + ข้อความของ error code, cancelled → "ยกเลิกแล้ว"; code อื่นใช้ข้อความจาก `GET /api/errors`
3. แสดง `result` เมื่อ completed พร้อมป้าย `SIMULATION`; needs_review แสดงปุ่ม "ตรวจผลเดิม" → `POST /api/jobs/{id}/commands/reconcile`
   และ "ยกเลิก" → `.../commands/cancel` (มีสิทธิ์ `jobs:command` เท่านั้น)
4. เทส Vitest ของ `statusText` ครบทุก status; ตรวจ `--scope ui typecheck`; commit `feat: show simulated Story job status and result`

**T3 เวอร์ชันและคำแนะนำ** — แก้ component หน้า "เชื่อมต่อ Extension" (`grep -rn "BrowserPairing" frontend/src`)
- แสดง `extension_version`, `helper_version` จาก `GET /api/browser` และข้อความ: ถ้าไม่ตรง ให้ build helper และ Reload Extension
  ตาม [Extension pairing](../architecture/extension-foundation.md); ไม่ต้องแก้ backend; commit `feat: show expected Extension and helper versions`

**T4 E2E** — ไฟล์ใหม่ `frontend/e2e/story-job.spec.ts` ตามขั้นใน [คู่มือคำสั่ง](p4-runbook.md#e2e-story-job)
- commit `test: e2e for starting and completing a simulated Story job`

**T5 Supervisor restart test** — [runtime.py](../../backend/smartflow/runtime.py), เทสใหม่ `tests/unit/test_supervisor.py`
1. ย้ายเนื้อหา loop ใน `supervise()` เป็นฟังก์ชัน `supervise_step(status, process, restarts, logger) -> (restarts, action)`
   โดย action เป็น `"none" | "restart" | "exhausted"`; `supervise()` เรียกฟังก์ชันนี้แทน พฤติกรรมต้องเหมือนเดิม
2. เทสด้วย fake process (`is_alive`, `terminate`, `join` นับจำนวนเรียก): stalled → terminate 1 ครั้ง + restart;
   down → restart; ครบ 3 → exhausted + log `WORKER_UNAVAILABLE`; ready → none
3. ตรวจ `--scope unit runtime`; commit `test: cover stalled worker restart decisions`

**T6 เอกสารและหลักฐาน** — ทำตาม [คู่มือคำสั่ง](p4-runbook.md#ปิดงาน)
- อัปเดต [status](../delivery/status.md), [milestones](story-extension-milestones.md) (P4 ทำอะไรแล้ว), [Draft API](../architecture/draft-api.md),
  [Step wizard](../architecture/step-wizard.md); สร้าง `docs/delivery/verification-p4.md` และเพิ่มลิงก์ใน [index](../index.md)

ถ้าเวลาไม่พอ: ทำ T1, T2, T4, T6 ให้ครบก่อน; T3 และ T5 ข้ามได้แต่ต้องเขียนในรายงานว่ายังไม่ทำ

## หยุดทันทีและรายงานเมื่อ

- ต้องเพิ่ม migration, แก้ registry, ติดตั้ง package, build EXE หรือแก้ไฟล์ Extension
- เทสที่ไม่เกี่ยวกับงานนี้ล้ม (ตรวจตาม [troubleshooting](p4-troubleshooting.md)) หรือแก้เทสเดิมแล้วยังล้ม 2 รอบ
- หน้าต่างโปรแกรมปิดไม่ได้, Chrome ไม่รับงานภายใน 120 วินาที หรือพบไฟล์ที่คนอื่นแก้

รายงานท้ายรอบเขียนไว้ใน `docs/delivery/verification-p4.md` และสรุปในแชท: commit ที่ทำ, ผลเทส+เวลา, สิ่งที่ยังไม่ทำ, สิ่งที่เจ้าของต้องตัดสินใจ
