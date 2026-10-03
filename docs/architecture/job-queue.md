# Job queue

คิวงานรวมของทุก feature: งานที่ยังไม่จบเรียงตามเวลาที่สร้าง (FIFO) ตามด้วยงานที่เพิ่งจบ
แนวคิดมาจาก creation queue ของระบบเดิม (ทำทีละงาน, ยกเลิกงานที่รอ, ลองใหม่งานที่ล้ม, กู้ต่อหลังเปิดใหม่)
แต่ออกแบบใหม่ให้ backend เป็นเจ้าของลำดับและสถานะทั้งหมด UI แค่อ่านและส่งคำสั่ง

## ทำแล้ว (source Dev)

| ส่วน | พฤติกรรม |
|---|---|
| `GET /api/queue?recent=N` (`jobs:read`) | งานที่ยังไม่จบ (`queued`, `waiting`, `running`, `needs_review`) เก่าก่อน แล้วตามด้วยงานที่จบล่าสุด N งาน |
| `kind` | `story` สำหรับงาน Story จำลอง; scenario อื่นเป็น `automation`; feature ใหม่เพิ่มใน `KINDS` |
| `queue_position` | ลำดับใน FIFO ของงาน Story ที่ยังไม่จบ (0 = งานที่ browser ทำ/จะทำถัดไป); งานที่จบเป็น `null` |
| สถานะตอนรอ | ยังไม่มี Extension เชื่อมต่อ → `waiting` + `EXTENSION_DISCONNECTED`; มี browser sync ใน 90 วินาที → `queued` |
| เวลาหมดอายุ | งบ 900 วินาทีเริ่มนับตอน Extension รับงานครั้งแรก งานที่รอคิวไม่หมดอายุเพราะรอนาน |
| ลำดับการทำ | Extension รับงานเก่าสุดก่อน ทีละงาน; งานที่ไม่แน่ใจว่าส่งแล้ว (`needs_review`) บล็อกงานถัดไปจนกว่าจะ reconcile |
| คำสั่ง | ใช้ `POST /api/jobs/{id}/commands/{cancel,reconcile,resume}` เดิม (`jobs:command`) server ตรวจทุกครั้ง |
| `StoryView.queue_position` | `GET /api/stories/{id}` บอกลำดับคิวของงานนั้นด้วย |

## หน้าจอ

- เมนู **คิวงาน** (`jobs:read`): ทุกงานทุก feature พร้อมประเภท สถานะ ลำดับ ไทม์ไลน์ และผลจำลอง
- แผงคิวในหน้า **เรื่องเล่า Shorts**: เฉพาะงาน Story แบบย่อ
- คลิกงานเพื่อดูไทม์ไลน์จาก `GET /api/jobs/{id}/events` และผลจาก `GET /api/stories/{id}` เมื่อเสร็จ
- ปุ่มคำสั่งตามสถานะ: รอ → ยกเลิก; `needs_review` → ตรวจผลเดิม/ยกเลิก; `failed` → ลองใหม่ (ไม่มี resume ของงานที่ไม่แน่ใจ)
- polling ทุก 1.5 วินาทีด้วย `setTimeout` เฉพาะตอนแผงแสดงอยู่; ทุกผลมีป้าย SIMULATION

## หลังกดเริ่มงาน

1. UI flush แบบร่าง แล้วสร้างงานด้วย key ต่อ draft revision (กดซ้ำได้งานเดิม)
2. เรียก `POST /api/story-drafts/{id}/successor` ด้วย key `successor-<job id>` ได้แบบร่างใหม่ที่ revision 1 ขั้นที่ 1
3. แบบร่างใหม่คงการตั้งค่า ล้างช่องที่ `perStory: true` ใน [draft_fields.json](../../backend/smartflow/draft_fields.json)
   (หัวข้อ, หัวข้อหลายคลิป, รายละเอียดเรื่อง, รูปหลัก, หมายเหตุ, ข้อความปก, บทเสียง)
4. ไฟล์ที่เป็นการตั้งค่า (โลโก้ เพลง ฯลฯ) ถูก clone เป็น asset ใหม่ของแบบร่างใหม่ (hard link ถ้าได้ ไม่งั้นคัดลอก)
   ไฟล์ที่หายไปแล้วไม่ถูกพาไป และจะขึ้น `FIELD_REQUIRED` ให้เลือกใหม่
5. ถ้าสร้างแบบร่างใหม่ไม่สำเร็จ งานยังอยู่ในคิว และหน้าจอมีปุ่ม "เปิดแบบร่างใหม่" ที่ใช้ key เดิม

## ยังไม่ทำ

ลำดับความสำคัญ/ลากเรียงคิว, หยุดคิวทั้งหมด, ลบงานเก่าออกจากรายการ, การนับโควตาไฟล์ที่ clone (hard link ไม่กินพื้นที่เพิ่ม
แต่ยังไม่มี GC ของ asset), งาน feature อื่นนอกจาก Story/automation

Source: [job_queue.py](../../backend/smartflow/job_queue.py), [story_workflow.py](../../backend/smartflow/story_workflow.py),
[drafts.py](../../backend/smartflow/drafts.py), [QueuePanel.tsx](../../frontend/src/features/queue/QueuePanel.tsx)
Tests: [test_story_queue.py](../../tests/test_story_queue.py), [queue.test.ts](../../frontend/src/features/queue/queue.test.ts),
[story-job.spec.ts](../../frontend/e2e/story-job.spec.ts)
